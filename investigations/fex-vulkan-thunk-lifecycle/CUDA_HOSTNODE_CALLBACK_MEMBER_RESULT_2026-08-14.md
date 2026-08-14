# CUDA host-node `callback_member` result — 2026-08-14

## Scope

Carrier: `teamleaderleo/FEX` branch `ci/agent-b-cuda-hostnode-callback-member-20260814`, head `9cf11fc6101e1ca05170b88eb8f8ad4ce9ee8bdd`.

Exact product baseline: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

GitHub Actions:

```text
run: 31785286590
job: 94719719529
artifact: 9213343773
artifact sha256: 4b801bb517eb6f178372c49b48f87456b5577eb7bb74a9dc1a87e93ad5fed285
```

## Result

The generic nested `callback_member` generator prototype successfully mediated a CUDA host-node callback carried inside `CUDA_HOST_NODE_PARAMS_st`.

Runtime matrix:

```text
native=0
pristine_reference=132
generated_candidate=0
```

The pristine FEX reference lacks the generated nested-member mediation path. The generated candidate reaches the synthetic native CUDA endpoint, invokes the guest callback through FEX, preserves `userData`, and returns cleanly:

```text
CUDA_PROBE callback=0x55a62d6b3370 add_host=0x7ffff7ea5b80 params=0x7fffffffd5e0
MARK add-enter
SYNTH_CUDA_ADD graph=0x1111 deps=(nil) count=0 params=0xffffcb580760 fn=0x7ffff7e5c000 user=0x12345678
CUDA_HOST_CALLBACK count=1 user=0x12345678
MARK add-return rc=0 node=0xc0de callbacks=1
```

## Generated guest-side form

The annotation changes `CUDA_HOST_NODE_PARAMS_st` from opaque to repackable and marks the callback member `_0`:

```cpp
template<>
struct fex_gen_type<CUDA_HOST_NODE_PARAMS_st> {};
template<>
struct fex_gen_config<&CUDA_HOST_NODE_PARAMS_st::_0> : fexgen::callback_member {};
```

Thunkgen then emits a caller-owned-input-preserving aggregate copy and replaces only the callback field in that copy:

```cpp
CUDA_HOST_NODE_PARAMS_st fex_callback_copy_4 {};
if (a_4) {
  fex_callback_copy_4 = *a_4;
  fex_callback_copy_4._0 = AllocateHostTrampolineForGuestFunction(a_4->_0);
}
args.a_4 = a_4 ? &fex_callback_copy_4 : nullptr;
```

The same generated pattern appears at the other CUDA entrypoints that accept this parameter type.

## Generated host-side form

The host unpacker finalizes the already-allocated callback trampoline and installs its native callable address in the repacked aggregate:

```cpp
auto fex_callback_4__0 = args->a_4.get_pointer()->data._0;
FinalizeHostTrampolineForGuestFunction(fex_callback_4__0);
a_4.data->data._0 = reinterpret_cast<decltype(a_4.data->data._0)>(uintptr_t { fex_callback_4__0.data });
```

## Interpretation

This is a second API-family proof for the semantic member annotation after DRM. It shows that nested callback mediation can be expressed once in thunkgen and applied to callback-bearing aggregates without handwritten per-command bridge wrappers.

The useful generator rule is semantic and directional:

- a callback-bearing member is explicitly annotated as native-to-guest callable;
- guest code copies the aggregate instead of editing caller-owned input;
- only the annotated function-pointer member is replaced;
- host code finalizes the generated callback trampoline;
- reverse callback machinery is emitted for the annotated member signature, not inferred for every function signature in the API.

That rule aligns with the i386 GL finding that resident host-call invokers and resident callback unpackers must be separate generated sets.

## Integration with const-pointee correction

This prototype predates the separately proven thunkgen fix that preserves `const` pointees in `repack_wrapper<T>`. The two changes are complementary. `callback_member` should continue to copy callback-bearing input aggregates, while generic repack generation should preserve source constness so unrelated repackable `const T*` inputs never receive accidental exit writeback.
