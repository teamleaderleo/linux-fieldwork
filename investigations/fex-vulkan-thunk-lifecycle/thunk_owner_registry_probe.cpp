#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <optional>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace {

using Owner = uint64_t;
using Signature = uint64_t;

enum class DispatchKind { GuestTarget, Reject, FrontendDecode };
struct Dispatch { DispatchKind kind {}; uintptr_t target {}; };

struct Claim {
  Owner owner {};
  uintptr_t target {};
  Signature signature {};
  uint64_t sequence {};
};

struct Entry {
  std::vector<Claim> claims;
  std::optional<size_t> active;
  Signature established_signature {};
  bool tombstone {true};
};

class Registry {
public:
  bool Add(uintptr_t host_key, Owner owner, uintptr_t guest_target, Signature signature) {
    auto &e = entries[host_key];
    for (const auto &c : e.claims) {
      if (c.owner == owner && c.target == guest_target && c.signature == signature) return true;
    }

    // Once a key has an active signature, retain incompatible claims for diagnostics but
    // do not allow them to become executable automatically.
    e.claims.push_back({owner, guest_target, signature, ++sequence});
    if (!e.active) {
      size_t idx = e.claims.size() - 1;
      if (e.established_signature == 0 || e.established_signature == signature) {
        e.active = idx;
        e.established_signature = signature;
        e.tombstone = false;
        compiled.erase(host_key);
        return true;
      }
      return false;
    }

    const auto &active = e.claims[*e.active];
    return active.signature == signature && active.target == guest_target;
  }

  Dispatch DispatchKey(uintptr_t host_key) {
    if (auto it = compiled.find(host_key); it != compiled.end()) return it->second;
    auto it = entries.find(host_key);
    if (it == entries.end()) return {DispatchKind::FrontendDecode, host_key};
    Entry &e = it->second;
    if (!e.active || e.tombstone) {
      auto d = Dispatch{DispatchKind::Reject, 0};
      compiled[host_key] = d;
      return d;
    }
    auto d = Dispatch{DispatchKind::GuestTarget, e.claims[*e.active].target};
    compiled[host_key] = d;
    return d;
  }

  // Models retirement by a per-load generation identity. Every affected synthetic key is
  // explicitly invalidated, independent of SMC mode.
  size_t RevokeOwner(Owner owner) {
    size_t invalidated = 0;
    for (auto &[key, e] : entries) {
      bool changed = false;
      std::optional<Claim> old_active;
      if (e.active) old_active = e.claims[*e.active];

      e.claims.erase(std::remove_if(e.claims.begin(), e.claims.end(),
                                    [&](const Claim &c) { return c.owner == owner; }),
                     e.claims.end());

      if (old_active && old_active->owner == owner) {
        e.active.reset();
        // Promote only a claim whose signature matches the already-established ABI.
        size_t best = 0;
        bool found = false;
        for (size_t i = 0; i < e.claims.size(); ++i) {
          if (e.claims[i].signature == e.established_signature &&
              (!found || e.claims[i].sequence < e.claims[best].sequence)) {
            best = i;
            found = true;
          }
        }
        if (found) {
          e.active = best;
          e.tombstone = false;
        } else {
          e.tombstone = true;
        }
        changed = true;
      }

      if (changed) {
        compiled.erase(key);
        ++invalidated;
      }
    }
    return invalidated;
  }

  bool IsTombstone(uintptr_t key) const {
    auto it = entries.find(key);
    return it != entries.end() && it->second.tombstone;
  }

  size_t ClaimCount(uintptr_t key) const {
    auto it = entries.find(key);
    return it == entries.end() ? 0 : it->second.claims.size();
  }

private:
  uint64_t sequence {};
  std::unordered_map<uintptr_t, Entry> entries;
  std::unordered_map<uintptr_t, Dispatch> compiled;
};

struct Tests {
  int pass {}, fail {};
  void Expect(bool cond, std::string_view name) {
    std::printf("%-76s %s\n", name.data(), cond ? "PASS" : "FAIL");
    cond ? ++pass : ++fail;
  }
};

} // namespace

