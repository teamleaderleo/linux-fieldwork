# Guest-thunk unload lifetime design experiment

Related Fieldwork: [#669](https://github.com/teamleaderleo/linux-fieldwork/pull/669) and [#672](https://github.com/teamleaderleo/linux-fieldwork/issues/672).

This directory records the local guest-thunk lifetime design experiment requested in #672. It contains seven competing lifecycle implementations, one common synthetic test suite, exact results, and a repeatability receipt. All writes are confined to `teamleaderleo/linux-fieldwork`; FEX upstream remains untouched.

## Result

Seven designs were compared: unload-owned deregistration, DSO bulk ownership, stable indirection slots, generation IDs, dispatch-time stale rejection, pin/refcount residency, and stable slot + generation + execution lease.

Exact scores:

| Design | Score |
|---|---:|
| `deregister` | 10/15 |
| `bulk_owner` | 11/15 |
| `stable_slot` | 13/15 |
| `generation` | 14/15 |
| `stale_reject` | 9/15 |
| `pin_refcount` | 1/15 |
| `lease_slot` | 15/15 |

The strongest design is `lease_slot`: stable host-owned indirection, load-generation identity, a draining state, and an execution lease held through the guest transition.

## Minimum lifecycle invariant

Every executable bridge or compiled path that can outlive a guest-thunk load instance must carry a revocable identity for that load instance and hold its execution lifetime through the guest jump. Unload blocks new acquisitions, revokes externally reachable bridges, retires cached paths that bypass revocation, drains existing acquisitions, and then unmaps the guest DSO.

Winning invalidation order:

`generation_draining > slot_invalidate > code_cache_invalidate > drain_complete > unmap`

## Exact remaining uncertainty

The retained real crash proves execution reaches the old guest Vulkan thunk image after unmap, while the retained evidence does not identify the final surviving holder. Candidates include the native-PFN CustomIR path, a host-to-guest callback trampoline, another thunk bridge, or translated code retaining a guest PC. The full-FEX integration unknowns are the exact pre-unmap guest-loader hook and whether current code invalidation already supplies execution quiescence strong enough to replace an explicit lease.

The full per-design analysis and artifacts are recorded alongside this file.
