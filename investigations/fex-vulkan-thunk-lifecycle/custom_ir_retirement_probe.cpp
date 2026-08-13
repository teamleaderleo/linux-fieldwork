#include <cstdint>
#include <cstdio>
#include <optional>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace {

enum class HandlerState { Active, Tombstone };
enum class DispatchKind { GuestTarget, Reject, FrontendDecode };

struct Dispatch {
  DispatchKind kind {};
  uintptr_t target {};
};

struct Handler {
  HandlerState state {HandlerState::Active};
  uintptr_t target {};
  uint64_t signature {};
};

class Model {
public:
  // Current FEX semantics for an active key: first insertion wins.
  bool Add(uintptr_t key, uintptr_t target, uint64_t signature) {
    auto it = handlers.find(key);
    if (it == handlers.end()) {
      handlers.emplace(key, Handler {HandlerState::Active, target, signature});
      return true;
    }
    if (it->second.state == HandlerState::Tombstone) {
      it->second = Handler {HandlerState::Active, target, signature};
      compiled.erase(key);
      return true;
    }
    return it->second.target == target;
  }

  Dispatch DispatchKey(uintptr_t key) {
    if (auto it = compiled.find(key); it != compiled.end()) return it->second;
    auto it = handlers.find(key);
    if (it == handlers.end()) {
      // This mirrors the real semantic danger after removing CustomIR: FEX falls through
      // to ordinary frontend decode at a synthetic/native host address.
      return {DispatchKind::FrontendDecode, key};
    }
    Dispatch d = it->second.state == HandlerState::Active
      ? Dispatch {DispatchKind::GuestTarget, it->second.target}
      : Dispatch {DispatchKind::Reject, 0};
    compiled[key] = d;
    return d;
  }

  void Invalidate(uintptr_t key) { compiled.erase(key); }

  // Earlier range-cleanup proposal: erase matching records.
  void EraseTarget(uintptr_t target) {
    std::vector<uintptr_t> keys;
    for (auto const& [key, h] : handlers) if (h.state == HandlerState::Active && h.target == target) keys.push_back(key);
    for (auto key : keys) {
      handlers.erase(key);
      compiled.erase(key);
    }
  }

  // Revised retirement proposal: retain the synthetic key as a rejected/tombstoned
  // entry so it never falls through to normal decoding, and permit a later reload to rebind it.
  void TombstoneTarget(uintptr_t target) {
    for (auto& [key, h] : handlers) {
      if (h.state == HandlerState::Active && h.target == target) {
        h.state = HandlerState::Tombstone;
        h.target = 0;
        compiled.erase(key);
      }
    }
  }

  std::optional<Handler> Get(uintptr_t key) const {
    auto it = handlers.find(key);
    if (it == handlers.end()) return std::nullopt;
    return it->second;
  }

private:
  std::unordered_map<uintptr_t, Handler> handlers;
  std::unordered_map<uintptr_t, Dispatch> compiled;
};

struct Tests {
  int pass {}, fail {};
  void Expect(bool cond, std::string_view name) {
    std::printf("%-70s %s\n", name.data(), cond ? "PASS" : "FAIL");
    cond ? ++pass : ++fail;
  }
};

} // namespace

int main() {
  Tests t;
  constexpr uintptr_t H = 0x700000001000ULL;
  constexpr uintptr_t T1 = 0x40001000ULL;
  constexpr uintptr_t T2 = 0x50001000ULL;
  constexpr uint64_t SIG_A = 0xaabbccddULL;
  constexpr uint64_t SIG_B = 0x11223344ULL;

  // A. Current active mapping compiles to the guest target.
  {
    Model m;
    t.Expect(m.Add(H, T1, SIG_A), "active: first host->guest registration accepted");
    auto d = m.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::GuestTarget && d.target == T1,
             "active: dispatch reaches registered guest wrapper");
  }

  // B. Earlier erase cleanup has a real-FEX fallback hazard.
  {
    Model m;
    m.Add(H, T1, SIG_A);
    (void)m.DispatchKey(H);
    m.EraseTarget(T1);
    auto d = m.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::FrontendDecode,
             "erase cleanup: stale host key falls through to ordinary frontend decode");
  }

  // C. Tombstone cleanup blocks stale dispatch without changing pointer identity.
  {
    Model m;
    m.Add(H, T1, SIG_A);
    (void)m.DispatchKey(H);
    m.TombstoneTarget(T1);
    auto d = m.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::Reject,
             "tombstone: stale host key is rejected instead of decoded as guest code");
    t.Expect(m.Get(H).has_value(), "tombstone: synthetic/native host key identity is retained");
  }

  // D. Reload can rebind the same guest-visible native PFN to a new guest image.
  {
    Model m;
    m.Add(H, T1, SIG_A);
    m.TombstoneTarget(T1);
    t.Expect(m.Add(H, T2, SIG_A), "reload: tombstoned native PFN can bind to new guest wrapper");
    auto d = m.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::GuestTarget && d.target == T2,
             "reload: same native PFN dispatches to new guest image");
  }

  // E. Current first-wins collision behavior is still visible while active.
  {
    Model m;
    t.Expect(m.Add(H, T1, SIG_A), "collision: first active claim accepted");
    t.Expect(!m.Add(H, T2, SIG_B), "collision: different active wrapper remains rejected");
    auto d = m.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::GuestTarget && d.target == T1,
             "collision: first active wrapper remains authoritative");
  }

  // F. Important compatibility limit: if two live DSOs could legitimately share one
  // host key, a single-target registry cannot promote the rejected owner on unload.
  {
    Model m;
    t.Expect(m.Add(H, T1, SIG_A), "cross-owner: first DSO claim accepted");
    t.Expect(!m.Add(H, T2, SIG_A), "cross-owner: equivalent-signature second DSO target is still not retained");
    m.TombstoneTarget(T1);
    auto d = m.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::Reject,
             "cross-owner: unloading first owner cannot promote an unrecorded second owner");
  }

  std::printf("\nRESULT passed=%d failed=%d\n", t.pass, t.fail);
  return t.fail ? 1 : 0;
}
