# FEX human learning packets — 2026-08-14

Status: internal teaching companion for the current human-review desk. This file is not an upstream submission and is not a substitute for independently reading and re-deriving the source changes.

The purpose is to make each desk-ready item learnable in the same order:

1. ELI5 mental model;
2. smallest bug statement;
3. source path to read;
4. experiment that proves causality;
5. implementation idea to independently re-derive;
6. maintainer questions to answer before writing anything upstream-facing;
7. explicit non-goals, so adjacent research does not leak into the patch.

---

## Packet 1 — Vulkan proc-address callback routing and native availability

### ELI5

Vulkan applications often do not call every function by a normal linked symbol. They ask the Vulkan loader for a function pointer by name using `vkGetInstanceProcAddr` (GIPA) or `vkGetDeviceProcAddr` (GDPA).

FEX already had special safe wrappers for several Vulkan functions that contain callbacks. Those wrappers are necessary because an x86 guest callback pointer cannot simply be handed to native ARM code.

The bug was that FEX had two ways to know a function was special:

- metadata saying “this has a custom host implementation”; and
- a separate manual name lookup used for dynamic proc-address queries.

Those lists drifted. Direct calls reached the safe wrapper, while some dynamic GIPA calls could return the native ARM-facing function instead. The native code later attempted to use a guest callback and FEX died with SIGILL.

A second, separable bug was that custom lookup happened before asking native Vulkan whether the function was actually available for the supplied scope. FEX could therefore manufacture a non-null guest function pointer where native Vulkan would have returned null.

### Smallest correct bug statements

**Routing bug:** Dynamic proc-address lookup must route every callback-sensitive Vulkan function with an existing custom FEX implementation through that implementation, just as a direct call does.

**Availability bug:** FEX must not make a Vulkan command appear available when native GIPA/GDPA rejects it for the requested instance/device/scope.

Keep these as two claims even if one final branch contains both fixes.

### Read these source paths first

1. `ThunkLibs/libvulkan/libvulkan_interface.cpp`
   - find the relevant `custom_host_impl` declarations;
   - understand what information thunk metadata already expresses.
2. `ThunkLibs/libvulkan/Host.cpp`
   - find `LookupCustomVulkanFunction()`;
   - then read `FEXFN_IMPL(vkGetInstanceProcAddr)` and `FEXFN_IMPL(vkGetDeviceProcAddr)`.
3. `ThunkLibs/libvulkan/Guest.cpp`
   - read guest GIPA/GDPA wrappers;
   - understand why GIPA/GDPA self-query needs to return guest entrypoints rather than raw native pointers.
4. The internal candidate branch `teamleaderleo/FEX:fix/vulkan-callback-proc-routing` only after reading the parent source yourself.

### Causal proof to understand

Hosted ARM64 baseline:

- direct debug-report route reaches FEX's established safe/dummy behavior;
- GIPA debug-report route reaches callback creation but host FEX exits 132 when the callback fires.

Route-only candidate fixes direct/dynamic callback safety but still exposes wrong NULL-scope availability.

Final candidate additionally matches native NULL behavior and GIPA/GDPA self-query semantics.

The important lesson is that the test matrix itself separated the two bugs rather than accepting “the crash stopped” as sufficient evidence.

### Re-derive the implementation yourself

Before looking at the candidate diff, answer:

- Where should native availability be queried?
- At what point is custom substitution allowed?
- If native approves `vkGetInstanceProcAddr` itself, what pointer must the x86 guest receive?
- Same question for `vkGetDeviceProcAddr`.
- Why should a successful native extension lookup be reused to populate any FEX loader slot instead of performing a second potentially different lookup?

Then write the smallest code that satisfies those invariants.

### Regression design

Minimum behavioral matrix:

- debug-report direct;
- debug-report via GIPA;
- debug-utils direct;
- debug-utils via GIPA;
- `GIPA(NULL, callback command)` where native returns null;
- `GIPA(NULL, ordinary non-global command)` where native returns null;
- GIPA self-query;
- real-device GDPA ordinary device command;
- GDPA self-query;
- invalid device/instance-scope names remain null.

A separate inventory test comparing `custom_host_impl` metadata with manual dynamic routing is useful prevention and can stay a distinct review item.

### Maintainer questions to be able to answer

