# FEX Vulkan guest-thunk unload: CustomIR lifetime follow-up

Status: local/owned-repository engineering record. This follow-up extends the retained evidence in [README.md](./README.md) and [EVIDENCE.md](./EVIDENCE.md).

Investigated FEX snapshot: `71afe476751deac24adabd1adb575fd2337b6e0a`.

The working hypothesis is supported: Vulkan dynamic PFNs are registered as native-host-address → guest-thunk-invoker CustomIR redirections, and those redirections can outlive the unloadable guest DSO containing the invoker.

This work did not contact or mutate FEX upstream. Local/owned-repository code and experiments are research material only. Any human upstream contribution remains subject to FEX's contribution policy.

## Conclusion

The unload failure has a concrete source-level ownership hole.

For Vulkan dynamic functions, `vkGetDeviceProcAddr` / `vkGetInstanceProcAddr` obtains a native Vulkan PFN, while `HostPtrInvokers` supplies a guest `CallHostFunction<...>` invoker compiled into `libvulkan-guest.so`. `MakeGuestCallable()` calls:

```text
LinkAddressToFunction(native_host_pfn, guest_CallHostFunction)
```

The thunk syscall reaches `ThunkFunctions::LinkAddressToGuestFunction`, which calls:

```text
Context::AddThunkTrampolineIRHandler(native_host_pfn, guest_CallHostFunction)
```

`AddThunkTrampolineIRHandler` registers a `CustomIRHandlers[native_host_pfn]` entry. The guest target is retained twice before compilation:

1. the handler lambda captures `GuestThunkEntrypoint`;
2. `CustomIRHandlerEntry::Data` is set to the same `GuestThunkEntrypoint`.

When the CustomIR path is compiled, the generated IR emits the guest thunk target as the constant destination of `_ExitFunction`. The translation is reachable by the synthetic entrypoint key, the native Vulkan PFN.

Guest `munmap` invalidates the unmapped **guest virtual-address range**. It has no ownership relation from that range back to the synthetic native-PFN keys. The traced Linux unmap path does not scan `CustomIRHandlers` for thunk `Data` inside the disappearing mapping and does not retire the matching synthetic keys.

The result is a stale redirection after the DSO disappears.

## Source-level lifecycle map

```text
vkGetDeviceProcAddr / vkGetInstanceProcAddr
        |
        v
native Vulkan PFN
        |
MakeGuestCallable(name, func)
        |
        +--> HostPtrInvokers[name]
        |      = guest CallHostFunction<signature> address
        |
        v
LinkAddressToFunction(
    native_PFN,
    guest_CallHostFunction
)
        |
fex:link_address_to_function
        |
ThunkFunctions::LinkAddressToGuestFunction
        |
        v
ContextImpl::AddThunkTrampolineIRHandler(
    Entrypoint           = native_PFN,
    GuestThunkEntrypoint = guest_CallHostFunction
)
        |
        +--> CustomIRHandlers[native_PFN]
        |      Handler lambda captures guest_CallHostFunction
        |      Creator = ThunkHandler
        |      Data    = guest_CallHostFunction
        |
        +--> generated CustomIR
               R11 = native_PFN
               ExitFunction(Constant(guest_CallHostFunction))
        |
        v
lookup/JIT entry reachable by native_PFN

final guest dlclose
        |
        v
munmap libvulkan-guest.so pages
        |
        +--> VMA removed
        +--> guest range invalidated
        |
        X  no dependency edge to native_PFN CustomIR keys
```

Source references for this trace:

- guest helper and `LinkAddressToFunction`: `https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/include/common/Guest.h`
- Vulkan `HostPtrInvokers` / `MakeGuestCallable`: `https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/libvulkan/Guest.cpp`
- host thunk dispatch: `https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/Source/Tools/LinuxEmulation/Thunks.cpp`
- CustomIR registration/removal: `https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/FEXCore/Source/Interface/Core/Core.cpp`
- Linux guest unmap/invalidation: `https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsSMCTracking.cpp`
- all-thread invalidation path: `https://redirect.github.com/teamleaderleo/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/Source/Tools/LinuxEmulation/LinuxSyscalls/ThreadManager.h`

