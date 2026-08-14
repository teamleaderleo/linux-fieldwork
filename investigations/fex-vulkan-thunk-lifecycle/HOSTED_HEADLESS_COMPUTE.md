# Hosted x86 Vulkan headless compute baseline

## Purpose

Canonical hosted ARM64 receipt proving that the FEX Vulkan lane can execute and verify real Vulkan work beyond loader/proc-address behavior or physical-device enumeration.

This baseline deliberately avoids window-system surfaces. It exercises a compute pipeline, command submission, shader execution, host-visible buffer readback, full object cleanup, and guest thunk `dlclose` against native ARM64 Lavapipe.

## Exact receipt

```text
repository: teamleaderleo/FEX
exact product candidate: c011366706eaf65a00380003989b3a10811212b6
Actions run: 31784278038
job: 94716605099
workflow commit: e32da017c1e9861a6b81262b79c6ce8ddcea63e4
artifact: 9212994500
artifact SHA-256: b5595f6f89d245e5a4af7449a13f8b89de59f5136cafdd90b028672cb2aa4dfe
runner: ubuntu-24.04-arm
host Vulkan: Mesa Lavapipe
```

## Workload

The x86-64 guest probe dynamically loads the generated FEX Vulkan guest thunk and performs:

```text
dlopen(libvulkan.so.1)
create Vulkan instance
enumerate physical device
select compute queue family
create device + queue
create storage buffer
allocate/bind HOST_VISIBLE|HOST_COHERENT memory
map and initialize 64 uint32 values to 0..63
create descriptor set layout/pool/set
update storage-buffer descriptor
create shader module from SPIR-V
create pipeline layout
create compute pipeline
record command buffer
bind pipeline + descriptor set
dispatch 64 x 1 x 1
submit + queue wait idle
map buffer and verify every value == original + 1
cleanup Vulkan objects
dlclose guest Vulkan thunk
return
```

The GLSL compute shader is intentionally tiny:

```glsl
#version 450
layout(local_size_x = 1) in;
layout(set = 0, binding = 0) buffer Data { uint values[]; } data;
void main() {
  data.values[gl_GlobalInvocationID.x] += 1;
}
```

Probe input hashes:

```text
x86 compute probe: bdb683d6a14573d3a3945ec4d5f6421407070e3d8af0f4547f545cc5f3cdd797
SPIR-V:           326a298311705ae70b21cb0ca6451fcaab8b63cb1f164472d95286a8b3398aae
```

## Result

Process exit:

```text
0
```

Phase receipt:

```text
COMPUTE_AFTER_DLOPEN
COMPUTE_AFTER_INSTANCE
COMPUTE_AFTER_DEVICE
COMPUTE_AFTER_PIPELINE
COMPUTE_AFTER_DISPATCH
COMPUTE_VERIFY_OK
COMPUTE_CLEANUP_DONE
COMPUTE_BEFORE_DLCLOSE
COMPUTE_AFTER_DLCLOSE
COMPUTE_RETURN
```

`COMPUTE_VERIFY_OK` is emitted only after mapping the result buffer and checking all 64 entries equal `i + 1`.

## Interpretation

The hosted ARM64 lane now demonstrates functional Vulkan execution through:

```text
x86-64 guest application
  -> generated FEX Vulkan guest thunk
  -> FEX
  -> ARM64 Vulkan host thunk
  -> native Lavapipe
  -> shader execution / memory writeback
  -> guest-visible verified result
```

This is stronger than a `vulkaninfo` enumeration receipt and provides a useful lower-layer baseline before window-system, Wine/DXVK, driver-diversity, or more exotic Vulkan structure work.

The full cleanup and `dlclose` also exit 0, consistent with the separate ordinary-lifecycle matrix. This does not weaken the forced-different-remap Finding B result; it further narrows that failure away from normal compute-object teardown and ordinary guest-thunk unload.

## Reuse

Future Vulkan investigations can treat this as the known-good hosted functional baseline. When a higher-level workload fails, compare its first missing phase against this workload before attributing the failure to generic Vulkan execution.