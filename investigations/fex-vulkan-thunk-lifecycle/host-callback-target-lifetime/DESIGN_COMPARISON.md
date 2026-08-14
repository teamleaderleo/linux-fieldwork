# Guest thunk lifetime design comparison

## Purpose

This note separates two related but different lifetime problems and compares the repair families that have now been exercised in the owned FEX/Fieldwork research environment.

The narrow problem is the original FEX Vulkan guest-wrapper teardown failure: code or function pointers inside a FEX-owned guest thunk wrapper remain reachable after the application's ordinary loader reference is dropped.

The broad problem is host-to-guest callback ownership: a native-callable FEX trampoline can retain an arbitrary guest target that belongs to some other unloadable guest DSO.

A repair that is excellent for the first problem does not automatically solve the second.

## Current evidence summary

| Design family | Real FEX path | Survives wrapper `dlclose` | Real Vulkan PFN after close | Real Vulkan X11 callback after close | Handles arbitrary target DSO unload | Handles same-address ABA reuse | Complexity |
|---|---:|---:|---:|---:|---:|---:|---|
| guest constructor self-`dlopen` | yes | yes | yes in focused gate | registration path exercised | no | no | low-medium |
| ELF `DF_1_NODELETE` on shared guest thunks | yes | yes | yes | yes | no | no | low |
| cache erasure / key retirement only | partly | no ownership guarantee | no | no | no | no | deceptively low |
| generation in cache key only | model/source analysis | no ownership guarantee | no | no | no | lookup only | medium but insufficient |
| revocable/tombstoned published trampoline + owner retirement | yes | designed for unload | n/a to narrow wrapper pin | synthetic/integration family | yes in tested synthetic lifecycle matrix | yes | high |
| pin every guest module reachable by a published trampoline | native model; policy family | yes | yes in principle | yes in principle | yes if every target is pinned | address reuse avoided while pin lives | medium; potentially broad retention |

## Design A: constructor self-pin

### Mechanism

A shared FEX guest wrapper runs a constructor and acquires another loader reference to itself. The application may close its own handle, but the extra reference keeps the wrapper mapped.

### What it proved

The focused FEX-2608 self-pin differential changed the tested lifetime property from:

```text
baseline: after-final-app-close retained=0
```

to:

```text
candidate: after-final-app-close retained=1
old saved PFN after app close -> success
reopen -> same guest addresses
second close -> retained=1
```

The combined Vulkan gate then kept that lifetime candidate while restoring the real Vulkan guest constructor and applying only the demonstrated debug-report routing repair. Vulkan instance creation, routed debug-report create/destroy, instance destruction, application `dlclose`, and a saved Vulkan entrypoint after close all succeeded.

### Advantages

- very small conceptual change;
- directly matches the historical preload-pin positive control;
- can be enabled selectively by wrapper.

### Weak points

- the library identifies/reopens itself at initialization time;
- correctness depends on loader name/SONAME behavior and constructor ordering details;
- `RTLD_NOLOAD` hardening is desirable if this family is used, so failure to find the already-loaded wrapper cannot accidentally load a different object;
- expresses a linker/loader lifetime property indirectly in runtime code.

### Current assessment

Good diagnostic and valid proof of the lifetime hypothesis. No longer the preferred implementation mechanism now that the ELF `NODELETE` lane has stronger loader-level evidence.

## Design B: ELF `DF_1_NODELETE`

### Mechanism

Mark shared guest thunk DSOs with the GNU ELF `NODELETE` dynamic flag using the linker option:

```cmake
if (TARGET_TYPE STREQUAL "SHARED")
  target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
endif()
```

The dynamic loader then keeps the DSO's mappings present until process termination even after the ordinary open count reaches zero.

### Direct glibc contract result

An isolated glibc loader probe established:

```text
FIRST_LOAD init=1 fini=0
AFTER_DLCLOSE_RETAINED_FN init=1 fini=0
RTLD_NOLOAD handle=<non-null>
AFTER_NOLOAD init=1 fini=0
GLOBAL_PROMOTION default_fn=<same function>
AFTER_GLOBAL_PROMOTION init=1 fini=0
AFTER_FINAL_DLCLOSE init=1 fini=0
NODELETE_GLIBC_CONTRACT_OK
```