## Exact references that survive unload

After the guest target page has been unmapped, source inspection permits these references to survive:

1. `CustomIRHandlers[native_pfn].Handler`, whose closure still captures the old `GuestThunkEntrypoint`.
2. `CustomIRHandlers[native_pfn].Data`, which still equals the old `GuestThunkEntrypoint`.
3. If the synthetic entrypoint was already translated, the compiled CustomIR block contains the old guest target constant and remains reachable through lookup/cache state keyed by `native_pfn`.

That gives two independent cleanup requirements:

- retire the registration so a cache miss cannot regenerate stale IR;
- invalidate every already-compiled synthetic-key entry so old IR cannot execute after registration removal.

The existing private `ContextImpl::RemoveCustomIREntrypoint(Thread, Entrypoint)` already expresses the right single-key idea: erase the CustomIR entry and invalidate the synthetic entrypoint. The missing part is ownership bookkeeping that can discover the affected synthetic keys when an unload removes the *target* range.

The public `Context` interface exposes `AddThunkTrampolineIRHandler()` without a symmetric target-range retirement operation.

## Interaction with ordinary guest-code invalidation

CustomIR generation sets `NeedsAddGuestCodeRanges = false`. Thus these synthetic blocks do not participate in the same guest-code-page dependency tracking as ordinary decoded guest code.

`GuestMunmap()` removes the VMA and calls range invalidation for the unmapped guest addresses. The stale CustomIR cache key is a native PFN, generally outside that range. Ordinary guest-range invalidation therefore cannot discover it by address overlap.

There is an additional policy trap: `SyscallHandler::InvalidateGuestCodeRange()` ultimately routes through `InvalidateCodeRangeIfNecessary`, which is gated by the configured SMC mode. Synthetic thunk ownership cleanup is a correctness operation and should remain sufficient even with ordinary SMC checks disabled.

For the candidate implementation, synthetic keys should be invalidated directly through the thread-manager/cache invalidation machinery after they are collected.

## Executable lifetime probe

A C++20 synthetic probe was built and executed locally. It models the relevant FEX relationships while using real executable mappings:

- real executable `mmap` page as a guest thunk target;
- synthetic native-PFN key;
- CustomIR-like registry with duplicate-key `emplace` semantics;
- compiled target cached by synthetic key;
- real `munmap` of the target page;
- forked invocation so stale execution is observed as SIGSEGV/SIGBUS;
- candidate target-range retirement plus synthetic-key invalidation.

Build form:

```sh
c++ -std=c++20 -O2 -g -Wall -Wextra -Wpedantic \
  custom_ir_lifetime_probe.cpp -o custom_ir_lifetime_probe
./custom_ir_lifetime_probe
```

Result:

```text
RESULT passed=34 failed=0
```

### Probe matrix

| Variant | Registration after unload | Precompiled synthetic entry | Result |
| --- | --- | --- | --- |
| current-unmap model | survives | survives | stale target faults |
| registry erase only | gone | survives | stale target faults |
| synthetic cache invalidation only | survives | gone initially | stale handler recompiles target; call faults |
| **target erase + synthetic-key invalidation** | gone | gone | stale redispatch cannot be recreated |
| pinned target control | survives | survives | target remains callable |
| unrelated-entry control | unrelated entry survives | unrelated entry survives | unrelated target remains callable |

Additional passing controls:

- two native PFN aliases pointing to the same guest target are both retired;
- duplicate-key semantics preserve the first registration and do not transfer ownership to a rejected second target;
- SMC-none control proves explicit synthetic-key cleanup is self-sufficient;
- cleanup before first translation prevents first compilation;
- after complete cleanup, the same synthetic PFN key can register a fresh guest target and execute that new target.

### Important negative results

