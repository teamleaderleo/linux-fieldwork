# Eleventh pass: exact synthetic-key eviction and rebind works on real FEX

Status: internal Linux Fieldwork record for issue #672. FEX upstream remains read-only. This pass records an executed diagnostic in the owned FEX fork.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned carrier branch: `teamleaderleo/FEX:ci/thunk-rebind-diagnostic-v2-20260814`.

Executed workflow run: `31743358148`.

Receipt artifact: `thunk-exact-all-cache-rebind-v3-31743358148`, digest `sha256:9a39fc2faf478bf3c368887986cc4279bc312a945a95a1eed2e99e81e9202cf6`.

## Bottom line

The real FEX forced-different-reload reproducer already established that a stable native host function address `H` remains associated with the first guest thunk target `T1` after that guest DSO is unloaded and reloaded at a different address.

This pass tested the missing repair operation directly:

1. detect a duplicate registration `H -> T2` when `H -> T1` is still installed;
2. remove the old CustomIR handler;
3. **exactly erase synthetic key `H` from every live shared guest-to-host map**;
4. **exactly invalidate `H` from every live guest thread's L1/L2 lookup cache**;
5. let `GuestToHostMap::Erase(H)` delink inbound compiled callers;
6. install the new `H -> T2` registration;
7. call `H` again.

The forced-different reload then succeeds through generation 2.

This is runtime evidence that the stale dynamic-PFN `LinkAddressToFunction` path is not merely a stale registry-entry problem. Correct rebinding requires retiring the already-compiled synthetic `H` entry as well.

## Exact runtime receipt

Generation 1:

```text
native host A                   0x00007ffff7d80860
native host B                   0x00007ffff7d80860 (SAME)

guest CallHost invoker A       0x00007ffff7da21b0
guest CallHost invoker B       0x00007ffff7da2210
GuestTarget                     0x00007ffff7da2170
GuestUnpacker                   0x00007ffff7da2190
guest DSO span                  0x00007ffff7da1000-0x00007ffff7da6000

pre-unload Link/CallHost        rv=1023 want=1023
pre-unload host->guest callback rv=10053 want=10053
```

After final unload:

```text
old invoker after dlclose       unmapped
old target after dlclose        unmapped
old unpacker after dlclose      unmapped
proof: all embedded guest executable addresses lost mappings
```

The old DSO span was then reserved with `PROT_NONE`, forcing generation 2 to a different guest base:

```text
reload invoker                  old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT
native host stable              old=0x00007ffff7d80860 new=0x00007ffff7d80860
```

Before re-registration, retained state is still stale:

```text
child retained Link after reload  signal=11 (Segmentation fault)
child retained callback reload    signal=11 (Segmentation fault)
```

Fresh direct generation-2 paths themselves are valid:

```text
fresh guest direct host call     rv=1001031 want=1001031
fresh/current callback            rv=10010053 want=10010053
```

When generation 2 attempts to register the same stable native host function `H` with its new guest invoker `T2`, the diagnostic records:

```text
DIAG_CUSTOM_ADD H=0x7ffff7d80860 inserted=0 data=0x7ffff7d781b0
DIAG_DUP H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d781b0
DIAG_EXACT_SHARED H=0x7ffff7d80860 erased=1
DIAG_EXACT_LOCAL H=0x7ffff7d80860 thread=0xff2630c01000
DIAG_CUSTOM_REMOVE H=0x7ffff7d80860 handler=1
DIAG_CUSTOM_ADD H=0x7ffff7d80860 inserted=1 data=0x7ffff7d781b0
```

The re-registered native host address then works:

```text
child Link after re-register      rv=1001035
child Link after re-register      exit=0
```

Overall diagnostic exit:

```text
rebind.exit = 0
```

## What this establishes

### 1. The dynamic-PFN lifetime defect is runtime-proven on real FEX

The earlier real-FEX reproduction showed:

```text
H -> T1 works
unload T1
force reload at T2 != T1
H remains stable
calling retained H route faults
fresh direct T2 route works
```

