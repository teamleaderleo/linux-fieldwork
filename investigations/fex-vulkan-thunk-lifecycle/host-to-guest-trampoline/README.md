# Host→guest callback trampoline lifetime investigation

This note follows the guest-thunk unload failure from the opposite direction: host→guest callback trampolines created by `GuestcallToHostTrampoline` / `MakeHostTrampolineForGuestFunction`.

It is part of the investigation behind:

- https://redirect.github.com/teamleaderleo/linux-fieldwork/pull/669
- https://redirect.github.com/teamleaderleo/linux-fieldwork/issues/672

No FEX upstream issue, pull request, review, comment, or branch mutation was performed by this work. Source changes and tests described here are research artifacts for owned/local trees.

## Executive result

`GuestcallToHostTrampoline` has a real generic lifetime defect.

A trampoline is cached by the raw pair `(GuestUnpacker, GuestTarget)`. The generated host executable trampoline permanently embeds those guest virtual addresses. The cache is owned by `ThunkHandler_impl`, which lives independently of individual guest DSOs. Guest `munmap`/DSO unload invalidates translated guest code and VMA state, but there is no path from guest unload to this trampoline cache. There is also no module identity, mapping identity, unload epoch, or generation in the cache key or instance record.

Therefore:

1. a trampoline can outlive the guest DSO containing `GuestUnpacker` or `GuestTarget`;
2. a native host library may still hold a copy of that trampoline after the cache entry itself is erased;
3. unloading and reloading can reuse the same guest virtual addresses, making a raw-address cache entry silently refer to a later DSO generation;
4. cache erasure alone cannot revoke already-published host function pointers;
5. the safe rule is that every guest executable address reachable through a published host trampoline must remain valid for the full invocation lifetime of that trampoline, or the trampoline must use revocable generation-aware state checked before guest entry.

Vulkan is a strong reproducer because its guest initialization passes guest libX11 function addresses together with `CallbackUnpack<...>::Unpack` code compiled into `libvulkan-guest.so`, while the host Vulkan thunk stores the resulting native callback pointers in a process-long `X11Manager` object.

The mechanism is proven as a separate generic bug. Its direct responsibility for the exact final `vulkaninfo` teardown branch remains to be demonstrated with entry-time instrumentation.

---

## ELI5

FEX sometimes has to let native ARM code call a function that belongs to the emulated x86 program.

Think of that as giving the ARM library a phone number for an x86 callback.

FEX cannot hand over the x86 function address directly, so it builds a tiny native helper — a trampoline. The trampoline remembers two x86 addresses:

- where the real guest function lives (`GuestTarget`);
- a guest helper that unpacks arguments and calls it (`GuestUnpacker`).

The native library keeps the trampoline pointer and calls it later.

The problem is that the guest `.so` containing one of those remembered addresses can be unloaded. Linux then removes that code from memory. The trampoline still exists and still remembers the old numeric address.

So the machine can reach this state:

```text
host library still owns callback pointer
              |
              v
native trampoline still exists
              |
              +--> remembers old GuestUnpacker address
              |
              +--> remembers old GuestTarget address

but guest DSO has been dlclose()'d and unmapped
```

Calling the trampoline after that is equivalent to calling a function pointer into freed executable memory.

There is a second problem. Linux often reuses virtual addresses when a DSO is loaded again. If a new generation lands at the same addresses, the cache sees the same numbers and can mistake the new mapping for the old lifetime.

That means an old callback can appear to come back to life and execute code from a later generation.

---

## Source-level lifecycle map

### Creation path

```text
guest code has callback function pointer
        |
        | GuestTarget
        | GuestUnpacker = CallbackUnpack<signature>::Unpack
        v
AllocateHostTrampolineForGuestFunction()
        |
        v
fexthunks_fex_allocate_host_trampoline_for_guest_function
        |
        v
ThunkFunctions::AllocateHostTrampolineForGuestFunction
        |
        v
MakeHostTrampolineForGuestFunction
        |
        +--> key = { GuestUnpacker, GuestTarget }
        |
        +--> look up GuestcallToHostTrampoline
        |
        +--> allocate/copy native executable trampoline if absent
        |
        +--> embed:
        |       HostPacker
        |       CallCallback
        |       GuestUnpacker
        |       GuestTarget
        |
        v
return native function pointer to host thunk/library
```

