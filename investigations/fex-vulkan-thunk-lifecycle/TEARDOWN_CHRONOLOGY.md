# Teardown chronology — FEX Vulkan guest thunk

## TL;DR

The exit-139 failure is now narrowed to a lifetime mismatch around `libvulkan-guest.so`.

The guest Vulkan thunk is deliberately unloaded by `vulkaninfo`. FEX invalidates ordinary translated code for the unmapped guest address range, but FEX also owns longer-lived bridge objects that contain raw addresses into that guest DSO. The strongest survivor is the dynamic-Vulkan-PFN CustomIR mapping: a native Vulkan function pointer is registered as an FEX entrypoint whose generated block exits to a `CallHostFunction<...>` body inside `libvulkan-guest.so`.

When the guest DSO goes away, invalidating its guest VA range does not inherently retire a CustomIR block keyed by a different address: the native Vulkan PFN. A cached block can therefore remain capable of selecting the old guest target after the bytes have disappeared.

The retained failing run already proves the destination side of this chain: after successful Vulkan enumeration, FEX records an x86 instruction-fetch page fault at `0x7ffff7cd21f0`, inside the former guest Vulkan thunk range. Using the former image base `0x7ffff7c87000` gives offset `0x4b1f0`, which resolves inside generated `CallHostFunction<...>` code.

What remains unproved is the immediately preceding transfer. The next discriminator is therefore small: at the first attempted execution inside the retired Vulkan range, record the transfer kind, guest `r11`, guest stack pointer, and return PC. If `r11` equals a previously registered native Vulkan PFN, the CustomIR path is identified directly.

No new target execution was possible in the 2026-08-14 continuation session because the Fedora VM, local FEX tree, installed thunk, and retained core were not mounted into that runtime. Everything below is separated into retained target evidence, exact source behavior, and remaining runtime proof.

## Explain like I'm five

Think of FEX as a receptionist connecting two rooms.

- The x86 program lives in the **guest room**.
- The real ARM Vulkan driver lives in the **host room**.
- `libvulkan-guest.so` contains little guest-side helper functions that let calls cross between the rooms.

When `vulkaninfo` asks Vulkan for a function pointer, FEX does something clever. It gives the x86 program the address of the real native Vulkan function, but secretly writes down:

```text
if the x86 program tries to run native address H,
redirect it to guest helper T first
```

`T` lives inside `libvulkan-guest.so`.

At shutdown, `vulkaninfo` closes Vulkan. The Linux loader removes `libvulkan-guest.so` from the guest process. The helper address `T` becomes empty space.

The problem is that FEX still has cards in its filing cabinet that say:

```text
H -> T
```

and FEX also has cached translated blocks that can contain that same destination.

So the likely final sequence is:

```text
Vulkan works
  -> vulkaninfo destroys Vulkan objects
  -> vulkaninfo dlclose()s Vulkan
  -> libvulkan-guest.so disappears
  -> FEX still has H -> old T
  -> something uses H one more time
  -> FEX sends execution to old T
  -> old T is empty memory
  -> guest instruction-fetch page fault
  -> FEX turns that into guest SIGSEGV
  -> exit 139
```

Pinning the guest Vulkan thunk makes the crash disappear because `T` remains real memory. Making guest `dlclose()` a no-op has the same effect. A bogus preload changes nothing and still crashes. llvmpipe still crashes, so Venus/virtio is outside the core failure.

The one missing fact is **who performs that one last use**. The leading suspect is a cached CustomIR Vulkan redirect. A host-to-guest callback trampoline is a second real stale-address class. Ordinary guest code and loader return/resume remain lower-ranked alternatives until the final transfer is captured.

## Scope and source identity