- Why is native Vulkan the availability oracle?
- Why are routing and availability separate fixes?
- Why are guest GIPA/GDPA self-pointers special?
- Could metadata generate the dynamic routing table instead of maintaining two inventories?
- Does the fix preserve 32-bit behavior too?

### Non-goals

This patch does not solve:

- guest thunk executable lifetime after `dlclose`;
- `vkCreateInstance` callback-bearing `pNext` nodes;
- generic callback lifetime/reclamation;
- allocation callback repacking.

---

## Packet 2 — thunkgen const-pointee repack correctness

### ELI5

Imagine an API says: “here is a pointer to some input data; it is `const`, so you may read it but must not modify it.”

FEX sometimes converts guest-layout structs into temporary host-layout structs before calling native code. That conversion is wrapped in `repack_wrapper`.

`repack_wrapper` uses the original pointer type to decide whether it should copy the temporary host object back into guest memory when the wrapper goes out of scope. Writable `T*` may need copyback; input-only `const T*` must not.

Thunkgen accidentally stripped `const` from the pointee before instantiating the wrapper. So a parameter declared `const T*` behaved like writable `T*` during cleanup.

In the Vulkan allocator case, FEX created a converted host `VkAllocationCallbacks`, native creation succeeded, and then wrapper destruction copied the converted temporary back over the application's original guest allocator. The guest callback fields were damaged. A later destroy call then consumed the already-corrupted allocator and crashed.

### Smallest correct bug statement

Thunkgen must preserve pointee constness when selecting the generated `repack_wrapper` type, because wrapper exit semantics use that qualification to determine whether guest memory may be written back.

### Read these source paths first

1. `ThunkLibs/Generator/gen.cpp`
   - find pointer-to-repackable parameter generation;
   - identify the helper that historically stripped pointee constness.
2. `ThunkLibs/include/common/Host.h` or the current location defining `repack_wrapper` / `make_repack_wrapper`.
   - follow entry conversion;
   - follow destructor/exit conversion;
   - find the condition that distinguishes const from writable guest input.
3. `unittests/ThunkLibs/generator.cpp`
   - understand existing `StructRepacking` tests before reading the added regression.
4. Only then inspect branch `teamleaderleo/FEX:linux-fieldwork/thunkgen-preserve-const-repack`.

### Causal proof to understand

The Vulkan allocator runtime discriminator checks more than process exit:

- guest allocator input is identical across create and destroy;
- converted native allocator identity is stable;
- guest free callback is actually entered and returns;
- destroy returns normally.

The generic generator regression then verifies that the generated wrapper type for a repackable `const A*` still contains the `const` pointee qualification for both supported guest ABIs.

A broader hosted thunkgen suite shows the same unrelated four failures on the exact unmodified parent, so there is no observed failure delta caused by this candidate.

### Re-derive the implementation yourself

Before reading the diff, answer:

- Why was const stripped originally? Was it needed for the internal host-layout storage, or only accidentally applied to the public wrapper type?
- Where does `repack_wrapper` itself already remove const internally when it needs mutable temporary storage?
- Which type should therefore be passed to `make_repack_wrapper`?
- Should top-level pointer cv-qualification and pointee cv-qualification be treated differently?

The desired change should fall naturally out of those answers rather than from copying the experimental patch.

### Regression design

The smallest useful generator test should prove:

- a repackable `const A*` parameter instantiates a wrapper whose source pointer type retains const;
- the same rule holds for both guest ABI modes;
- ordinary writable `A*` behavior is unchanged.

The Vulkan runtime case is a strong integration test, but the generic generator regression is the durable unit-level protection.

### Maintainer questions to be able to answer

- Why is this generic rather than Vulkan-specific?
- What exact writeback policy depends on pointee constness?
- Could preserving const break legitimate writable-output repacks?
- Why is changing the generator preferable to a Vulkan-only custom suppression of copyback?
- Is the regression asserting semantics rather than fragile generated formatting?

### Non-goals

This patch does not solve:

- how Vulkan allocation callbacks are translated between ISAs;
- executable callback lifetime;
- callback-member annotations;
- thunk wrapper unload.

It only restores the input/output semantics implied by `const T*`.

---

## Packet 3 — Vulkan `vkCreateInstance` callback-bearing `pNext` handling

### ELI5

Vulkan lets applications extend many structs through a linked list called `pNext`.