### Invocation path

```text
native host library
        |
        | calls returned function pointer
        v
HostToGuestTrampolineTemplate instance
        |
        | custom ABI points at embedded instance info
        v
host CallbackUnpack<F>::CallGuestPtr
        |
        v
ThunkHandler_impl::CallCallback(GuestUnpacker, ...)
        |
        v
CTX->HandleCallback(..., GuestUnpacker)
        |
        v
guest CallbackUnpack<...>::Unpack
        |
        v
guest GuestTarget
```

### Guest unload path

```text
guest dlclose()
        |
        v
guest loader munmap(s)
        |
        v
FEX GuestMunmap
        |
        +--> TrackMunmap
        |      \--> VMATracking.DeleteVMARange
        |
        +--> InvalidateCodeRangeIfNecessary
               \--> translated guest code invalidation
```

There is no corresponding edge from guest unload into `GuestcallToHostTrampoline`.

---

## Relevant FEX source

Current source read used commit `71afe476751deac24adabd1adb575fd2337b6e0a`; the retained 2608 runtime investigation used `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

Primary files:

- `Source/Tools/LinuxEmulation/Thunks.cpp`
  - https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/Source/Tools/LinuxEmulation/Thunks.cpp
- `ThunkLibs/include/common/Guest.h`
  - https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/include/common/Guest.h
- `ThunkLibs/include/common/Host.h`
  - https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/include/common/Host.h
- `Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsSMCTracking.cpp`
  - https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsSMCTracking.cpp
- `ThunkLibs/libvulkan/Guest.cpp`
  - https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/libvulkan/Guest.cpp
- `ThunkLibs/libvulkan/Host.cpp`
  - https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/libvulkan/Host.cpp
- `ThunkLibs/include/common/X11Manager.h`
  - https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/include/common/X11Manager.h
- `ThunkLibs/libGL/libGL_Guest.cpp`
  - https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/libGL/libGL_Guest.cpp

---

## Exact cache and instance state

The core key is:

```cpp
struct GuestcallInfo {
  uintptr_t GuestUnpacker;
  uintptr_t GuestTarget;

  bool operator==(const GuestcallInfo&) const noexcept = default;
};
```

The instance record embedded directly into executable trampoline memory is:

```cpp
struct TrampolineInstanceInfo {
  void* HostPacker;
  uintptr_t CallCallback;
  uintptr_t GuestUnpacker;
  uintptr_t GuestTarget;
};
```

The handler owns:

```cpp
fextl::unordered_map<GuestcallInfo,
                     HostToGuestTrampolinePtr*,
                     GuestcallInfoHash>
  GuestcallToHostTrampoline;
