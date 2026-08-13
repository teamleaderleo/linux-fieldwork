#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <string_view>
#include <unordered_map>
#include <vector>

using Owner = uint64_t;

enum class BridgeKind { SyntheticPFN, HostCallback };
enum class State { Active, Revoked };
enum class Dispatch { Guest, Reject, FrontendDecode };

struct Bridge {
  BridgeKind kind{};
  uintptr_t public_key{};
  std::vector<Owner> deps;
  State state{State::Active};
  uintptr_t guest_unpacked_target{};
};

class Graph {
public:
  void Add(Bridge b) { bridges[b.public_key] = std::move(b); }

  Dispatch Invoke(uintptr_t key) const {
    auto it = bridges.find(key);
    if (it == bridges.end()) return Dispatch::FrontendDecode;
    return it->second.state == State::Active ? Dispatch::Guest : Dispatch::Reject;
  }

  size_t RevokeOwner(Owner owner) {
    size_t n{};
    for (auto& [key, b] : bridges) {
      if (b.state == State::Active && std::find(b.deps.begin(), b.deps.end(), owner) != b.deps.end()) {
        b.state = State::Revoked;
        ++n;
      }
    }
    return n;
  }

  bool Rebind(uintptr_t key, std::vector<Owner> deps, uintptr_t guest_target) {
    auto it = bridges.find(key);
    if (it == bridges.end()) return false;
    it->second.deps = std::move(deps);
    it->second.guest_unpacked_target = guest_target;
    it->second.state = State::Active;
    return true;
  }

  bool Revoked(uintptr_t key) const {
    auto it = bridges.find(key);
    return it != bridges.end() && it->second.state == State::Revoked;
  }

private:
  std::unordered_map<uintptr_t, Bridge> bridges;
};

struct T {
  int pass{}, fail{};
  void expect(bool v, std::string_view s) {
    std::printf("%-82s %s\n", s.data(), v ? "PASS" : "FAIL");
    v ? ++pass : ++fail;
  }
};

int main() {
  T t;
  constexpr Owner Vulkan = 11;
  constexpr Owner X11 = 22;
  constexpr Owner GL = 33;
  constexpr Owner Other = 44;
  constexpr uintptr_t VK_PFN = 0x700000001000ULL;
  constexpr uintptr_t VK_XSYNC_TRAMP = 0x800000001000ULL;
  constexpr uintptr_t GL_PFN = 0x700000002000ULL;
  constexpr uintptr_t UNKNOWN = 0x12345000ULL;

  {
    Graph g;
    g.Add({BridgeKind::SyntheticPFN, VK_PFN, {Vulkan}, State::Active, 0x40001000});
    t.expect(g.Invoke(VK_PFN) == Dispatch::Guest, "customir: active Vulkan PFN dispatches through guest wrapper");
    t.expect(g.RevokeOwner(Vulkan) == 1, "customir: unloading wrapper owner revokes the synthetic PFN");
    t.expect(g.Invoke(VK_PFN) == Dispatch::Reject, "customir: revoked PFN rejects instead of frontend-decoding host bytes");
  }

  {
    Graph g;
    g.Add({BridgeKind::HostCallback, VK_XSYNC_TRAMP, {Vulkan, X11}, State::Active, 0x50001000});
    t.expect(g.Invoke(VK_XSYNC_TRAMP) == Dispatch::Guest, "callback: active trampoline requires Vulkan unpacker plus X11 guest target");
    t.expect(g.RevokeOwner(Vulkan) == 1, "callback: unloading Vulkan revokes trampoline although X11 remains loaded");
    t.expect(g.Invoke(VK_XSYNC_TRAMP) == Dispatch::Reject, "callback: host-held stale trampoline address remains safely rejectable");
  }

  {
    Graph g;
    g.Add({BridgeKind::HostCallback, VK_XSYNC_TRAMP, {Vulkan, X11}, State::Active, 0x50001000});
    t.expect(g.RevokeOwner(X11) == 1, "callback: unloading guest target owner also revokes trampoline");
    t.expect(g.Invoke(VK_XSYNC_TRAMP) == Dispatch::Reject, "callback: missing target owner cannot be masked by live unpacker");
  }

  {
    Graph g;
    g.Add({BridgeKind::SyntheticPFN, VK_PFN, {Vulkan}, State::Active, 0x40001000});
    g.Add({BridgeKind::HostCallback, VK_XSYNC_TRAMP, {Vulkan, X11}, State::Active, 0x50001000});
    g.Add({BridgeKind::SyntheticPFN, GL_PFN, {GL}, State::Active, 0x60001000});
    t.expect(g.RevokeOwner(Vulkan) == 2, "fanout: one load generation revokes every bridge depending on it");
    t.expect(g.Invoke(VK_PFN) == Dispatch::Reject, "fanout: Vulkan dynamic PFN revoked");
    t.expect(g.Invoke(VK_XSYNC_TRAMP) == Dispatch::Reject, "fanout: Vulkan-created X11 callback trampoline revoked");
    t.expect(g.Invoke(GL_PFN) == Dispatch::Guest, "fanout: unrelated GL bridge remains active");
  }

  {
    Graph g;
    g.Add({BridgeKind::HostCallback, VK_XSYNC_TRAMP, {Vulkan, X11}, State::Active, 0x50001000});
    g.RevokeOwner(Vulkan);
    constexpr Owner Vulkan2 = 55;
    t.expect(g.Rebind(VK_XSYNC_TRAMP, {Vulkan2, X11}, 0x50002000), "reload: stable trampoline identity can be rebound to new unpacker generation");
    t.expect(g.Invoke(VK_XSYNC_TRAMP) == Dispatch::Guest, "reload: rebound callback bridge becomes callable again");
  }

  {
    Graph g;
    g.Add({BridgeKind::SyntheticPFN, VK_PFN, {Vulkan}, State::Active, 0x40001000});
    g.RevokeOwner(Vulkan);
    t.expect(g.Invoke(UNKNOWN) == Dispatch::FrontendDecode, "scope: arbitrary address still follows ordinary guest frontend semantics");
    t.expect(g.Invoke(VK_PFN) == Dispatch::Reject, "scope: formerly synthetic PFN stays distinguished from ordinary guest addresses");
  }

  {
    Graph g;
    g.Add({BridgeKind::HostCallback, VK_XSYNC_TRAMP, {Vulkan, X11}, State::Active, 0x50001000});
    t.expect(g.RevokeOwner(Other) == 0, "scope: unrelated load generation revokes no bridge");
    t.expect(g.Invoke(VK_XSYNC_TRAMP) == Dispatch::Guest, "scope: unrelated unload leaves callback bridge active");
  }

  std::printf("\nRESULT passed=%d failed=%d\n", t.pass, t.fail);
  return t.fail ? 1 : 0;
}