**Registry-only cleanup was discarded.** Once the synthetic PFN has been compiled, deleting `CustomIRHandlers[key]` leaves the precompiled stale target executable.

**Cache-only cleanup was discarded.** Retaining the handler lets a subsequent lookup compile a new block containing the same unmapped guest target.

**Pinning the DSO is a control/workaround.** It prevents the target from becoming invalid, matching the retained real `vulkaninfo` result, but preserves the ownership defect.

## Relationship to retained real FEX evidence

The earlier fieldwork independently localizes the real teardown fault to this lifetime boundary:

- after the separate callback-routing diagnostic, x86-64 `vulkaninfo` completes enumeration and exits 139 during teardown;
- the terminal guest fault is an x86 instruction-fetch page fault;
- the saved guest RIP belongs to the former `libvulkan-guest.so` range and resolves near a generated `CallHostFunction<...>` body;
- that range is unmapped at crash time;
- replacing guest `dlclose()` with a no-op changes the run to exit 0;
- a bogus preload remains exit 139;
- pinning only `libvulkan-guest.so` changes llvmpipe and Venus runs to exit 0.

The prior run matrix is retained in [EVIDENCE.md](./EVIDENCE.md). This follow-up identifies a specific FEX owner capable of producing exactly that old-image execution target.

## Candidate implementation A: range scan + batched synthetic invalidation

Strongest experimental candidate:

1. Add a `Context` operation that scans `CustomIRHandlers` under `CustomIRMutex`.
2. Select entries whose `Creator == ThunkHandler` and whose `Data` lies in the guest range being unmapped.
3. Erase those entries and collect their synthetic `Entrypoint` keys.
4. Release `CustomIRMutex`.
5. Invalidate the collected synthetic keys in code buffers and every thread lookup cache through the existing thread-manager/code-invalidation locking path.
6. Perform this correctness cleanup regardless of SMC policy.

Pseudo-interface:

```cpp
fextl::vector<uintptr_t>
Context::RemoveThunkTrampolineIRHandlersInRange(uintptr_t Base, uint64_t Size);

void ThreadManager::InvalidateGuestCodeEntrypoints(
    InternalThreadState* CallingThread,
    std::span<const uintptr_t> Entrypoints);
```

`GuestMunmap()` calls the range-retirement operation after successful unmap and then invalidates the returned synthetic keys.

Benefits:

- uses target ownership already stored in `CustomIRHandlerEntry::Data`;
- handles Vulkan aliases where multiple host PFNs map to one guest invoker;
- tied to actual executable-memory lifetime;
- minimal additional metadata.

Cost:

- O(number of CustomIR handlers) scan per successful guest `munmap`.

This is the best first full-FEX discriminator because it has few new invariants.

## Candidate implementation B: reverse dependency bookkeeping

A production-oriented design can maintain a reverse index from guest target page or guest-image generation to synthetic PFN keys.

On registration:

```text
guest target page/generation -> { synthetic PFN keys }
```

On final range removal, retrieve exact affected keys, erase their CustomIR records, then batch-invalidate the keys.

Benefits:

- unload work scales with affected registrations;
- ownership is explicit;
- repeated load/unload generations can be represented cleanly.

Costs:

- more state and consistency rules;
- alias and duplicate-key handling;
- fork/exec/reset lifecycle review;
- more careful collision behavior because `AddCustomIREntrypoint` keeps the first registration.

## Competing ownership designs

### Explicit guest-side unlink

Track every `LinkAddressToFunction` in the guest thunk and unregister in a DSO destructor/finalizer.

This gives precise semantic DSO ownership, but correctness becomes coupled to guest loader teardown order and every thunk family must maintain exact registration state. Vulkan PFN aliases complicate the bookkeeping.

### Stable process-lifetime invoker code

Move dynamic host-PFN invokers out of unloadable guest DSOs into guest code with process lifetime, dispatching by signature/thunk id.

This removes the dangling code-pointer class at its source. It is a larger thunk ABI/generator redesign.

### DSO/load-generation ownership token

