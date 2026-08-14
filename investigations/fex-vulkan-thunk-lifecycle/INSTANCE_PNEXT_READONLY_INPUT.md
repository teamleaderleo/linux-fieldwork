# Vulkan instance `pNext`: read-only input requirement

Status: confirmed runtime defect class; this supersedes any claim that “mutate then restore” is fully non-mutating.

## Requirement correction

The earlier `vkCreateInstance` candidates proved two useful properties:

- callback-bearing instance `pNext` nodes can be suppressed so host Vulkan never calls guest x86 callback addresses;
- temporarily changed guest-visible links can be restored before returning, so ordinary writable guest memory looks unchanged after the call.

That is **not sufficient** for a `const VkInstanceCreateInfo*` input.

A guest is allowed to place its create-info in read-only/protected memory. FEX's current 64-bit Vulkan wrapper aliases guest memory directly enough that a `const_cast` write faults immediately. Therefore the implementation requirement is stronger:

> `vkCreateInstance` callback suppression must not write to the guest's `VkInstanceCreateInfo` or any guest `pNext` node at any point, even temporarily.

Any candidate that edits `pNext`, `pfnCallback`, `pfnUserCallback`, or another field in the original guest chain and later restores it is only **after-call restoring**, not truly read-only-safe.

## Baseline read-only reproduction

Internal branch/workflow:

- branch: `ci/agent-b-readonly-pnext-arm64-20260814`
- workflow/source carrier commit: `f5c32d5f524102128ca76ef21d765c4a0900c1d4`
- product base asserted by workflow: `71afe476751deac24adabd1adb575fd2337b6e0a`
- probe source commit: `1c5e9855f63eb13cd909a3556cec7d093c4b8e2f`
- run: `31770241831`
- job: `94674461075`

The probe places `VkInstanceCreateInfo` in an `mmap` allocation, initializes it, then changes the page to `PROT_READ` before calling Vulkan.

Result:

```text
native=0
fex=139
```

Native ARM64 returns without attempting to write the const input. FEX reaches:

```text
MARK readonly=0x7ffff7f45000 pnext=0x7fffffffd5c0
MARK create-enter
```

and then segfaults before `vkCreateInstance` returns.

This demonstrates a real protected-memory failure caused by the wrapper writing the incoming const create-info.

## Partial callback candidate also fails the read-only contract

A separate earlier candidate:

- product candidate: `0a19582b538b521420df07ffadeb13679351a4c3`
- branch: `fix/vulkan-instance-callback-pnext`
- read-only carrier branch: `ci/vulkan-pnext-candidate-readonly-20260814`
- run: `31783496219`
- job: `94714147345`

That candidate removes debug-report nodes by mutating `pNext` and substitutes a dummy callback for debug-utils.

The read-only run result was again:

```text
native=0
candidate=139
```

Representative output:

```text
MARK create-return result=-7 instance=(nil) pnext=... same=1
MARK readonly=... pnext=...
MARK create-enter
timeout: the monitored command dumped core
```

Artifact:

- ID `9212682095`
- ZIP SHA-256 `24217f909131ae6259ce089cd12f2ab3ab21d8971d55a88075e5b76a81e549a4`

The candidate compiled successfully; the failure is runtime memory protection, not a build/harness error.

## Impact on the currently validated splice/restore candidate

The current-main combined branch `fix/vulkan-callback-routing-current-main` at `2665bfecd29387357c40e63432c684b36f21849a` passed:

- four direct/GIPA callback-routing cases,
- after-call `pNext` pointer restoration,
- 760/760 non-beta GIPA/GDPA parity.

Its `vkCreateInstance` implementation still uses `const_cast<VkBaseInStructure*>` and temporarily rewrites predecessor `pNext` links. Therefore it should be described as **after-call restoring**, not as a true no-write solution. The read-only baseline establishes that this implementation form is not sufficient for an upstream-quality const-input fix.

The hosted current-main confirmation remains useful evidence for callback routing and proc availability; this note narrows the pNext implementation claim only.

## Callback-field substitution experiment

A second source-quality experiment on current main keeps the callback-bearing nodes in the chain and temporarily replaces only their callback function fields with FEX dummy callbacks, then restores those fields after native `vkCreateInstance` returns.

That form may preserve more Vulkan instance-creation semantics than removing callback nodes, but it still writes guest callback nodes and therefore does not satisfy the full read-only contract if those nodes are protected.

A stronger probe should protect the entire callback-bearing chain (root plus debug-report/debug-utils nodes), not only the root create-info page.

## Preferred implementation direction

The preferred implementation must operate on host-owned writable copies only.

Conceptually:

1. Treat the guest `VkInstanceCreateInfo` and original `pNext` chain as read-only.
2. Construct a host-owned equivalent chain that preserves all non-callback nodes, ordering, and values.
3. In the host-owned copies of callback-bearing nodes, replace guest callback function pointers with FEX dummy host callbacks (or omit those nodes according to the established suppression policy).
4. Call native `vkCreateInstance` using the host-owned root/chain.
5. Discard the copies without writing anything back to the guest input.

The difficult part is heterogeneous `pNext` cloning: redirecting a callback node in the middle of a chain requires a mutable predecessor link, so simply copying the callback node is not enough. A robust solution likely needs existing/generated Vulkan structure-copy/repack machinery or an `sType`-aware clone mechanism rather than hand-copying only the base header.

## Acceptance tests for the final implementation

A final pNext implementation should pass all of these:

1. Native ARM64 positive control proves temporary debug callbacks can fire during `vkCreateInstance`.
2. x86/FEX direct/GIPA callback matrix remains safe with current suppression policy (`callback_count=0`).
3. Consecutive `debug_report -> debug_utils` chain is handled.
4. After-call full integrity:
   - root/report/utils `pNext` unchanged,
   - debug-report `pfnCallback` unchanged,
   - debug-utils `pfnUserCallback` unchanged,
   - both `pUserData` unchanged,
   - zero guest callbacks.
5. **Entire guest root + callback-bearing chain placed on read-only pages must not segfault or be written.**

The final item is now a hard correctness requirement, not an optional robustness test.
