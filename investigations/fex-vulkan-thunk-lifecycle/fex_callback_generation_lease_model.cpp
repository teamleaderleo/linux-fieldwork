#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <thread>

struct GuestGeneration {
  uint64_t id;
  uintptr_t unpacker;
  uintptr_t target;
  std::atomic<bool> mapped{true};
};

struct BridgeState {
  uint64_t generation;
  GuestGeneration* owner;
  std::mutex mu;
  std::condition_variable cv;
  bool draining{};
  unsigned active{};
};

struct TrampolineInstanceInfo {
  uintptr_t guest_unpacker;
  uintptr_t guest_target;
  BridgeState* state;
  bool revoked{};
};

enum class Result { Executed, Revoked, UAF };

static const char* name(Result r) {
  switch (r) {
    case Result::Executed: return "EXEC";
    case Result::Revoked: return "REVOKED";
    case Result::UAF: return "UAF";
  }
  return "?";
}

struct SelectedCallback {
  uintptr_t unpacker;
  uintptr_t target;
  BridgeState* state;
};

static SelectedCallback select(const TrampolineInstanceInfo& t) {
  return {t.guest_unpacker, t.guest_target, t.state};
}

static Result call_with_generation_lease(const SelectedCallback& s,
                                         std::condition_variable* acquired_cv = nullptr,
                                         std::mutex* acquired_mu = nullptr,
                                         bool* acquired_flag = nullptr,
                                         std::condition_variable* resume_cv = nullptr,
                                         std::mutex* resume_mu = nullptr,
                                         bool* resume_flag = nullptr) {
  BridgeState* st = s.state;
  {
    std::unique_lock lk(st->mu);
    if (st->draining) return Result::Revoked;
    ++st->active;
  }

  if (acquired_cv) {
    {
      std::lock_guard lk(*acquired_mu);
      *acquired_flag = true;
    }
    acquired_cv->notify_all();
    std::unique_lock lk(*resume_mu);
    resume_cv->wait(lk, [&]{ return *resume_flag; });
  }

  // Models the FEX-owned guest transition. The lease must cover this point.
  Result out = st->owner->mapped.load(std::memory_order_acquire) ? Result::Executed : Result::UAF;

  {
    std::lock_guard lk(st->mu);
    if (--st->active == 0) st->cv.notify_all();
  }
  return out;
}

static void retire_and_drain(TrampolineInstanceInfo& t, BridgeState& st,
                             std::condition_variable* draining_cv = nullptr,
                             std::mutex* draining_mu = nullptr,
                             bool* draining_flag = nullptr) {
  {
    std::lock_guard lk(st.mu);
    st.draining = true;
  }
  // The escaped trampoline address stays stable, but new uses are revoked.
  t.revoked = true;

  if (draining_cv) {
    {
      std::lock_guard lk(*draining_mu);
      *draining_flag = true;
    }
    draining_cv->notify_all();
  }

  std::unique_lock lk(st.mu);
  st.cv.wait(lk, [&]{ return st.active == 0; });
  lk.unlock();

  // Physical unmap is allowed only after the generation has drained.
  st.owner->mapped.store(false, std::memory_order_release);
}

static Result invoke_current(const TrampolineInstanceInfo& t) {
  if (t.revoked) return Result::Revoked;
  return call_with_generation_lease(select(t));
}