```

`MakeHostTrampolineForGuestFunction()` does the following:

1. build `GuestcallInfo { GuestUnpacker, GuestTarget }`;
2. check the map under a shared lock;
3. retry under an exclusive lock;
4. allocate a 16 KiB anonymous `PROT_READ | PROT_WRITE | PROT_EXEC` slab when needed;
5. copy `HostToGuestTrampolineTemplate` into the slab;
6. write the four instance fields into the copied template;
7. store the trampoline pointer in `GuestcallToHostTrampoline`;
8. return the trampoline pointer.

A repeated request with the same raw pair returns the existing trampoline.

### Lifetime table

| Property | Current behavior |
| --- | --- |
| Cache key | raw `(GuestUnpacker, GuestTarget)` virtual addresses |
| Trampoline allocation | anonymous host executable mapping |
| Embedded guest state | raw `GuestUnpacker` and `GuestTarget` |
| Cache owner | `ThunkHandler_impl` |
| Per-entry destructor/release | none found |
| Guest VMA association | none |
| ELF/module association | none |
| DSO generation/epoch | none |
| Guest unload invalidation | none |
| Protection from address reuse | none |
| Revocation of copies held by host code | none |

### Adjacent lifetime smell

`ThunkHandler_impl` contains a `Libs` set and an explicit comment saying it would ideally track when a library is unloaded and remove it before the backing memory disappears. The host→guest trampoline cache has no corresponding tracking.

---

## What owns a trampoline?

There are two owners to distinguish.

### 1. FEX owns the allocated trampoline memory and cache entry

The executable instance is allocated by `ThunkHandler_impl`, and the map entry is held by the handler.

There is no individual free/release API for a generated trampoline.

### 2. Native code can own copies of the returned function pointer

A host thunk can store the returned pointer indefinitely.

This means removing a cache entry cannot revoke copies already held elsewhere.

This point kills the simplest proposed fix:

```text
on guest unload:
    erase cache entry
```

That only prevents future lookups. A native library holding the old pointer can still call it.

---

## Why Vulkan is such a useful reproducer

Vulkan `Guest.cpp::OnInit()` does roughly this for several X11 helpers:

```cpp
void* libx11 = dlopen("libX11.so.6", RTLD_LAZY);

fexfn_pack_Vulkan_SetGuestXSync(
  (uintptr_t)dlsym(libx11, "XSync"),
  (uintptr_t)CallbackUnpack<decltype(XSync)>::Unpack);
```

That pair has two separate guest owners:

```text
GuestTarget   = XSync in guest libX11.so.6
GuestUnpacker = CallbackUnpack<XSync>::Unpack in libvulkan-guest.so
```

The host Vulkan thunk calls `MakeHostTrampolineForGuestFunctionAt()` and stores the resulting native callback in the static `x11_manager`.

So the resulting lifetime graph is:

```text
host libvulkan thunk / static x11_manager
                 |
                 | native callback pointer
                 v
host executable trampoline
                 |
                 +--> GuestTarget   -> guest libX11
                 |
                 +--> GuestUnpacker -> guest libvulkan-guest.so
```

If `libvulkan-guest.so` is unloaded while the host thunk remains resident, the trampoline can retain a valid target plus a dead unpacker.

That is a particularly clean demonstration that the logical callback owner and the DSO containing its unpacker can have different lifetimes.

The same class appears outside Vulkan. `libGL_Guest.cpp::OnInit()` creates host-callable callbacks using `CallbackUnpack<...>::Unpack` for X11 helpers and `malloc`, so the lifetime rule belongs in generic thunk machinery.

---

## Address reuse and generation confusion

Virtual addresses are reusable identifiers.

Suppose generation 1 maps:

```text
GuestUnpacker = 0x70001000
GuestTarget   = 0x70002000
```

The cache creates:

```text
key {0x70001000, 0x70002000} -> trampoline A
```

Then generation 1 unloads.

Later generation 2 maps at the same addresses:

```text
GuestUnpacker = 0x70001000
GuestTarget   = 0x70002000
```

The cache lookup sees the same integers and returns trampoline A.

The cache cannot distinguish:

```text
same addresses, same lifetime
```

from:

```text
same addresses, completely different DSO generation
```

An old trampoline therefore moves through three states without its own bytes changing:

```text
generation 1 loaded:   valid

generation 1 unloaded: dangling

generation 2 reuses VA: numerically valid again,
                         semantically rebound to new code
