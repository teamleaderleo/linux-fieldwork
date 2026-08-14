# Selective NODELETE wrapper-state audit — 2026-08-14

## Scope

This note reviews the proposed selective `DF_1_NODELETE` set for FEX guest thunk wrappers:

- Vulkan
- GL
- Wayland-client
- CUDA

The question is not only memory footprint. `NODELETE` changes loader lifetime: constructor state remains alive across ordinary `dlclose`/reopen and destructors are deferred to process shutdown. A safe containment policy therefore needs the retained wrapper state to be compatible with process-lifetime FEX bridge state.

This is an owned-fork research conclusion, not an upstream-ready patch.

## Common guest-thunk loader behavior

`ThunkLibs/include/common/Guest.h` defines:

```cpp
#define LOAD_LIB_BASE(name, init_fn)                   \
  __attribute__((constructor)) static void loadlib() { \
    LoadlibArgs args = {#name};                        \
    fexthunks_fex_loadlib(&args);                      \
    if ((init_fn)) ((void (*)())init_fn)();            \
  }

#define LOAD_LIB(name) LOAD_LIB_BASE(name, nullptr)
#define LOAD_LIB_INIT(name, init_fn) LOAD_LIB_BASE(name, init_fn)
```

There is no paired common guest-thunk destructor hook here.

An independent glibc runtime-promotion experiment on the owned FEX fork also verifies base-namespace `NODELETE` semantics: after close the DSO remains resident/callable and `RTLD_NOLOAD` still finds it; reopening uses the retained object rather than re-running its constructor. Run `31775371984` is green.

Therefore selective `NODELETE` means these FEX wrappers become process-lifetime runtime objects after first load.

## Vulkan

`ThunkLibs/libvulkan/Guest.cpp` has two kinds of persistent wrapper state that are directly relevant to the unload bug class.

### Dynamic-PFN invoker map

A process-global `HostPtrInvokers` table maps Vulkan API names to addresses of generated guest `CallHostFunction<...>` instantiations. Dynamic native Vulkan PFNs are linked to those guest addresses through `LinkAddressToFunction(H, T)`.

Those T addresses are exactly the kind of executable wrapper targets that become stale if the guest Vulkan DSO is unmapped while FEX still has H→T state.

Keeping the wrapper resident therefore preserves the generated code whose addresses FEX publishes.

### Constructor-published X11 callback helpers

`OnInit()` opens guest `libX11.so.6` and publishes guest X11 function addresses plus Vulkan-owned `CallbackUnpack<...>::Unpack` addresses to the host side. `LOAD_LIB_INIT(libvulkan, OnInit)` runs this during first wrapper load.

Current FEX host-side callback/trampoline state can outlive an ordinary guest Vulkan `dlclose`; it has no matching DSO-generation retirement API. Reconstructing a new guest Vulkan wrapper generation while those old host references survive is therefore unsafe under the current lifetime model.

With `NODELETE`, `OnInit()` runs once and the published wrapper-owned unpacker code remains executable for the process. That is more coherent with current host bridge lifetime than unloading/re-running the constructor into a new generation.

Limit: the X11 `GuestTarget` belongs to another guest DSO. Vulkan wrapper residency protects the Vulkan-owned unpacker, not arbitrary target-DSO lifetime.

## GL

`ThunkLibs/libGL/libGL_Guest.cpp` follows essentially the same two patterns:

- a persistent proc-name→generated guest-invoker table used by `glXGetProcAddress`-style dynamic H→T linking;
- `OnInit()` publishes guest X11 helpers/callback unpackers to host-side GL state.

Again, the retained state is primarily FEX bridge infrastructure whose executable addresses can escape ordinary DSO scope under the current implementation.

Keeping GL resident prevents those published generated targets and unpackers from becoming unmapped. Re-running `OnInit()` after an unload would create a new guest generation while old host-side references are not generationally retired, so process-lifetime residency is the safer behavior under the existing bridge model.

The same arbitrary-X11-target caveat applies as for Vulkan.

## Wayland-client