int main() {
  // Deliberately reuse the same raw guest executable addresses across generations,
  // matching the ABA behavior observed in the full-FEX callback experiment.
  constexpr uintptr_t SAME_UNPACKER = 0x7ffff7da2190ULL;
  constexpr uintptr_t SAME_TARGET   = 0x7ffff7da2170ULL;

  // Negative control: raw address selection followed by unmap still loses even
  // if the published trampoline is tombstoned after selection.
  GuestGeneration raw_owner{1, SAME_UNPACKER, SAME_TARGET};
  TrampolineInstanceInfo raw_t{SAME_UNPACKER, SAME_TARGET, nullptr, false};
  const auto raw_selected = select(raw_t);
  (void)raw_selected;
  raw_t.revoked = true;
  raw_owner.mapped.store(false);
  Result raw = raw_owner.mapped.load() ? Result::Executed : Result::UAF;
  std::printf("raw_select_then_unmap=%s\n", name(raw));

  GuestGeneration gen1{1, SAME_UNPACKER, SAME_TARGET};
  BridgeState state1{1, &gen1};
  TrampolineInstanceInfo old_trampoline{SAME_UNPACKER, SAME_TARGET, &state1, false};

  // Worker copies the stable generation token and acquires an execution lease.
  const SelectedCallback selected_old = select(old_trampoline);
  std::mutex acquired_mu, resume_mu, draining_mu;
  std::condition_variable acquired_cv, resume_cv, draining_cv;
  bool acquired = false, resume = false, draining = false;
  Result worker = Result::UAF;

  std::thread w([&] {
    worker = call_with_generation_lease(selected_old,
      &acquired_cv, &acquired_mu, &acquired,
      &resume_cv, &resume_mu, &resume);
  });

  {
    std::unique_lock lk(acquired_mu);
    acquired_cv.wait(lk, [&]{ return acquired; });
  }

  std::thread retire([&] {
    retire_and_drain(old_trampoline, state1, &draining_cv, &draining_mu, &draining);
  });

  {
    std::unique_lock lk(draining_mu);
    draining_cv.wait(lk, [&]{ return draining; });
  }

  // Retirement is waiting on active==0, so the owner must still be executable.
  const bool mapped_while_draining = gen1.mapped.load();
  {
    std::lock_guard lk(resume_mu);
    resume = true;
  }
  resume_cv.notify_all();
  w.join();
  retire.join();

  std::printf("lease_inflight_worker=%s mapped_while_draining=%d mapped_after_drain=%d\n",
              name(worker), mapped_while_draining ? 1 : 0, gen1.mapped.load() ? 1 : 0);
  std::printf("escaped_old_after_retire=%s\n", name(invoke_current(old_trampoline)));

  // ABA reload: raw guest executable addresses are deliberately identical, but
  // the stable FEX-owned BridgeState token is a different generation object.
  GuestGeneration gen2{2, SAME_UNPACKER, SAME_TARGET};
  BridgeState state2{2, &gen2};
  TrampolineInstanceInfo fresh_trampoline{SAME_UNPACKER, SAME_TARGET, &state2, false};
  const Result fresh = invoke_current(fresh_trampoline);
  std::printf("same_address_reload old_gen=%llu new_gen=%llu unpacker_same=%d target_same=%d fresh=%s stale=%s\n",
              (unsigned long long)state1.generation,
              (unsigned long long)state2.generation,
              old_trampoline.guest_unpacker == fresh_trampoline.guest_unpacker,
              old_trampoline.guest_target == fresh_trampoline.guest_target,
              name(fresh), name(invoke_current(old_trampoline)));

  // Selected before retirement, but acquisition delayed until after retirement:
  // the copied old stable token observes draining and rejects instead of ABA-binding.
  GuestGeneration gen3{3, SAME_UNPACKER, SAME_TARGET};
  BridgeState state3{3, &gen3};
  TrampolineInstanceInfo t3{SAME_UNPACKER, SAME_TARGET, &state3, false};
  SelectedCallback selected_but_not_acquired = select(t3);
  {
    std::lock_guard lk(state3.mu);
    state3.draining = true;
  }
  t3.revoked = true;
  Result late = call_with_generation_lease(selected_but_not_acquired);
  gen3.mapped.store(false);
  std::printf("selected_old_token_acquire_after_retire=%s\n", name(late));

  const bool ok = raw == Result::UAF && worker == Result::Executed && mapped_while_draining &&
                  !gen1.mapped.load() && invoke_current(old_trampoline) == Result::Revoked &&
                  fresh == Result::Executed && late == Result::Revoked;
  std::printf("all_checks=%s\n", ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}
