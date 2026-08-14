# Thunkgen callback_member + bridge-role unit proof

Date: 2026-08-14

FEX branch: `ci/thunkgen-callback-member-bridge-role-unit-20260814`

Successful workflow run: `31798634940`

Artifact: `9218396850` (`thunkgen-callback-member-v3-31798634940`)

Base integration source: `48e28a2ce9da1334feb8d7b77dbade66efa24be2`

## Observed contracts

A focused synthetic record combines `custom_repack` and `callback_member` on the same containing type:

```cpp
struct Hooks { void* user; int (*cb)(int); };
template<> struct fex_gen_config<&Hooks::user> : fexgen::custom_repack {};
template<> struct fex_gen_config<&Hooks::cb> : fexgen::callback_member {};
```

The generated guest code copies the input record before replacing the callback field:

```text
fex_callback_copy_0 = *a_0;
fex_callback_copy_0.cb = AllocateHostTrampolineForGuestFunction(a_0->cb);
args.a_0 = a_0 ? &fex_callback_copy_0 : nullptr;
```

The workflow explicitly compared source line numbers and verified copy-before-rewrite ordering.

The generated host code contains both the custom repack entry path and generated callback finalization/assignment:

```text
fex_custom_repack_entry(...)
FinalizeHostTrampolineForGuestFunction(fex_callback_0_cb);
data.cb = reinterpret_cast<...>(... fex_callback_0_cb.data ...);
```

The same canonical `int (int)` signature was required both as a caller and an unpacker. Bridge emission produced exactly one canonical role entry with both requirements ORed:

```text
FEX_BRIDGE_ROLE ... caller=1 unpacker=1 ... int (int)
```

The accessor output contains both `FEXResidentBridgeInvoker` and `FEXResidentBridgeUnpacker` for that signature.

The same contracts passed under `-for-32bit-guest`; the canonical signature/hash remained a single merged caller+unpacker entry.

## Rejection contracts

A non-function-pointer member annotated with `callback_member` exited nonzero with:

```text
callback_member requires a function-pointer field
```

A variadic function-pointer member exited nonzero with:

```text
Variadic callback members are not supported by this prototype
```

Final workflow marker:

```text
THUNKGEN_CALLBACK_MEMBER_BRIDGE_ROLE_OK
```

## Conclusion

`callback_member` now has focused generator-level evidence independent of Vulkan, DRM, CUDA, or Wayland integration. The covered invariants are guest copy-before-rewrite, host finalization, composition with `custom_repack`, canonical caller/unpacker role merging, 32-bit guest parity, and explicit rejection of unsupported member/variadic cases.
