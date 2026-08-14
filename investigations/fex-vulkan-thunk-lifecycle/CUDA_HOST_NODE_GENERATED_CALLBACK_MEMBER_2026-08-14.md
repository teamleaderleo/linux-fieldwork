# Generated CUDA host-node callback-member repair — 2026-08-14

## Result

The same generic research `callback_member` extension previously demonstrated on DRM also repairs CUDA host-node callback conversion on exact current FEX product source.

Owned-fork run:

`31785286590`

Exact FEX source before the runtime-applied diagnostic:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

Artifact:

- id: `9213343773`
- name: `agent-b-cuda-hostnode-callback-member-31785286590`
- digest: `sha256:4b801bb517eb6f178372c49b48f87456b5577eb7bb74a9dc1a87e93ad5fed285`

## Product-source delta

The workflow applies only the generic callback-member generator prototype plus one CUDA interface annotation. It restores the DRM interface before building, so the product delta is limited to:

- `ThunkLibs/Generator/analysis.cpp`
- `ThunkLibs/Generator/analysis.h`
- `ThunkLibs/Generator/gen.cpp`
- `ThunkLibs/include/common/GeneratorInterface.h`
- `ThunkLibs/libcuda/libcuda_interface.cpp`

The CUDA-specific metadata change is conceptually:

```cpp
template<>
struct fex_gen_type<CUDA_HOST_NODE_PARAMS_st> {};

template<>
struct fex_gen_config<&CUDA_HOST_NODE_PARAMS_st::_0> : fexgen::callback_member {};
```

There is no handwritten CUDA `Guest.cpp` / `Host.cpp` callback conversion in this lane.

## Generated code shape

Thunkgen emits callback-bearing temporary copies at every generated CUDA call site using `CUDA_HOST_NODE_PARAMS_st`.

The retained generated guest markers include four call sites, for example:

```text
CUDA_HOST_NODE_PARAMS_st fex_callback_copy_4 {};
fex_callback_copy_4 = *a_4;
fex_callback_copy_4._0 = AllocateHostTrampolineForGuestFunction(a_4->_0);
args.a_4 = a_4 ? &fex_callback_copy_4 : nullptr;
```

and analogous copies for other host-node parameter positions.

Generated host-side unpacking contains the corresponding typed finalization, for example:

```text
auto fex_callback_4__0 = args->a_4.get_pointer()->data._0;
FinalizeHostTrampolineForGuestFunction(fex_callback_4__0);
a_4.data->data._0 = reinterpret_cast<...>(uintptr_t { fex_callback_4__0.data });
```

This shows the annotation covers the host-node parameter type across the generated CUDA API family rather than special-casing only `cuGraphAddHostNode`.

## Runtime matrix

The same GPU-free synthetic `libcuda.so.1` discriminator used for the pristine finding reports:

```text
native=0
pristine_reference=132
generated_candidate=0
```

Candidate stderr:

```text
CUDA_PROBE callback=0x55a62d6b3370 add_host=0x7ffff7ea5b80 params=0x7fffffffd5e0
MARK add-enter
SYNTH_CUDA_ADD graph=0x1111 deps=(nil) count=0 params=0xffffcb580760 fn=0x7ffff7e5c000 user=0x12345678
CUDA_HOST_CALLBACK count=1 user=0x12345678
MARK add-return rc=0 node=0xc0de callbacks=1
```

The important pointer transition is visible directly: pristine FEX delivered the raw guest callback address into the native endpoint, while the generated candidate supplies a host trampoline at `0x7ffff7e5c000`. The native endpoint calls that trampoline, the guest callback executes exactly once with the expected user data, and the CUDA API returns normally.

## Interpretation

This is cross-library evidence that `callback_member` is a generic thunkgen capability rather than a DRM-specific repair technique.

The same mechanism now has successful ARM64 runtime evidence for:

- `drmEventContext` callback fields through `drmHandleEvent`;
- `CUDA_HOST_NODE_PARAMS_st::CUhostFn` through CUDA graph host-node APIs.

It also preserves the important caller-input rule: generated guest code copies the callback-bearing structure and rewrites only the temporary copy, rather than mutating caller-owned input.

## Lifetime boundary

This run uses the ordinary wrapper-local callback unpacker. It proves cross-ISA callback conversion, not unload safety. Real CUDA graph host nodes execute their host function when the graph node runs, so a driver can retain callback state beyond the API call that configured the node. A per-library resident CUDA bridge is therefore the next relevant lifetime discriminator if the ordinary CUDA guest wrapper is allowed to unload.

A real NVIDIA-driver graph instantiate/launch test remains useful as a separate fidelity check; it is not required to establish the immediate nested callback conversion defect or the generated repair shown here.

This is fork-local research code and evidence, not upstream-ready contribution code.