During `vkCreateInstance`, some `pNext` nodes can contain debug callbacks. Native Vulkan may call those callbacks *during the create call itself*.

FEX historically handled one old debug-report node by temporarily removing it from the chain, because letting native ARM code call an x86 guest callback would be unsafe under the existing suppression policy.

Two things were wrong:

1. the newer debug-utils callback node was not also removed, so native validation code could call the guest callback and FEX would SIGILL;
2. the old removal code changed `pNext` pointers in the marshaled input and did not restore them, so the caller-visible input chain could be different after `vkCreateInstance` returned.

A third edge is consecutive callback-bearing nodes: after removing one node, the loop must re-check the same predecessor rather than advance and accidentally skip the next callback node.

### Smallest correct bug statement

Under FEX's current callback-suppression policy for instance-creation debug callbacks, all callback-bearing debug-report/debug-utils nodes must be hidden from the native `vkCreateInstance` call without leaving guest-visible mutation in the input `pNext` chain.

### Read these source paths first

1. `ThunkLibs/libvulkan/Host.cpp`
   - read the full custom `FEXFN_IMPL(vkCreateInstance)`;
   - understand why it passes `nullptr` for `VkAllocationCallbacks` in the current implementation;
   - inspect the historical debug-report splice loop.
2. Vulkan definitions for:
   - `VkBaseInStructure`;
   - `VkDebugReportCallbackCreateInfoEXT`;
   - `VkDebugUtilsMessengerCreateInfoEXT`.
3. Read Vulkan's `pNext` const/input conventions: the application owns the input chain; FEX should not expose persistent mutation.
4. Then inspect branch `teamleaderleo/FEX:fix/vulkan-instance-pnext-callback-restoration`.

### Causal proof to understand

The hosted finding separates this from proc-address routing:

- native ARM64 control proves debug-utils callback may fire during `vkCreateInstance`;
- the proc-routing candidate still exits 132 on the debug-utils `pNext` case, proving it is a different bug;
- the pNext candidate exits 0;
- the integrity probe verifies the chain is unchanged afterward;
- zero guest debug callbacks are observed, matching the existing suppression policy.

Consecutive callback nodes are included to verify the loop does not skip the second one after a splice.

### Re-derive the implementation yourself

There are at least two defensible implementation families:

**Temporary splice + restoration**

- record every predecessor and original `pNext` value;
- splice callback-bearing nodes;
- re-check the same predecessor after each removal;
- call native Vulkan;
- restore in reverse order before returning.

**Copied chain**

- construct a temporary host-side copy of the relevant chain excluding callback-bearing nodes;
- pass that copy to native Vulkan;
- leave original input completely untouched.

The current candidate uses the first approach because it is small. Human review should explicitly decide whether its temporary mutation is acceptable under all exits and future maintenance, or whether a copied-chain implementation is clearer.

### Regression design

At minimum exercise:

- debug-report node alone;
- debug-utils node alone;
- consecutive report -> utils nodes;
- a normal non-callback node before/between/after them;
- create success and, if practical, create failure;
- original chain pointer identity/content unchanged after return;
- guest callbacks remain suppressed under current policy.

### Maintainer questions to be able to answer

- Is temporary mutation of a marshaled const input acceptable if always restored?
- What happens if native `vkCreateInstance` fails?
- Are there exception/early-return paths that could bypass restoration?
- Which regular-Vulkan extensible structs actually contain callback/function-pointer fields?
- Should this remain explicit Vulkan policy or become generic pNext transformation machinery?

### Non-goals

This patch does not attempt to make arbitrary Vulkan `pNext` callbacks work through host-to-guest trampolines. It preserves the project's existing suppression policy while making it complete and input-safe for the demonstrated debug callback nodes.

---

## Submission philosophy for these small findings

These are intentionally separate review units. Do not combine them merely because they were discovered during the same investigation.

A strong human-owned submission sequence is:

1. independently reproduce the bug from clean source;
2. explain the invariant without relying on investigation prose;
3. write the smallest correction yourself;
4. write or adapt the smallest regression yourself;
5. compare against the research candidate only as a cross-check;
6. run project-native CI;
7. prepare a maintainer-facing description that states what the patch does and explicitly what it does not do.

The small fixes should still be pursued even if the resident-bridge/lifetime architecture remains under research. They correct independent, bounded semantics and do not need to wait for the larger design.