int main() {
  Tests t;
  constexpr uintptr_t H = 0x700000001000ULL;
  constexpr uintptr_t H2 = 0x700000002000ULL;
  constexpr uintptr_t T1 = 0x40001000ULL;
  constexpr uintptr_t T2 = 0x50001000ULL;
  constexpr uintptr_t T3 = 0x60001000ULL;
  constexpr Owner A = 101;
  constexpr Owner B = 202;
  constexpr Owner C = 303;
  constexpr Signature SIG_VOID_PTR = 0xaabbccddULL;
  constexpr Signature SIG_OTHER = 0x11223344ULL;

  // Baseline active mapping and explicit owner retirement.
  {
    Registry r;
    t.Expect(r.Add(H, A, T1, SIG_VOID_PTR), "owner: first load-generation claim becomes active");
    auto d = r.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::GuestTarget && d.target == T1,
             "owner: active claim dispatches to its guest wrapper");
    t.Expect(r.RevokeOwner(A) == 1, "owner: revocation invalidates affected synthetic key");
    d = r.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::Reject, "owner: no surviving claim leaves a tombstone");
    t.Expect(r.IsTombstone(H), "owner: tombstone retains native PFN identity");
  }

  // Compatible live second owner survives first-owner unload.
  {
    Registry r;
    t.Expect(r.Add(H, A, T1, SIG_VOID_PTR), "promotion: first compatible owner active");
    // Different guest address but same signature: retained as a claim even though first stays active.
    t.Expect(!r.Add(H, B, T2, SIG_VOID_PTR), "promotion: second compatible target does not replace live first owner");
    t.Expect(r.ClaimCount(H) == 2, "promotion: second compatible owner is retained for lifetime handoff");
    (void)r.DispatchKey(H); // compile old active path
    t.Expect(r.RevokeOwner(A) == 1, "promotion: unloading active owner invalidates compiled synthetic path");
    auto d = r.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::GuestTarget && d.target == T2,
             "promotion: surviving same-signature owner becomes active");
  }

  // Incompatible claim is retained diagnostically but never auto-promoted.
  {
    Registry r;
    t.Expect(r.Add(H, A, T1, SIG_VOID_PTR), "abi: establish active signature");
    t.Expect(!r.Add(H, B, T2, SIG_OTHER), "abi: incompatible owner cannot replace active claim");
    t.Expect(r.ClaimCount(H) == 2, "abi: incompatible collision is retained for diagnosis");
    r.RevokeOwner(A);
    auto d = r.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::Reject,
             "abi: incompatible survivor is not promoted after active owner unload");
  }

  // Reload after full unload can rebind the same key with the established signature.
  {
    Registry r;
    r.Add(H, A, T1, SIG_VOID_PTR);
    r.RevokeOwner(A);
    t.Expect(r.Add(H, C, T3, SIG_VOID_PTR), "reload: new generation can revive tombstoned native PFN");
    auto d = r.DispatchKey(H);
    t.Expect(d.kind == DispatchKind::GuestTarget && d.target == T3,
             "reload: rebound key reaches new guest image");
  }

  // Owner retirement spans aliases but preserves unrelated owners/keys.
  {
    Registry r;
    r.Add(H, A, T1, SIG_VOID_PTR);
    r.Add(H2, A, T2, SIG_OTHER);
    constexpr uintptr_t HU = 0x700000003000ULL;
    r.Add(HU, B, T3, SIG_VOID_PTR);
    t.Expect(r.RevokeOwner(A) == 2, "aliases: one load generation revokes every dependent synthetic key");
    t.Expect(r.DispatchKey(H).kind == DispatchKind::Reject, "aliases: first alias tombstoned");
    t.Expect(r.DispatchKey(H2).kind == DispatchKind::Reject, "aliases: second alias tombstoned");
    auto du = r.DispatchKey(HU);
    t.Expect(du.kind == DispatchKind::GuestTarget && du.target == T3,
             "aliases: unrelated owner remains callable");
  }

  // Unknown values remain ordinary guest addresses. Only values FEX previously blessed remain tombstoned.
  {
    Registry r;
    constexpr uintptr_t UNKNOWN = 0x12345000ULL;
    t.Expect(r.DispatchKey(UNKNOWN).kind == DispatchKind::FrontendDecode,
             "scope: arbitrary guest address still uses ordinary frontend decode");
    r.Add(H, A, T1, SIG_VOID_PTR);
    r.RevokeOwner(A);
    t.Expect(r.DispatchKey(H).kind == DispatchKind::Reject,
             "scope: formerly synthetic native PFN remains distinguished after unload");
  }

  std::printf("\nRESULT passed=%d failed=%d\n", t.pass, t.fail);
  return t.fail ? 1 : 0;
}