Wayland has an even more explicit host-retention relationship.

`wl_proxy_add_listener` replaces a guest callback table with host-callable pointers created through `AllocateHostTrampolineForGuestFunction`. The native/host-side `wl_proxy` retains that substitute callback table until proxy destruction or replacement.

The guest wrapper also has `OnInit()` logic that late-initializes many exported `wl_interface` objects by exchanging host interface data into guest wrapper globals. `LOAD_LIB_INIT(libwayland-client, OnInit)` runs this once per actual DSO load generation.

Process-lifetime wrapper residency therefore preserves:

- wrapper-owned callback unpacker code;
- late-initialized `wl_interface` globals;
- the code/data identity associated with host-retained listener trampolines.

This is preferable to destroying and recreating those wrapper objects while native objects may still retain FEX-created callback pointers.

Limit: listener `GuestTarget` functions are arbitrary application/other-DSO addresses. `NODELETE` on libwayland-client does not own those target lifetimes. The callback generation/revocation/lease design is still required for the generic case.

## CUDA

`ThunkLibs/libcuda/libcuda_Guest.cpp` is simpler:

- it has a process-global immutable `HostPtrInvokers` map from known CUDA proc names to generated guest `CallHostFunction` targets;
- `cuGetProcAddress_v2` obtains native host PFNs and links them to those guest wrapper targets through `LinkAddressToFunction`;
- it uses plain `LOAD_LIB(libcuda)`, with no wrapper-specific `OnInit()` state.

Thus CUDA has no constructor-owned callback registration state to reinitialize. `NODELETE` primarily preserves the generated wrapper targets and the immutable lookup table whose addresses participate in dynamic PFN bridging.

This is a particularly clean fit for process-lifetime wrapper residency.

## Destructor / reset concern

The common guest thunk loader macro has no unload destructor hook, and no selected wrapper audit found a deliberate teardown function paired with `LOAD_LIB[_INIT]` that application semantics require to run on each `dlclose`.

C++ global object destructors (for example an `unordered_map`) naturally move to process shutdown when the DSO is `NODELETE`. For these wrappers that is consistent with making the FEX-private bridge infrastructure process-lifetime.

This does **not** prove that every future state added to these libraries will be NODELETE-safe. The policy should remain explicit/selective so new mutable per-load state is reviewable.

## Footprint

The hosted ELF LOAD-footprint audit measured approximately:

- Vulkan: 300 KiB
- GL: 956 KiB
- Wayland-client: 40 KiB
- CUDA: 188 KiB

Total page-rounded retained LOAD footprint: about **1.45 MiB**.

That is small enough that selective residency is a credible containment mechanism rather than a broad “pin every thunk” policy.

## Close/reopen interpretation

The most important semantic point is that current FEX already lets bridge state escape the guest wrapper's ordinary DSO lifetime. Under that implementation, a real unload/reload does not produce a clean fresh lifetime: old native PFN/custom-IR/callback state can still refer to the previous guest generation.

For the selected wrappers, `NODELETE` deliberately makes the guest-side executable infrastructure match the longer host-side lifetime that FEX already has.

So the immediate tradeoff is not:

> perfect true unload semantics versus a convenient leak.

It is closer to:

> keep FEX-private wrapper infrastructure alive coherently, or physically unmap it while FEX may still retain executable dependencies on it.

A future fully generational bridge implementation can revisit true unload/reload semantics.

## Recommendation

Selective `DF_1_NODELETE` remains a strong staged containment candidate for Vulkan, GL, Wayland-client, and CUDA.

It should be paired conceptually with the generic callback repair rather than advertised as the complete lifetime solution:

1. selected FEX-owned wrappers remain process-resident;
2. arbitrary callback target generations are tracked/revoked and protected by execution leases;
3. a later full dynamic-PFN bridge ABI can make true unload/reload safe without relying on wrapper residency.

Regression coverage should include ordinary first load, final `dlclose`, reopen, repeated proc lookup/callback use, and process shutdown so future wrapper state changes cannot silently make the NODELETE policy unsafe.