This pass adds the positive repair discriminator:

```text
exact-remove old H route
install H -> T2
call H
success
```

That closes the generic mechanism much more tightly than source inspection alone.

### 2. `RemoveCustomIREntrypoint` needs exact compiled-entry retirement semantics

CustomIR blocks are created without guest `CodePages` dependencies. Ordinary guest-range invalidation cannot reliably discover a compiled synthetic block keyed by native host address `H`.

The successful diagnostic therefore uses exact-key eviction:

```text
shared L3: GuestToHostMap::Erase(H)
thread L1/L2: LookupCache::InvalidateCache(H)
```

across all live thread caches while holding the established code-invalidation transaction.

The shared exact erase also executes inbound block delinkers.

This is the operation the old range-based `RemoveCustomIREntrypoint(H)` path was missing.

### 3. Duplicate host-address registration must be a lifecycle operation, not merely a warning

Current FEX detects `H` already associated with a different guest target and logs the collision. The forced-different reload demonstrates that this collision is a normal consequence of unloading and relocating a guest thunk generation while the native host library/PFN remains stable.

For compatible registrations, keeping the first target is not safe across unload/reload.

A complete design needs explicit ownership/generation and compatibility semantics. The diagnostic's remove-and-rebind behavior is evidence that rebinding is mechanically viable; it is not by itself the complete multi-owner policy.

## Independent callback result survives the dynamic-PFN repair

The same run provides an unusually clean separation between the two lifetime classes.

After generation 2 loads:

```text
child first callback after new    signal=11 (Segmentation fault)
child current callback after new  rv=10010093
child current callback after new  exit=0
```

So exact retirement/rebinding of dynamic `LinkAddressToFunction` state fixes the host-PFN path **without fixing an escaped first-generation host->guest callback trampoline**.

That is strong evidence that callback-trampoline lifetime is a second, independent generic bug class rather than an alternate description of the same stale CustomIR object.

The callback side still needs its own owner/generation/revocation or stable-indirection design.

## What this does not establish

This run does **not** prove that stale dynamic-PFN CustomIR is the immediate producer of the original Apple-M5 `vulkaninfo` teardown fault.

The original run still has one missing edge: who selected the retired guest `CallHostFunction` target during final teardown? The retained core's guest `R11` / guest stack remains the shortest direct discriminator for that exact workload.

This run also does not establish the final unload protocol for concurrent guest threads. Exact cache removal is necessary for rebinding, but removing lookup reachability is not automatically an execution lease for a thread that already entered a bridge. Final-unload revocation still needs a quiescence/concurrency policy.

## Design consequence

The generic design now has three experimentally separated requirements:

1. **Owner identity / load generation** — know which retained FEX bridge state depends on a particular guest DSO generation.
2. **Exact synthetic-key retirement** — remove registration plus compiled/cached `H` state, including inbound links and all thread lookup caches.
3. **Execution lifetime / quiescence** — ensure no thread can continue through retired guest code after final unload.

For dynamic host-function-pointer bridges, compatible generation-2 ownership can then rebind the stable native `H` to the current guest invoker `T2`.

For host->guest callback trampolines, the same run shows that a separate solution is required because old escaped trampoline pointers can remain stale even while newly allocated/current callbacks work.

## Current confidence boundary

High confidence / executed:

- stable native `H` + moved guest `T` produces a stale real-FEX `LinkAddress` route;
- the stale route faults while direct new-generation guest code remains healthy;
- exact shared + per-thread synthetic-key eviction followed by `H -> T2` registration restores the native-H path;
- the original first-generation callback remains stale independently;
- a newly created/current generation-2 callback works.

Still open:

- immediate caller into old `T` in the original M5 `vulkaninfo` teardown;
- final all-thread unload/quiescence protocol;
- compatible-owner selection rules for aliases/multiple guest libraries;
- stable ABI/signature identity for safe dormant-owner promotion;
- callback-trampoline revocation/indirection semantics.