```

This is generation confusion.

Adding a generation only to the map key would prevent the cache from returning the old entry to a new lookup, but would still leave old native copies callable. A complete generation solution needs validity checked by the trampoline or by stable indirection used by the trampoline.

---

## Synthetic reproducer

The files beside this README build a native analogue of the FEX mechanism:

- `guest.c`: tiny unloadable DSO containing a target and unpacker;
- `repro.c`: executable trampoline cached by raw `(unpacker,target)`;
- `candidates.c`: pinning, invalidation-only, and generation-guard experiments.

The test intentionally isolates the lifetime contract. It does not claim to execute FEX guest code.

### Build

```sh
gcc -shared -fPIC -O2 -DGEN=1 guest.c -o libguest_v1.so
gcc -shared -fPIC -O2 -DGEN=2 guest.c -o libguest_v2.so
gcc -O2 -Wall -Wextra repro.c -ldl -o repro
gcc -O2 -Wall -Wextra candidates.c -ldl -o candidates

./repro
./candidates
```

### Observed primary run

```text
v1 target=0x7fd47c9ab100 unpacker=0x7fd47c9ab110 tramp=0x7fd47c9a9000 result=1017
mapped-before-close=1
mapped-after-close=0
stale-call-signal=11
v2 target=0x7fd47c9ab100 unpacker=0x7fd47c9ab110 tramp=0x7fd47c9a9000 result=2027
address-pair-reused=1 cache-trampoline-reused=1
```

This one run demonstrates:

- the DSO mapping disappeared after `dlclose`;
- the executable host trampoline survived;
- calling that retained trampoline while the DSO was absent produced SIGSEGV;
- the replacement DSO reused the exact target+unpacker addresses;
- the raw-address cache returned the same old trampoline;
- that same trampoline then executed generation-2 code.

---

## Candidate lifecycle implementations

### Candidate A — erase affected cache entries on unload

Concept:

```text
guest mapping removal
    |
    v
find all trampoline entries where
GuestTarget or GuestUnpacker intersects removed guest range
    |
    v
erase entries
```

Result in the synthetic test:

```text
[invalidation-only]
cache-erased-but-external-pointer stale-child=-11
```

Meaning: cache invalidation is useful but insufficient. Native code can still hold the trampoline pointer.

This candidate should be kept as bookkeeping even when a stronger lifetime policy is chosen because it prevents future cache hits and supplies diagnostics.

### Candidate B — pin guest code while a trampoline can be called

Concept:

```text
published host trampoline
    |
    +--> owns/refcounts guest mapping containing GuestUnpacker
    |
    +--> owns/refcounts guest mapping containing GuestTarget
```

Observed:

```text
[pinning]
before close result=1013 mapped=1
after ordinary close result=1013 mapped=1
after pin release mapped=0 stale-child=-11
```

This is mechanically safe: the raw addresses remain mapped for as long as the trampoline may execute them.

The difficult part is determining the final native release point. The current API hands out a raw host function pointer and supplies no release notification. Therefore precise refcounting cannot be inferred from `GuestcallToHostTrampoline` alone.

A conservative process-lifetime pin is safe with the current API. It may retain guest DSOs longer than applications expect.

### Candidate C — revocable generation-aware indirection

Concept:

```text
host trampoline
    |
    v
stable slot:
    GuestUnpacker
    GuestTarget
    generation
    valid
