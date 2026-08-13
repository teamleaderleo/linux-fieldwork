# FEX integration notes

Owned source mirror: `teamleaderleo/FEX` at FEX-2608 commit `e869aa644a16e4332cdc15c1ea0b4d13d482385d`. FEX upstream remains untouched.

## Source lifecycle map

`ThunkFunctions::LinkAddressToGuestFunction` receives only a native function address and a guest target, then calls `AddThunkTrampolineIRHandler(native, guest_target)`. No guest DSO identity, mapping identity, generation, or unload token crosses that API.

[`Thunks.cpp`](https://github.com/teamleaderleo/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/Source/Tools/LinuxEmulation/Thunks.cpp)

`ContextImpl::AddThunkTrampolineIRHandler` installs a CustomIR handler keyed by the native entrypoint. The handler captures `GuestThunkEntrypoint` and emits an exit to that guest address. Duplicate native PFNs are explicitly possible in Vulkan aliases. `RemoveCustomIREntrypoint` already erases a CustomIR key and requests guest-code invalidation, but the thunk API has no load-instance bulk-removal boundary.

[`Core.cpp`](https://github.com/teamleaderleo/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/FEXCore/Source/Interface/Core/Core.cpp)

The host->guest callback side independently stores raw `GuestUnpacker` and `GuestTarget` values in `TrampolineInstanceInfo`, and caches trampolines by those guest addresses. Therefore a PFN-only deregistration leaves another stale-address class alive.

## Integration implication

A winning implementation needs an explicit guest-thunk load identity shared by both bridge directions. Conceptually:

```text
begin load -> obtain load token/generation
register PFN bridge under token
register callback bridge under token
begin unload -> mark token draining
revoke/rebind PFN and callback entries
invalidate translated paths
wait for active executions using token
allow guest DSO unmap
reclaim empty metadata
```

Compatible aliases sharing one native PFN need owner stacking or canonicalization so unloading the newest owner can reveal an older live owner. Incompatible bridge ABIs sharing one PFN need rejection or a richer dispatch key.

## Code-cache / thread-safety question

The source comments that thunk entrypoints do not get cached, which reduces persistent-cache concerns. The unresolved requirement is execution quiescence: after CustomIR removal and guest-code invalidation, can a thread already committed to the old guest target survive until the DSO is unmapped underneath it?

The source read did not establish a synchronous guarantee strong enough to answer yes. If FEX invalidation already waits for those executions, it can supply the drain phase. Otherwise an explicit execution lease or equivalent quiescence mechanism is required.

The conceptual invalidation order remains:

`generation_draining > bridge_invalidate > code_invalidate > execution_drain > unmap`

The drain must avoid holding locks required by callbacks or translated threads as they leave the retiring generation.

## Exact remaining uncertainty

1. The real crash proves execution reaches the old Vulkan guest image after unmap, but does not identify the final surviving holder: PFN CustomIR, host callback trampoline, another bridge, or translated execution retaining a guest PC.
2. The exact guest-loader pre-unmap hook that can issue/retire a load token has not been demonstrated in a full FEX run.
3. Existing code invalidation may already provide sufficient quiescence; the source read did not prove it.
4. The seven variants were executed as a local lifecycle model. Full-FEX integration remains the validation gate.

External precedent from the parent investigation: [FEX Vulkan callback PR #1803](https://redirect.github.com/FEX-Emu/FEX/pull/1803).