Associate each redirection with an explicit guest image generation and retire all registrations at final image unload.

This gives strong reload semantics, but FEX's Linux syscall layer observes VMAs rather than a semantic `dlclose` final-unload event. The generation still needs to derive from VMA/resource lifetime or be propagated from the guest loader/thunk layer.

### Pin the guest thunk

Proven real-runtime workaround/control. It trades the use-after-unmap for process-lifetime retention and leaves the ownership rule unresolved.

## Regression-test prototype

The core regression must force translation before unload:

```text
dlopen tiny guest DSO
    |
register synthetic host address -> invoker inside DSO
    |
call synthetic address once
    |  forces CustomIR translation/cache
    v
dlclose DSO
    |  guest executable target becomes unmapped
    v
assert matching redirection and synthetic cache entry retired
    |
reload DSO / register fresh target
    |
call same synthetic key successfully
```

An uncompiled-only test misses the precompiled-cache half of the defect.

Useful cases:

- one key / one target;
- two PFN aliases / one target;
- unrelated DSO unmap does not remove the entry;
- duplicate-key first-registration behavior;
- SMC checks disabled;
- repeated unload/reload at reused virtual addresses;
- concurrent thread lookup while final unload occurs.

A Vulkan integration case can use llvmpipe for deterministic device independence: discover dynamic PFNs, invoke enough to translate them, allow final guest Vulkan thunk unload, and assert a clean process exit. The pinned-thunk run remains the negative/control variant.

## Instrumentation for a full FEX run

Useful local probes:

- `AddThunkTrampolineIRHandler`: log synthetic/native PFN key, guest target, `Creator`, and `Data`.
- successful `GuestMunmap`: log range and enumerate thunk `Data` values inside the disappearing range.
- target retirement: log removed synthetic keys and remaining matching handlers.
- lookup/cache: probe each removed key immediately before and after invalidation.
- redispatch: detect a thunk `GuestThunkEntrypoint` whose target has no executable VMA and log/abort before executing it.

Expected causal signature with the candidate:

```text
THUNKIR add key=<native pfn> guest_target=<libvulkan-guest address>
...
THUNKIR munmap <libvulkan-guest range>
THUNKIR retire key=<same native pfn> guest_target=<address inside range>
THUNKIR invalidate synthetic key=<same native pfn>
(no subsequent execution at the old guest target)
```

## Other unload-sensitive thunk state

`ThunkHandler_impl::GuestcallToHostTrampoline` is a separate lifetime area worth auditing. Its trampoline instance records include `GuestUnpacker` and `GuestTarget`, which can also refer to guest code.

That host-to-guest callback cache is distinct from the Vulkan `MakeGuestCallable` dynamic-PFN path examined here. The observed teardown guest RIP near `CallHostFunction<...>` aligns directly with the CustomIR native-PFN → guest-invoker route, so this follow-up keeps the primary finding bounded to CustomIR while flagging the callback trampoline cache for later lifetime review.

## Exact remaining uncertainty

The full FEX candidate was not rebuilt and executed in the current sandbox.

The execution sandbox could read the owned FEX fork through the GitHub connector but direct repository cloning/materialization failed because the execution environment had no outbound DNS route and no complete repository archive was exposed by the connector. The synthetic lifetime probe compiled and executed, but the whole emulator tree could not be rebuilt here.

Two questions therefore remain open for the real FEX integration run:

1. Does target-range retirement plus synthetic-key invalidation turn the actual post-enumeration `vulkaninfo` exit 139 into exit 0?
2. What synchronization is required if another guest thread is invoking or compiling the same PFN while final guest unmap occurs?

The source ownership and probe evidence are strong enough to make that full-tree A/B the next discriminating experiment. The weak approaches have already been eliminated at the mechanism level.

## External-reference policy

Links to GitHub material outside this Fieldwork packet use `redirect.github.com`. Relative links are used for files within this investigation directory. No FEX upstream issue, PR, comment, review, reaction, push, or discussion was created or modified by this follow-up.
