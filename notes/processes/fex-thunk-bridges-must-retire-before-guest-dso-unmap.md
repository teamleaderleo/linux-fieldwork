# FEX thunk bridges must retire before guest DSO unmap

## In simple words

FEX thunking lets x86 guest code call native host libraries. Some of the bridge machinery lives longer than the guest shared object that contains the bridge's guest-side helper code.

That creates a lifecycle trap:

```text
guest asks for native function pointer H
    ↓
FEX records H -> guest helper T
    ↓
T lives inside a guest thunk DSO
    ↓
guest dlclose() unloads that DSO
    ↓
T becomes unmapped
    ↓
if the H -> T bridge survives, a later use of H can jump to dead T
```

The reusable lesson is broader than Vulkan: **any executable bridge that contains a guest code address must have an owner whose lifetime is at most the lifetime of the guest image containing that address, or it must use an indirection that can be safely revoked/rebound before unmap.**

The concrete Vulkan investigation is [`../../investigations/fex-vulkan-thunk-lifecycle/`](../../investigations/fex-vulkan-thunk-lifecycle/). Its detailed teardown record is [`TEARDOWN_CHRONOLOGY.md`](../../investigations/fex-vulkan-thunk-lifecycle/TEARDOWN_CHRONOLOGY.md).

## Why this class is easy to create

Thunk systems cross several independently owned lifetimes:

1. **guest ELF lifetime** — `dlopen()` / `dlclose()` and the guest dynamic loader decide when guest code mappings appear and disappear;
2. **host library lifetime** — the native host DSO may remain resident for the entire emulator process;
3. **bridge metadata lifetime** — maps, callback records, generated trampolines, and caches may be owned by long-lived FEX objects;
4. **translated code lifetime** — JIT blocks can remain executable after the source operation that created them;
5. **in-flight execution lifetime** — another thread can already have selected a bridge while unload begins.

A bridge can therefore be logically created by one library load yet physically stored in a process-wide table. Ordinary guest `munmap()` invalidation only sees the guest virtual-address range. That is insufficient when the surviving bridge is keyed by a different address or resides in host-owned memory.

## Concrete FEX Vulkan example

At FEX-2608 (`e869aa644a16e4332cdc15c1ea0b4d13d482385d`), the guest Vulkan thunk returns native Vulkan function pointers to the guest. Before returning one, `MakeGuestCallable()` calls `LinkAddressToFunction(native_pfn, guest_invoker)`.

The guest invoker is a generated `CallHostFunction<...>` body inside `libvulkan-guest.so`.

On the FEX side, `LinkAddressToGuestFunction` installs a CustomIR entry:

```text
key:    native Vulkan PFN H
value:  guest thunk entrypoint T
```

The generated CustomIR block stores the original native entrypoint in guest `r11` and exits to the captured guest thunk entrypoint.

The critical ownership mismatch is that the registration is keyed by `H`, while the lifetime-sensitive executable target is `T`.

When `libvulkan-guest.so` is unloaded, guest-range code invalidation covers the old `T` range. It does not inherently identify a CustomIR entry keyed by `H` as belonging to that guest image. A cached CustomIR block can also execute after its generation-time handler lookup, so logging only `CustomIRHandlers.find()` misses an already-compiled stale redirect.

## A second independent stale-address class

FEX's host-to-guest callback trampoline cache stores raw guest addresses such as `GuestUnpacker` and `GuestTarget` in host-owned trampoline metadata. Vulkan initialization creates such trampolines for guest X11 helpers.

This means a complete solution cannot assume the dynamic-PFN CustomIR path is the only bridge type with guest-image lifetime. The same ownership rule must cover every externally reachable host-owned bridge containing guest code addresses.

## Why ordinary code invalidation is not the same as bridge retirement

Guest `munmap()` answers:

> Which guest virtual-address bytes stopped existing?

Bridge retirement must answer:

> Which host-owned executable paths can still select one of those bytes?

Those sets are related, but they are indexed differently.

A range invalidation for `[T_base, T_end)` can remove ordinary translated guest blocks originating in that range. It cannot safely retire `H -> T` unless FEX has retained enough ownership metadata to discover that `T` belongs to the retiring load.

## The lifecycle invariant

The safe ordering is conceptually:

