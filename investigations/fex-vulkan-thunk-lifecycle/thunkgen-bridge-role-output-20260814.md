# Thunkgen bridge role output — 2026-08-14

## Why roles are required

The first direct `-guest-bridge` prototype treated every function-pointer signature as one flat bridge class. GL exposed the flaw: it contains a 23-argument dynamic-PFN signature that needs a guest caller but is not a callback unpacker. Instantiating callback machinery for every caller-only signature caused a false compile failure.

The current research branch carries two orthogonal properties per function-pointer registration:

```
needs_caller
needs_unpacker
```

Callback parameters register unpacker-only; `indirect_guest_calls` APIs register caller-only; canonical-signature deduplication ORs the two properties.

## Real-library caller-only gate

Branch: `teamleaderleo/FEX:diagnostic/thunkgen-bridge-role-output-20260814`

Workflow run `31789283277` completed successfully.

Receipt:

```
gl_total=736
gl_caller_only=736
gl_unpacker_only=0
gl_both=0
vulkan_total=476
vulkan_caller_only=476
vulkan_unpacker_only=0
vulkan_both=0
```

This is the desired result for the stock dynamic-PFN surfaces in those two libraries. In particular, GL's large caller-only signatures no longer instantiate `CallbackUnpack`.

The direct Vulkan bridge still builds as NODELETE with the role-aware thunkgen transform applied, so the known caller path does not regress at the compile/link boundary.

## Explicit function-pointer edge found by the deterministic fixture

A first tiny fixture attempted to test a conservative `fex_gen_type<function-pointer>` both-role registration. Run `31789808989` caused thunkgen itself to segfault before role validation.

The failure exposed an existing representation mismatch: explicit function-pointer registration stored the pointer type in `thunked_funcptrs`, while downstream data-layout code assumes a `FunctionProtoType`. The role transform is being tightened to store the pointee function prototype, consistent with ordinary callback registration.

The deterministic role fixture was then changed to avoid depending on that edge for the OR test:

- one callback-only signature is registered only by an ordinary callback parameter;
- another canonical signature appears once as an ordinary callback and once as an `indirect_guest_calls` API, so deduplication must produce `caller=1, unpacker=1`.

## Direct accessor output — active

The text-extractor prototype generated both resident bridge definitions and typed wrapper accessors. To remove generated-C++ parsing completely, thunkgen now has a research companion mode:

```
-guest-bridge-accessors
```

The intended contract is:

- `-guest-bridge`: definitions/instantiations in the resident DSO;
- `-guest-bridge-accessors`: declarations and typed specializations consumed by the unloadable wrapper.

Exported caller/unpacker functions use a symbol suffix derived from the canonical signature SHA-256 rather than the iteration index. This matters because bridge definitions and accessors are produced by separate thunkgen invocations; no correctness assumption should depend on `unordered_map` traversal order.

The accessor fragment provides typed selectors for:

- resident guest callers;
- resident callback unpackers;
- `FEXAllocateResidentHostTrampolineForGuestFunction`, which passes the resident unpacker to FEX at trampoline allocation time.

That last property is the one directly validated by the CUDA `GuestUnpacker` ownership trace.

## Next gate

The active role workflow now needs to prove all three role states without text parsing:

1. real GL/Vulkan: caller-only;
2. fixture callback-only: unpacker-only;
3. fixture overlapping callback + indirect signature: both.

After that, the same direct role/accessor output becomes the base for CUDA's generated `callback_member` moved-reload test, replacing the Python extractor while retaining the already-proven `GuestUnpacker` ownership invariant.
