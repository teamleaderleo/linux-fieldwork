# Direct thunkgen bridge role/accessor gate — 2026-08-14

Branch: `teamleaderleo/FEX:diagnostic/thunkgen-bridge-role-output-20260814`

Workflow run: `31791079045` — success.

## Contract validated

Thunkgen now has research outputs for:

```
-guest-bridge
-guest-bridge-accessors
```

Function-pointer registrations carry orthogonal bridge roles:

```
needs_caller
needs_unpacker
```

Canonical signatures are deduplicated while ORing those role requirements. Bridge definitions and accessor declarations use stable SHA-256-derived symbol suffixes, so their identity does not depend on `unordered_map` iteration order across separate thunkgen invocations.

## Receipt

```
gl_total=736
gl_caller_only=736
gl_unpacker_only=0
gl_both=0

vulkan_total=476
vulkan_caller_only=476
vulkan_unpacker_only=0
vulkan_both=0

fixture_total=2
fixture_unpacker_only=1
fixture_both=1
```

Fixture detail:

```
caller=1 unpacker=1 hash=8d71f6460eaa4744188547f22727f2e336c403db5d29c6210fc34903429ca2d1 int (int)
caller=0 unpacker=1 hash=396cb1802947f7689e0324c4ebbcdb15d3576e2e9b74659654fc7f1971df2d59 void (int)
```

The `int(int)` canonical signature is deliberately registered once as an ordinary callback and once as an `indirect_guest_calls` API. The final bridge correctly emits both roles under one stable hash.

The `void(int)` signature is callback-only and emits only the resident unpacker role.

## GL significance

All 736 current stock GL bridge signatures are caller-only. Therefore the large dynamic-PFN signatures — including the earlier 23-argument compile discriminator — no longer instantiate `CallbackUnpack` at all.

This is the intended correction to the flat-signature bridge prototype.

## Accessor identity gate

The workflow separately generates bridge definitions and accessor declarations, then compares the normalized role sets by:

```
(caller, unpacker, canonical-signature hash, signature text)
```

The sets match for:

- GL;
- Vulkan;
- the deterministic role fixture.

For each role entry, the validator also checks that the corresponding hash-named exported symbol exists only when required:

```
fex_bridge_invoker_<hash>()
fex_bridge_unpacker_<hash>()
```

The direct Vulkan companion still links with `DF_1_NODELETE` under the role-aware generator transform.

## Explicit function-pointer representation fix

The role work also exposed and corrected a representation edge: explicit `fex_gen_type<function-pointer>` registration must store the pointee `FunctionProtoType` in the bridge registry, consistent with generated callback registrations, rather than leaving the pointer type for downstream code that expects a function prototype.

## Next integration

The next gate is CUDA generated `callback_member` lifetime using these direct outputs only:

- no `extract_guest_bridge.py`;
- direct role-aware bridge definitions;
- direct typed accessors;
- pre-close callback control;
- traced `HostToGuestTrampoline.GuestUnpacker` ownership;
- physical generation-1 unload;
- forced moved generation 2;
- no callback re-registration;
- retained callback must fail with wrapper-local unpacker and pass with resident direct-generated unpacker.