- Internal carrier: [linux-fieldwork PR 669](https://github.com/teamleaderleo/linux-fieldwork/pull/669)
- Owning follow-up: [linux-fieldwork issue 672](https://github.com/teamleaderleo/linux-fieldwork/issues/672)
- Executed FEX revision: `FEX-2608` / `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- Owned source mirror: [teamleaderleo/FEX at FEX-2608](https://github.com/teamleaderleo/FEX/tree/e869aa644a16e4332cdc15c1ea0b4d13d482385d)
- Current upstream comparison used by the parent investigation: `71afe476751deac24adabd1adb575fd2337b6e0a`
- Vulkan-Tools application-side teardown cross-check: tag `vulkan-sdk-1.4.341.0`, commit `48a4bcbdf619e57204783f8c1a04c76c160ddd5b`
- External FEX links, when used, must use `https://redirect.github.com/...`
- FEX upstream interaction: none

## Retained target evidence

The controls from the parent investigation remain the authoritative execution evidence:

| Variant | Driver | Result |
| --- | --- | --- |
| normal post-callback-fix run | llvmpipe | enumeration succeeds, exit 139 |
| guest `dlclose()` replaced by no-op | llvmpipe | exit 0 |
| bogus/nonexistent preload | llvmpipe | exit 139 |
| only `libvulkan-guest.so` pinned | llvmpipe | exit 0 |
| pinned guest thunk | Venus / Apple M5 | exit 0; Venus enumerated |

At the stable terminal fault FEX recorded:

```text
State.rip = 0x7ffff7cd21f0
FaultToTopAndGeneratedException = true
Signal = 11
TrapNo = 14
si_code = 2
err_code = 21  # 0x15
```

`TrapNo=14` is an x86 page fault. `0x15` includes the instruction-fetch bit.

At crash time the old Vulkan guest address was unmapped. The retained map neighborhood contains a hole approximately:

```text
0x7ffff7c87000 - 0x7ffff7cdc000  [unmapped]
```

Treating `0x7ffff7c87000` as the former image base gives:

```text
0x7ffff7cd21f0 - 0x7ffff7c87000 = 0x4b1f0
```

`addr2line` and `objdump` against the retained guest thunk put `0x4b1f0` inside generated `CallHostFunction<...>` code from `ThunkLibs/include/common/Guest.h`.

This proves a transfer reaches the former guest thunk image after that image has disappeared. It does not by itself identify the preceding dispatch mechanism.

## Exact source lifecycle before teardown

### Guest DSO constructor

`ThunkLibs/include/common/Guest.h` defines `LOAD_LIB_INIT` as a constructor. Vulkan uses:

```text
LOAD_LIB_INIT(libvulkan, OnInit)
```

so guest load performs:

```text
constructor
  -> fexthunks_fex_loadlib("libvulkan")
  -> FEX ThunkHandler_impl::LoadLib("libvulkan")
  -> host libvulkan-host.so dlopen/init
  -> OnInit()
```

The helper API has no symmetric guest unload hook paired with `LOAD_LIB_INIT` in this revision.

Owned-source links:

- [Guest.h](https://github.com/teamleaderleo/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/ThunkLibs/include/common/Guest.h)
- [Vulkan Guest.cpp](https://github.com/teamleaderleo/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/ThunkLibs/libvulkan/Guest.cpp)
- [Thunks.cpp](https://github.com/teamleaderleo/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/Source/Tools/LinuxEmulation/Thunks.cpp)

### Host-to-guest callback registrations

Vulkan `OnInit()` loads guest X11 symbols and passes guest callback unpackers into host setup calls. FEX's generic trampoline allocator stores:

```text
HostPacker
CallCallback
GuestUnpacker
GuestTarget
```

inside `TrampolineInstanceInfo` and caches trampolines in `GuestcallToHostTrampoline` keyed by guest addresses.

This creates one independent stale-address class if `libvulkan-guest.so` unloads while those trampoline records survive.

### Dynamic Vulkan PFN registrations

`vkGetInstanceProcAddr()` and `vkGetDeviceProcAddr()` call the native Vulkan lookup through the host thunk. `MakeGuestCallable()` then performs:

```text
native Vulkan PFN H
  + known function name
  -> choose guest CallHostFunction invoker T
  -> LinkAddressToFunction(H, T)
  -> return H to guest application
```

`LinkAddressToFunction` crosses the thunk boundary to `ThunkFunctions::LinkAddressToGuestFunction`, which calls:

```text
AddThunkTrampolineIRHandler(H, T)
```

`AddThunkTrampolineIRHandler` installs a CustomIR entry keyed by `H`. Its handler captures `T`, writes `H` to guest `r11`, and emits an `_ExitFunction` to constant `T`.

Therefore FEX owns an explicit long-lived object containing an executable guest address into `libvulkan-guest.so`.

## Application teardown order

Vulkan-Tools `vulkan-sdk-1.4.341.0` has the application-side order needed for this investigation.

`AppGpu::~AppGpu()` destroys its Vulkan device. Those GPU objects die before the local `AppInstance` leaves scope.

`AppInstance::~AppInstance()` performs:

```text
vkDestroyDebugReportCallbackEXT(...)
vkDestroyInstance(...)
unload_vulkan_library()
```

and the Linux implementation of `unload_vulkan_library()` calls:

```text
dlclose(vulkan_library)
```

External source reference:

- https://redirect.github.com/KhronosGroup/Vulkan-Tools/tree/48a4bcbdf619e57204783f8c1a04c76c160ddd5b

The retained FEX diagnostic already showed the native debug-report destroy call returning before exit 139.

This makes an intended application Vulkan call *after a completed `dlclose()`* a weak candidate. It increases the value of tracing loader/FEX teardown and retained FEX execution objects.

## Ordered teardown timeline

The exact boundary map is:

### T0 — guest Vulkan image is mapped

Retained run reconstructs the old image range approximately as:

```text
[0x7ffff7c87000, 0x7ffff7cdc000)
```

Live FEX state later accumulates addresses inside this image.

### T1 — guest constructor runs

`LOAD_LIB_INIT(libvulkan, OnInit)` invokes FEX `loadlib` and guest Vulkan initialization.

Live references afterward:

- FEX host thunk `libvulkan-host.so` loaded;
- `ThunkHandler_impl::Libs` contains `libvulkan`;
- Vulkan X11 callback setup begins.

### T2 — host-to-guest callback trampolines are created

Live references afterward:

- `GuestcallToHostTrampoline` entries containing guest unpacker/target addresses;
- host-side Vulkan/X11 state pointing at generated host trampolines.

### T3 — dynamic Vulkan PFNs are registered

Each GIPA/GDPA result can create:

```text
CustomIRHandlers[host_pfn H] -> guest CallHostFunction target T
```

Live references afterward:

- CustomIR handler lambda capturing `T`;
- CustomIR handler data containing `T`;
- eventually a compiled CustomIR block for `H` containing an exit to `T`.

### T4 — CustomIR block generation

`GenerateIR()` checks `CustomIRHandlers` before ordinary guest decoding.

When it finds `H`, the handler emits the redirect block. The result is flagged with:

```text
NeedsAddGuestCodeRanges = false
```

This is important. It means a late `CustomIRHandlers.find()` event is not required for the final failure. Once compiled, the cached block can execute again directly from FEX's lookup cache.

A trace that instruments only `CUSTOMIR GENERATE` can therefore miss the decisive post-unmap use. Runtime instrumentation must separately log **execution of a compiled CustomIR redirect**.

### T5 — Vulkan work completes

`vulkaninfo --summary` prints the expected enumeration under llvmpipe.

This removes Venus/virtio from the minimal failure path.

### T6 — Vulkan objects are destroyed

`AppGpu` teardown destroys devices before `AppInstance` teardown.

`AppInstance` then destroys the debug-report callback and the Vulkan instance. The retained diagnostic proves the native debug-report destroy wrapper returns.

The guest Vulkan thunk is still mapped here.

### T7 — guest `dlclose` begins

`AppInstance::~AppInstance()` calls `unload_vulkan_library()`, then guest `dlclose(vulkan_library)`.

This is the application owner of the unload request.

### T8 — guest DSO finalizers run

The loader runs the object's finalizers while its memory remains mapped.

Guest static destruction can retire guest-side containers such as `HostPtrInvokers`. No symmetric FEX bridge cleanup is triggered by the guest thunk helper API in this revision.

Live FEX references still include:

- CustomIR handler entries containing old guest targets;
- compiled CustomIR redirect blocks;
- callback trampoline metadata containing old guest unpackers/targets;
- `ThunkHandler_impl::Libs` bookkeeping.

### T9 — loader reachability ends

Before the bytes are unmapped, the loader removes the retiring DSO from normal lookup/search scopes.

This is the useful **loader-unreachable boundary**: fresh guest lookup can no longer discover the thunk through ordinary loader search, while its pages may still exist briefly.

FEX bridge references are independent of this loader search state and remain live.

### T10 — the Vulkan guest image is unmapped

The loader retires the guest DSO's mapped span.

This is the first point at which a previously valid guest thunk execution address becomes physically invalid.

For the retained run, the image is reconstructed as approximately:

```text
[0x7ffff7c87000, 0x7ffff7cdc000)
```

A new target trace should print the exact retiring `link_map` bounds or all guest mappings immediately before this point instead of relying on reconstruction.

### T11 — FEX performs the host `munmap`

In FEX `GuestMunmap`, the 64-bit path performs real host:

```text
::munmap(addr, length)
```

before `TrackMunmap` and before `InvalidateCodeRangeIfNecessary`.

This ordering matters. The guest bytes disappear first.

### T12 — FEX updates VMA tracking

`TrackMunmap` records the removal in FEX's guest memory tracking.

The stale bridge objects described above are outside this VMA table.

### T13 — FEX invalidates ordinary code for the unmapped guest range

`InvalidateCodeRangeIfNecessary` calls thread-manager guest-code invalidation when SMC checking requires it.

That operation targets the old guest VA range.

A CustomIR redirect block for a native PFN is keyed by `H`, not by old guest `T`. Its generated code contains `T` as an exit destination. Therefore invalidating `[old_guest_base, old_guest_end)` does not inherently identify the `H -> T` bridge for retirement.

This is the strongest source-level lifetime mismatch found in the current pass.

### T14 — stale FEX references remain

After guest image retirement, surviving FEX objects can still contain addresses into it:

1. **CustomIR dynamic-PFN state**
   - handler keyed by native `H`;
   - captured/data target `T` in old guest image;
   - cached compiled block potentially exiting directly to `T`.

2. **Host-to-guest callback state**
   - `GuestUnpacker` / `GuestTarget` in `TrampolineInstanceInfo`;
   - cache keyed by those guest addresses.

3. **Thunk library bookkeeping**
   - `ThunkHandler_impl::Libs` still reports the library as loaded from FEX's point of view.

The source itself contains a comment beside `Libs` saying FEX ideally should track library unload before memory backing disappears.

### T15 — first stale execution target

Retained runtime evidence proves eventual guest execution reaches:

```text
0x7ffff7cd21f0
```

inside the old image interval, with offset `0x4b1f0` resolving to generated `CallHostFunction<...>`.

The immediate caller remains the single missing runtime edge.

### T16 — synthesized guest SIGSEGV

FEX records x86 page fault:

```text
TrapNo = 14
err_code = 0x15
```

including instruction fetch, then enters its deliberate `GuestSignal_SIGSEGV` path and the process exits 139.

## Which mapping disappears first?

The meaningful failure boundary is the guest Vulkan DSO image itself. The retained evidence reconstructs its old interval as approximately:

```text
0x7ffff7c87000 - 0x7ffff7cdc000
```

The current packet does not contain a pre-unmap trace showing every individual `PT_LOAD` mapping or the exact `link_map` `l_map_start/l_map_end` pair at retirement. Therefore the precise mapping receipt should be captured in the next run.

What the FEX source establishes exactly is the local operation order:

```text
real host munmap
  -> TrackMunmap
  -> guest-code invalidation
```

so the destination is already invalid by the time normal FEX code-range invalidation runs.

## When does the thunk become unreachable through the guest loader?

There are two different boundaries:

1. **loader-unreachable:** the retiring object is removed from normal loader search scopes;
2. **memory-unreachable:** its mapped bytes are actually unmapped.

The first occurs before the second during normal loader teardown.

FEX's bridge objects are neither ordinary guest-loader lookups nor guest symbol-table ownership. They can therefore survive both boundaries.

## Live references after each boundary

| Boundary | Guest loader | Guest bytes | FEX CustomIR | FEX callback trampolines | Ordinary translated code |
| --- | --- | --- | --- | --- | --- |
| before `dlclose` | reachable | mapped | live | live | live |
| after finalizers | retiring | mapped | live | live | live |
| after loader-search removal | unreachable by normal lookup | mapped | live | live | live |
| immediately after real `munmap` | unreachable | gone | live | live | may still await invalidation |
| after FEX range invalidation | unreachable | gone | **still has H -> old T unless separately removed** | **still contains old guest addresses unless separately removed** | old-range translations should be retired under active SMC invalidation |
| final fault | unreachable | gone | leading suspect | secondary suspect | lower-ranked alternative |

## Final caller -> callee chain: leading reconstruction

The strongest source-consistent chain is:

```text
some guest-side indirect use of native Vulkan PFN H
  -> FEX lookup finds compiled CustomIR block for H
  -> block places H in guest r11
  -> block exits to captured guest target T
  -> T belongs to old libvulkan-guest.so CallHostFunction<...>
  -> instruction fetch at unmapped T
  -> guest x86 #PF, err_code 0x15
  -> FEX GuestSignal_SIGSEGV
  -> exit 139
```

The registration and generated-transfer portions of this chain are established by source.

The dead destination and instruction-fetch fault are established by the retained target run.

The first line — the immediate post-unmap user of `H`, or an equivalent already-committed CustomIR dispatch — is still open.

## Competing explanations ranked by evidence

### 1. Cached CustomIR dynamic-PFN redirect -> dead `CallHostFunction` target

**Rank: strongest.**

Why it fits:

- it directly stores the old guest target;
- it is keyed by a native address outside the guest DSO range;
- generated code contains an exit to the old guest target;
- the observed dead RIP belongs to the expected `CallHostFunction` family;
- ordinary DSO-range invalidation does not identify this ownership relation.

Missing proof:

- the final transfer into the dead guest target has not been directly classified as CustomIR execution.

### 2. FEX return/resume or invalidation transition around guest `munmap`

**Rank: serious alternative.**

Why it fits:

- Vulkan-Tools performs no intended Vulkan API operation after its final `dlclose` inside `AppInstance::~AppInstance()`;
- FEX's saved RIP can be imperfect while JIT execution is active;
- a thread already committed to a guest target across the unmap boundary could produce the same destination fingerprint.

Discriminator:

- record the last transfer kind and guest caller/return PC before the first stale target.

### 3. Host-to-guest callback trampoline

**Rank: real generic lifetime bug class, weaker fit to this exact crash.**

Why it fits:

- FEX stores guest unpacker/target addresses process-long in trampoline metadata;
- Vulkan `OnInit()` creates such trampolines.

Why it ranks lower:

- its natural first destination is a callback unpacker, while the recorded dead RIP resolves to `CallHostFunction`.

### 4. Ordinary stale guest function pointer

**Rank: possible, weaker.**

Why it fits:

- a guest pointer into an unloaded DSO would produce the same instruction-fetch failure.

Why it ranks lower:

- FEX dynamic Vulkan PFNs exposed to the application are native host addresses; the hidden `CallHostFunction` target is FEX-owned bridge state;
- application teardown source gives no intended Vulkan call after the final `dlclose`.

### 5. Loader teardown calling an already-unmapped finalizer

**Rank: weak.**

Normal loader order runs finalizers before unmapping the object.

### 6. Ordinary guest JIT block simply survived DSO unmap

**Rank: lower.**

FEX explicitly runs guest-range invalidation after `TrackMunmap` under active SMC checking. The leading CustomIR case has a clearer reason to escape that range-based cleanup.

## Exact next discriminator

### Cheapest path: inspect the retained core

At the existing synthesized SIGSEGV, read:

```gdb
set $f = (FEXCore::Core::CpuStateFrame*)$x28
p/x $f->State.rip
p/x $f->State.gregs[FEXCore::X86State::REG_R11]
p/x $f->State.gregs[FEXCore::X86State::REG_RSP]
x/gx $f->State.gregs[FEXCore::X86State::REG_RSP]
```

Interpretation:

- if `r11` equals one of the native Vulkan PFNs logged at `LinkAddressToFunction(H,T)`, that is a strong direct fingerprint of `AddThunkTrampolineIRHandler` because that generated path explicitly puts `H` into guest `r11` before exiting to `T`;
- the guest word at `rsp` can identify the caller/return PC and distinguish an ordinary guest call site from a loader/resume transition.

### Execution-grade rerun

Use llvmpipe and preserve the existing four controls:

1. normal;
2. Vulkan thunk pinned;
3. guest `dlclose` no-op;
4. bogus preload.

Emit one globally ordered trace stream with a monotonic sequence counter. Required events:

```text
GUEST_MAP path/base/end/prot
GUEST_CTOR_ENTER/EXIT
FEX_LOADLIB_ENTER/EXIT
GIPA name/native_pfn/guest_invoker
GDPA name/native_pfn/guest_invoker
LINK_REGISTER host_pfn/guest_target/name
CUSTOMIR_GENERATE host_pfn/guest_target
CUSTOMIR_EXEC host_pfn/guest_target/target_mapped
HOST_TO_GUEST_TRAMPOLINE trampoline/unpacker/target
VK_DESTROY name/object
GUEST_DLCLOSE_ENTER/EXIT handle
GUEST_DTOR_ENTER/EXIT
LOADER_UNREACHABLE base/end
GUEST_MUNMAP_ENTER base/len
HOST_MUNMAP_DONE base/len
TRACK_MUNMAP_DONE base/len
CODE_INVALIDATE_ENTER/EXIT base/len
LIVE_REF_SUMMARY old_base/old_end
FIRST_STALE_TARGET target/r11/rsp/return_pc/transfer_kind
GUEST_SIGSEGV rip/trap/err
```

`CUSTOMIR_EXEC` matters separately from `CUSTOMIR_GENERATE`. A cached block can execute after unload without another handler lookup.

At every boundary, scan and print:

- CustomIR entries whose `Data`/captured target overlaps retiring Vulkan guest range;
- callback trampolines whose `GuestUnpacker` or `GuestTarget` overlaps it;
- thread RIPs / cached lookup entries overlapping it where practical.

### Decisive outcomes

```text
REGISTER H->T
UNMAP T range
CUSTOMIR_EXEC H->T target_mapped=0
FIRST_STALE_TARGET T r11=H
```

would establish stale CustomIR as the immediate cause.

A first stale target with no CustomIR execution and a caller inside loader/ordinary guest code would demote it immediately.

A host-to-guest trampoline event immediately before the stale target would select the callback class.

## Smallest repair direction supported today

The current evidence supports a lifecycle requirement, not a contribution-ready patch:

- guest-thunk bridge registrations need explicit load identity;
- unload must stop new bridge acquisitions;
- every externally reachable bridge for that load needs revocation or rebinding;
- translated bypass paths must be invalidated;
- already-acquired executions must drain before guest bytes are unmapped;
- callback and dynamic-PFN directions must share the same lifetime owner.

The local `lifetime-designs/` experiment already tests this family of requirements and currently favors stable host-owned indirection plus load-generation identity plus an execution lease.

See:

- [lifetime-designs/FEX_INTEGRATION_NOTES.md](lifetime-designs/FEX_INTEGRATION_NOTES.md)
- [lifetime-designs/DESIGN_COMPARISON.md](lifetime-designs/DESIGN_COMPARISON.md)

This remains local/owned engineering evidence. FEX upstream contribution policy requires any eventual contribution implementation to be independently human-derived.

## Evidence boundary

### Demonstrated on target

- x86 Vulkan enumeration succeeds after the separate callback-routing diagnostic;
- teardown exits 139 with llvmpipe;
- dead guest instruction fetch is in the former Vulkan guest thunk range;
- no-op guest `dlclose` changes the result to exit 0;
- bogus preload preserves exit 139;
- pinning only `libvulkan-guest.so` changes the result to exit 0;
- pinned Venus path reaches Apple M5 and exits 0.

### Established by exact source read

- guest thunk constructor invokes FEX `loadlib`;
- no paired guest unload registration exists in the helper path reviewed;
- Vulkan GIPA/GDPA registers native PFNs to guest `CallHostFunction` targets through CustomIR;
- CustomIR state stores/captures guest target addresses;
- generated CustomIR block exits to constant guest target and is treated separately from ordinary guest code-range tracking;
- generic host-to-guest trampolines also retain raw guest addresses;
- `GuestMunmap` performs the real `munmap` before FEX VMA tracking and code invalidation;
- Vulkan-Tools 1.4.341.0 performs debug callback destroy, instance destroy, then `dlclose` in `AppInstance` teardown.

### Still open

- exact pre-unmap guest loader mapping bounds from the failing process;
- exact immediate caller of the first stale execution target;
- whether that first stale transfer is cached CustomIR execution, callback trampoline, ordinary guest code, loader/resume state, or another FEX path;
- whether current code invalidation already supplies sufficient execution quiescence once bridge ownership is corrected.

### 2026-08-14 continuation execution limit

No new target run was executed in this continuation because the Fedora VM, `~/src/FEX-2608`, `/opt/fex-2608`, and retained `~/fex-segv-full.core` were absent from the available runtime. The new contribution of this pass is the refined teardown ordering, source-level surviving-reference map, application destructor ordering, and the reduced final discriminator above.