```

Unload marks the slot invalid before guest executable memory disappears.

Reload creates a new generation.

The trampoline checks `valid` and `generation` before entering guest code.

Observed:

```text
[generation-guard]
live result=1013
after-unload guarded-result=-7777
after-reload same-address raw-pair=1 guarded-old-result=-7777
```

The test uses `-7777` only as an observable synthetic sentinel. Generic FEX cannot safely invent an arbitrary callback return value. A production implementation needs a defined expired-callback behavior, likely a controlled fatal diagnostic unless the higher-level thunk can unregister/cancel the callback before unload.

This candidate solves same-address resurrection because the old external trampoline remains tied to the old invalid slot.

---

## Recommended lifecycle rule

The rule should be phrased independently of Vulkan:

> A published host trampoline owns the validity lifetime of every guest executable address it can enter. Raw guest virtual addresses do not identify that lifetime.

Two implementation families can satisfy the rule:

1. **ownership/pinning:** retain every guest module/range containing `GuestUnpacker` or `GuestTarget` until every native user of the trampoline is finished;
2. **revocable callbacks:** make the trampoline consult stable generation-aware state that is invalidated before those guest ranges are unmapped, and ensure native APIs stop calling or receive a defined expired-callback failure.

With the current raw-pointer API and no release contract, conservative pinning is the simplest fully safe policy. Generation-aware state is the cleaner long-term design if callback unregistration/lifetime can be represented.

Range/module association should exist in either design.

---

## Proposed FEX instrumentation

### At trampoline creation / cache lookup

Record:

```text
trampoline=<host address>
cache=<hit|new>
GuestTarget=<guest address>
GuestTarget VMA=<base..top>
GuestTarget resource=<file/module identity>
GuestTarget generation=<mapping epoch>
GuestUnpacker=<guest address>
GuestUnpacker VMA=<base..top>
GuestUnpacker resource=<file/module identity>
GuestUnpacker generation=<mapping epoch>
HostPacker=<host address>
```

### At guest mapping removal

Before deleting guest VMA/resource state, find every trampoline for which either embedded guest address intersects the removed range and print:

```text
THUNK-LIFETIME unload overlap
trampoline=<...>
removed-range=<...>
target=<...> target-overlap=<0|1>
unpacker=<...> unpacker-overlap=<0|1>
```

For a prototype fix, mark associated slots invalid at this point before host `munmap` completes.

### At trampoline invocation

Immediately before `HandleCallback`, validate/query both embedded guest addresses and print:

```text
THUNK-LIFETIME invoke
trampoline=<...>
GuestTarget=<mapped current generation | missing | reused>
GuestUnpacker=<mapped current generation | missing | reused>
```

For the current Vulkan teardown, the discriminating event is an invocation where `GuestUnpacker` points into the old `libvulkan-guest.so` range after that range has disappeared.

---

## Relationship to the retained Vulkan teardown crash

The earlier investigation established:

- after the callback-routing diagnostic change, `vulkaninfo` reaches enumeration and then exits 139 during teardown;
- llvmpipe exhibits the same teardown crash, separating it from Venus;
- at the final guest SIGSEGV, the guest RIP lies in the old unmapped `libvulkan-guest.so` image range;
- the corresponding image offset resolves into generated `CallHostFunction<...>` code in `ThunkLibs/include/common/Guest.h`;
- suppressing guest `dlclose` changes the result to exit 0;
- a bogus preload leaves exit 139;
- pinning only `libvulkan-guest.so` changes the result to exit 0.

Those results prove an execution-after-guest-thunk-unload failure.

The host→guest trampoline investigation adds another specific way executable references can survive that unload.

### What is proven

A separate generic defect exists:

```text
host callback trampoline lifetime > guest code lifetime
```

Vulkan creates concrete trampolines whose `GuestUnpacker` belongs to `libvulkan-guest.so` and stores them in long-lived native host state.

### What remains to connect

The recorded terminal RIP resolved near/inside generated `CallHostFunction<...>`, while a direct stale host→guest trampoline would be expected first to enter a `CallbackUnpack<...>::Unpack` guest helper.

That means the available trace does not yet prove that the exact terminal `vulkaninfo` branch came through `GuestcallToHostTrampoline`.

Possible outcomes of entry-time instrumentation:

#### Outcome 1 — stale trampoline invocation appears immediately before the crash

```text
host native callback
 -> stale HostToGuestTrampoline
 -> unmapped libvulkan GuestUnpacker
 -> guest instruction-fetch fault