```text
begin guest thunk unload
    ↓
block new bridge acquisitions for this load
    ↓
revoke or rebind every externally reachable bridge
    ↓
invalidate translated paths that embed retired destinations
    ↓
drain executions that already acquired the retiring generation
    ↓
unmap guest DSO
    ↓
reclaim retired bridge metadata
```

The key word is **before**. Cleaning metadata after physical unmap leaves a window where an already-selected or cached transfer can target dead guest code.

## Why "just pin the thunk forever" is useful but incomplete

Keeping the guest thunk resident makes stale destinations remain executable. In the Vulkan reproducer, pinning only `libvulkan-guest.so` changes exit 139 to exit 0, and replacing guest `dlclose()` with a no-op also changes exit 139 to exit 0.

That makes residency a strong diagnostic control and a possible compatibility workaround.

It does not repair ownership. Long-lived processes that load/reload thunk DSOs, namespace loaders, address reuse, aliases, ABI changes, and callback state still need explicit lifecycle semantics if unload is supported.

## Better implementation model

A robust design needs an identity for each guest thunk load, such as a generation/token owned by the loader-facing thunk layer.

Every bridge created during that load carries the token:

```text
load generation G
  ├─ native PFN H1 -> guest invoker T1
  ├─ native PFN H2 -> guest invoker T2
  ├─ host callback trampoline -> guest unpacker U1
  └─ translated/cache entries derived from those bridges
```

Unload of `G` can then retire all of them together.

If two live generations legitimately use the same native host PFN, the bridge table needs owner stacking or a stable host-owned indirection so retiring one generation can expose/rebind the surviving owner instead of deleting a shared key blindly.

## Why this probably survived for so long

This class hides behind normal success paths:

- most programs keep foundational graphics libraries loaded until process exit;
- process exit destroys the entire address space, so stale pointers never get a chance to fire;
- same-address reload can accidentally make stale state look valid;
- a host library can remain process-resident even though its guest thunk unloads, creating an asymmetric lifetime that ordinary native testing does not have;
- thunk registration and guest `dlclose()` live in different subsystems, so each local implementation can look correct in isolation;
- callbacks, dynamic PFNs, JIT caching, guest loader behavior, and host loader behavior only meet during unusual teardown/reload sequences;
- GPU failures usually draw attention toward drivers, while this one reproduces with llvmpipe and is actually in emulator thunk lifetime.

The lesson is to test bridge systems under explicit `load -> acquire callable -> use -> unload -> late-use/reload` scenarios, not only initialization and steady-state calls.

## Distinguishing trace for this class

For a suspected stale bridge, record these events in one ordered stream:

```text
MAP guest DSO generation G
REGISTER bridge source=H destination=T generation=G
BRIDGE_GENERATE/CACHE H -> T
BEGIN_UNLOAD generation=G
RETIRE bridge H -> T
INVALIDATE translated paths
DRAIN generation=G
MUNMAP guest DSO range containing T
BRIDGE_EXEC H -> T target_mapped=<0|1>
FAULT target=T caller=<...>
```

If `BRIDGE_EXEC` appears after `MUNMAP` with `target_mapped=0`, the lifetime violation is direct.

For FEX's dynamic-PFN CustomIR path, guest `r11` is especially useful because the generated bridge stores the original native entrypoint there before transferring to the guest thunk target.

## Evidence boundary

The Vulkan investigation demonstrates execution reaches an address in the former `libvulkan-guest.so` image after unload and that retaining that image repairs the failure. Source review establishes multiple FEX bridge objects capable of retaining guest code addresses beyond ordinary guest mapping lifetime.

The retained target run does not yet prove which surviving bridge performs the immediate final transfer. Dynamic-PFN CustomIR is the leading mechanism because the dead location resolves inside `CallHostFunction<...>`. Host-to-guest callback trampolines and an already-selected translated path remain competitors until the final caller is captured.

## Practical review checklist

When reviewing any thunk or FFI bridge that returns function pointers or accepts callbacks, ask:

- What object owns the bridge?
- What object owns every code address embedded in it?
- Can either side unload independently?
- What event begins retirement?
- Can new acquisitions race with retirement?
- How are cached translated paths revoked?
- How are already-running calls drained?
- Can a stable host address be rebound to a new guest load?
- What happens when a library reloads at a different guest base?
- Does same-address reuse hide stale state?

If those questions cannot be answered from explicit lifecycle metadata, teardown/reload deserves a dedicated test.