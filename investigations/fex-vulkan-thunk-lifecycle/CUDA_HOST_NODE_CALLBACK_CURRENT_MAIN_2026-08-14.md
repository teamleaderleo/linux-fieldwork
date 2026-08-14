# CUDA host-node callback escape on current FEX — 2026-08-14

## Result

A GPU-free hosted ARM64 discriminator demonstrates a non-Vulkan nested callback escape in current FEX.

Owned-fork run:

`31784877322`

Exact FEX product source:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

The workflow carrier contains only `LinuxFieldwork/` probe fixtures plus the workflow before the build. Its product-source diff guard across `ThunkLibs`, `FEXCore`, and `Source` is empty.

Artifact:

- id: `9213201181`
- name: `agent-b-cuda-hostnode-callback-31784877322`
- digest: `sha256:ceb13d373c81ee87c7df06a107bcbdedd1009c5b8eb4a42c8e3d8e7de7fe30ce`

## Source shape

Current FEX actively thunks the CUDA graph host-node API while treating the callback-bearing host-node parameter structure as opaque on the 64-bit path.

The pinned CUDA definition represented by FEX contains a host callback plus user data:

```c
struct CUDA_HOST_NODE_PARAMS_st {
  CUhostFn fn;
  void *userData;
};
```

The first discriminator targets `cuGraphAddHostNode`.

## Why no GPU is required for this discriminator

The generated CUDA host thunk only needs `dlopen("libcuda.so.1")` to succeed; individual generated loader slots are populated with `dlsym` and are not all required to be non-NULL at initialization.

The workflow therefore builds a tiny native ARM64 `libcuda.so.1` that exports only `cuGraphAddHostNode`. That endpoint logs the callback-bearing structure it receives, immediately invokes `nodeParams->fn(nodeParams->userData)`, writes a deterministic dummy node handle, and returns success.

This isolates the thunk ABI/callback conversion boundary without CUDA context setup, graph execution, or GPU hardware.

## Native control

The native ARM probe reports:

```text
CUDA_PROBE callback=<arm64 callback> add_host=<synthetic host function> params=<stack>
MARK add-enter
SYNTH_CUDA_ADD graph=0x1111 deps=(nil) count=0 params=<stack> fn=<arm64 callback> user=0x12345678
CUDA_HOST_CALLBACK count=1 user=0x12345678
MARK add-return rc=0 node=0xc0de callbacks=1
```

Native exit is `0`.

## Pristine FEX result

The same x86-64 guest probe under exact FEX reaches:

```text
CUDA_PROBE callback=0x55db3c38c370 add_host=0x7ffff7ea6b80 params=0x7fffffffd600
MARK add-enter
SYNTH_CUDA_ADD graph=0x1111 deps=(nil) count=0 params=0x7fffffffd600 fn=0x55db3c38c370 user=0x12345678
```

and then exits by SIGILL:

```text
native=0
pristine_fex=132
```

There is no `CUDA_HOST_CALLBACK` marker and no `MARK add-return`.

The synthetic native endpoint therefore receives the raw x86 guest callback address in the callback-bearing structure and faults when native ARM code invokes it.

## Interpretation

This promotes the CUDA host-node structure from a source-level callback hazard to a demonstrated current-main cross-ISA callback defect.

It is structurally analogous to the DRM `drmEventContext` failure rather than to Vulkan proc-address routing:

- the callback is nested inside an otherwise ABI-compatible/opaque structure;
- the public thunked API itself is found and called normally;
- the failure occurs when the native host library consumes a function-pointer field that FEX did not mediate.

The already demonstrated research `callback_member` generator mechanism is therefore a direct repair discriminator for this CUDA path.

## Boundary

The synthetic host endpoint invokes the callback synchronously inside `cuGraphAddHostNode`. This proves the cross-ISA structure conversion defect, but it does not model the real NVIDIA driver's deferred graph-node execution/lifetime semantics. A real-driver graph create/add/instantiate/launch test is a separate follow-up.

This is owned-fork research evidence, not upstream-ready contribution code.