```

Then this mechanism directly explains the teardown crash.

#### Outcome 2 — no stale trampoline invocation appears

Then there are at least two independent unload defects:

1. the already-observed stale continuation/execution path into the unloaded guest thunk;
2. the independently proven host→guest callback trampoline lifetime defect documented here.

This is why Vulkan should remain the reproducer, not the assumed owner of the lifetime rule.

---

## Negative controls

### Existing Vulkan controls

| Variant | Result | Meaning |
| --- | --- | --- |
| callback routing + normal unload + llvmpipe | exit 139 | Venus is unnecessary |
| callback routing + bogus preload | exit 139 | preload warnings alone do not cure failure |
| callback routing + no-op guest `dlclose` | exit 0 | unload is causal |
| callback routing + pinned `libvulkan-guest.so` + llvmpipe | exit 0 | retaining that guest image is sufficient |
| callback routing + pinned `libvulkan-guest.so` + Venus | exit 0 | same lifetime effect on real Venus path |

### Synthetic controls

| Probe | Result | Meaning |
| --- | --- | --- |
| `/proc/self/maps` before close | DSO present | initial state valid |
| `/proc/self/maps` after close | DSO absent | stale test really exercises unmapped code |
| call stale trampoline in child | SIGSEGV | embedded guest addresses can outlive mapping |
| extra loader reference | callback keeps working | pinning preserves validity |
| erase cache entry only | stale external pointer still SIGSEGVs | cache ownership and published pointer lifetime differ |
| reload replacement DSO | exact address pair reused | virtual-address generation reuse is real |
| raw cache after reuse | old trampoline reused | current key cannot distinguish generations |
| generation-validity guard | old trampoline stays invalid | stable revocable state prevents resurrection |

---

## Regression-test form

A FEX regression test should avoid Vulkan as its only trigger.

Suggested form:

1. create a tiny guest DSO containing a callback target and guest unpacker;
2. expose a host thunk operation that receives them and obtains a host-callable trampoline;
3. host side stores that trampoline outside the guest DSO lifetime;
4. invoke once while loaded and assert success;
5. guest `dlclose`s the DSO;
6. verify FEX mapping/resource state says the code range is gone or intentionally pinned according to the selected lifecycle rule;
7. attempt controlled host invocation after unload;
8. reload the DSO and attempt to obtain same virtual addresses;
9. verify stale generation cannot silently execute as the new generation.

Expected test behavior depends on the chosen rule:

### Pinning rule

- mapping remains present while published trampoline is live;
- post-`dlclose` callback remains valid;
- final explicit release permits unmap.

### Revocable rule

- mapping may disappear;
- old callback produces a deterministic expired-callback result/diagnostic;
- same-address reload creates a distinct generation;
- old host pointer remains expired.

The test should separately cover:

- target and unpacker in the same guest DSO;
- target in DSO A, unpacker in DSO B;
- unload only A;
- unload only B;
- reload at different addresses;
- reload at identical addresses;
- cache hit while generation is unchanged.

The split-DSO case directly models Vulkan's X11 target plus Vulkan-thunk unpacker arrangement.

---

## Exact remaining uncertainty

1. Whether a `GuestcallToHostTrampoline` invocation occurs immediately before the retained `vulkaninfo` teardown SIGSEGV.
2. Which specific generated callback, if any, supplies that invocation.
3. Whether the recorded `State.rip` in the old image is the exact invalid entry, a later continuation/return path, or a nearby JIT bookkeeping value. The earlier investigation already records the limitation on JIT RIP precision.
4. What generic release contract FEX wants for published native callback pointers. Current code exposes no final-release notification.
5. Whether FEX wants guest thunk DSOs to remain resident for process lifetime as a policy, or wants unloadable guest thunks plus explicit callback revocation.

Everything below that boundary is established by source and the synthetic test:

- raw unloadable guest addresses are embedded in host executable trampoline state;
- the trampoline cache is process/handler-owned rather than guest-module-owned;
- guest unload has no trampoline invalidation/module association;
- stale invocation after unmap is possible;
- cache erasure alone cannot revoke native copies;
- same-address reload can cause generation confusion;
- pinning makes the raw-address design safe;
- generation-aware validity can prevent stale pointer resurrection.

---

## Engineering boundary

Any FEX source edits made from this investigation are diagnostic/prototype research only. FEX's contribution policy remains the upstream-submission boundary. A human can independently implement or translate the evidence into an upstream-compliant change.