The DSO's destructor was recorded exactly once, at process exit:

```text
fini init=1 fini=1
```

This is a particularly useful contract property for guest thunk wrappers: ordinary application closes stop controlling executable mapping lifetime, but normal process-exit finalization is retained.

### Real Vulkan PFN result

A real x86-64 FEX Vulkan guest wrapper built with `DF_1_NODELETE` demonstrated:

- ELF `FLAGS_1: NODELETE` present;
- SONAME remains `libvulkan.so.1`;
- real Vulkan PFN succeeds before close;
- wrapper mapping remains after ordinary `dlclose`;
- the previously saved PFN still succeeds after close;
- reopen returns the same guest Vulkan entrypoint identity.

### Real Vulkan X11 callback result

A stronger ARM64/FEX integration lane created a real Vulkan instance with Xlib surface support and invoked `vkGetPhysicalDeviceXlibPresentationSupportKHR` before and after ordinary Vulkan `dlclose`.

Before close:

```text
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
BEFORE_CLOSE_XLIB result=0
```

After close, through the already-saved Vulkan PFN:

```text
AFTER_DLCLOSE_BEGIN_CALLBACK_TEST
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
AFTER_CLOSE_XLIB result=0
REAL_NODELETE_VULKAN_X11_CALLBACK_OK
```

This closes an important gap in the earlier combined gate: native Vulkan host code really did call back through FEX into guest-side X11 functions after the application's Vulkan loader handle was closed, and the guest Vulkan wrapper's unpacker/continuation code remained valid.

The guest X11 stub itself stayed loaded. Therefore this proves the **wrapper/unpacker** lifetime side of the callback edge, not arbitrary target-module ownership.

### Advantages

- directly tells the ELF loader the intended lifetime policy;
- no self-discovery or self-`dlopen` constructor;
- no added invocation-path checks;
- preserved function identities across close/reopen in the tested environment;
- destructor/finalizer still runs once at process exit under glibc;
- naturally protects generated guest thunk continuations and `CallbackUnpack` code for the entire process.

### Costs and questions

- every shared guest thunk marked this way remains resident after first load;
- memory footprint depends on how many wrappers a workload touches, not on every wrapper installed on disk;
- this intentionally changes observable `dlclose` unload semantics for FEX guest thunk DSOs;
- Linux/glibc is the demonstrated contract. FEX is a Linux project, so this is directly relevant, but the exact loader assumptions should remain explicit in any human-authored design discussion.

### Current assessment

**Preferred minimal lifetime mechanism for the narrow guest-wrapper problem, pending the original real `vulkaninfo` application gate.** It is cleaner than runtime self-pinning and is already demonstrated through both a real Vulkan PFN and a real Vulkan/X11 callback after close.

## Design C: cache erasure or raw key retirement only

### Mechanism

Delete the `(GuestUnpacker, GuestTarget)` cache entry when the corresponding guest mapping disappears, or add some unload state to future lookups.

### Why it is insufficient

The returned host trampoline is a published native function pointer. Native code can copy it into its own state. Deleting FEX's map entry changes future lookup behavior but does not reach out and revoke already-copied pointers.

The earlier native model demonstrated this directly: after cache erasure, an externally retained callback pointer still entered stale guest addresses and faulted.

There is a second limitation for the Vulkan teardown crash: an already-active guest-to-host call can need to return into guest thunk code. Cache retirement cannot repair an active continuation whose DSO has already unmapped.

### Current assessment

Useful bookkeeping and diagnostics, not a complete lifetime repair.

## Design D: generation in the cache key only

### Mechanism

Associate a module generation with `(GuestUnpacker, GuestTarget)` so a newly loaded DSO at the same virtual address does not hit an old cache entry.

### Why it is insufficient alone

It solves only future lookup ambiguity. An old native pointer already stored by host code can still be called without consulting the cache.

Therefore generation must participate at **invocation/revocation time**, or the underlying guest mapping must remain alive.

### Current assessment

Helpful component of a revocable design, not a standalone fix.

## Design E: revocable/tombstoned published trampoline

### Mechanism

Keep the native trampoline address stable, but attach state that can be invalidated before a guest module disappears. Invocation checks that the callback's owner/module generation is still current before entering guest execution. Unload retires ownership and tombstones stale callbacks.

A real FEX-2608 research integration lane now exercises this family with explicit retirement helpers, coherent locking, owner tracking, and callback tombstones.

### Tested matrix

The integrated lane passed these lifecycle families:

- different-address unload/reload;
- forced same-address ABA unload/reload;
- thread-local/cache-state update paths;
- multiple owners for the same callback state.

The expected old-callback behavior is deliberate rejection rather than accidental execution of a new module that reused the same virtual address. Freshly registered/current callbacks continue to work.

### Advantages

- permits actual guest target DSO unloading;
- can distinguish same virtual address across generations;
- already-published native callback pointers can be made safely stale rather than dangling;
- scales to the broad arbitrary-`GuestTarget` problem.

### Costs

- much more state and synchronization than `NODELETE`;
- unload order becomes part of correctness;
- all published native callback owners need a coherent invalidation rule;
- races between invocation and retirement need explicit handling;
- API semantics need to answer when native code has really stopped retaining a callback;
- active callbacks/frames must be protected while in flight.

### Current assessment

**Leading design family for the broad arbitrary-target unload problem if FEX wants to preserve unloadability.** It is more machinery than the original Vulkan wrapper crash appears to require.

## Design F: pin every reachable target module

### Mechanism

A published trampoline acquires/owns lifetime references for modules containing both `GuestUnpacker` and `GuestTarget`, releasing them only when native callback ownership is known to end.

### Advantages

- simple invocation path;
- no stale generations while the pin is active;
- naturally protects arbitrary target code as well as unpacker code.

### Problem

FEX's generic trampoline API currently returns a raw native function pointer and does not pair publication with an explicit release callback. Without an owner-lifetime API, the safe generic release point may be process exit, which can make this effectively a much broader `NODELETE` policy for arbitrary guest DSOs.

### Current assessment

Simple if callback lifetime is process-wide or an API-specific unregister point exists. Less attractive as a universal implicit policy for arbitrary application DSOs.

## Narrow versus broad repair decision

### Narrow: original Vulkan guest-wrapper teardown

Evidence currently points toward this policy:

> Once a shared FEX guest thunk wrapper has been loaded, its executable mappings remain resident until process exit.

Why this fits:

- historical `libvulkan-guest.so` pin changes exit 139 to exit 0;
- bogus preload does not;
- focused self-pin differential succeeds;
- combined real Vulkan routing/lifetime gate succeeds;
- real `NODELETE` Vulkan PFN survives close;
- real X11 callback through saved Vulkan state survives close;
- glibc `NODELETE` semantics preserve one process-exit finalization.

The original real `vulkaninfo --summary` teardown gate remains the final application-level discriminator for this narrow repair.

### Broad: arbitrary host-to-guest callback target DSO unload

The policy question is different:

> What owns a guest target module after native code has received a callback pointer capable of entering it?

`NODELETE` on FEX's own wrappers does not answer that. A target in a separate application DSO can still disappear.

For this broad problem, the choice is principally between:

- owning/pinning the target module for the callback's lifetime; or
- revoking/tombstoning the published trampoline before target unload, with generation-aware invocation checks and in-flight synchronization.

The integrated FEX-2608 retirement/tombstone matrix makes the latter a demonstrated research direction rather than a theoretical one.

## Recommended investigation order

1. Finish the real x86-64 distro `vulkaninfo --summary` llvmpipe gate with routing + wrapper retention and no preload workaround.
2. If it exits 0 twice, treat the narrow wrapper-lifetime repair as application-level demonstrated.
3. Compare constructor self-pin versus ELF `NODELETE`; current evidence favors `NODELETE` as the cleaner mechanism.
4. Measure touched-wrapper resident-memory footprint before choosing all-shared-wrapper versus selective wrapper policy.
5. Keep arbitrary `GuestTarget` unload as a separate generic callback-lifetime project. Reuse the already-green revocation/ABA/multi-owner lane rather than reproducing the same matrix from scratch.
6. Do not package AI-authored FEX source changes as an upstream contribution. A human can use these receipts to independently author/review any contribution under FEX's repository rules.

## Administrative note

The user-owned FEX fork contains many disposable research branches. They are acceptable provenance and do not need to be force-cleaned before investigation continues. Linux Fieldwork remains the durable source for causal summaries, test receipts, design comparisons, and next-step boundaries.
