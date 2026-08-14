# Hosted ordinary Vulkan lifecycle matrix

## Purpose

Supplementary Finding B discriminator on the hosted ARM64/Lavapipe lane. This is intentionally narrower than the existing forced-different-remap PFN lifetime work in `APPLICATION_TEARDOWN_LOG.md`.

The question here was only whether ordinary guest Vulkan thunk load/use/unload, reference counting, `RTLD_NODELETE`, or repeated load/unload is sufficient to reproduce the teardown failure on the real Ubuntu amd64 hosted rootfs.

## Exact source and run

```text
FEX candidate: c011366706eaf65a00380003989b3a10811212b6
Actions run: 31783927903
job: 94715486297
artifact: 9212880416
artifact SHA-256: c51a54b0f2e312efcc9e776161d8d459271baaba2de556a925f29f3d60f2cf4c
runner: ubuntu-24.04-arm
host Vulkan: Lavapipe
```

The guest rootfs uses Ubuntu 24.04 amd64 packages resolved by foreign debootstrap, with deferred package payloads extracted by the ARM host. The generated `libvulkan-guest.so` replaces guest `libvulkan.so.1`, and real distro x86 `libX11.so.6` supplies the guest thunk constructor helpers.

## Matrix

```text
load-close=0
normal-close=0
no-close=0
nodelete=0
extra-ref=0
repeat=0
close-_exit=0
```

`normal-close` performs:

```text
dlopen(libvulkan.so.1)
vkCreateInstance
vkEnumeratePhysicalDevices
vkDestroyInstance
dlclose
normal process return
```

and reaches every phase cleanly.

`repeat` performs the same create/enumerate/destroy/dlclose cycle 20 times in one process. All 20 iterations complete with `DLCLOSE_RESULT=0`; the run exits 0.

`load-close`, `RTLD_NODELETE`, an extra pair of `dlopen` references, skipping `dlclose`, and using `_exit` after a normal close all also exit 0.

## Interpretation

Ordinary Vulkan guest thunk load/use/unload is **not sufficient** to reproduce Finding B on this hosted rootfs and exact candidate.

This result is consistent with the stronger parallel teardown work: the meaningful Finding B trigger is the forced-different guest-thunk remap / stale dynamic-PFN lifetime scenario, not normal `dlclose` by itself.

Do not use this matrix to weaken the forced-remap finding. Its value is negative discrimination: it removes several ordinary lifetime hypotheses and keeps the failure boundary narrow.

## Follow-up implication

No more ordinary `dlclose` stress is warranted unless a new workload produces contradictory evidence. Future Finding B work should build on the existing forced-remap PFN-lifetime candidate and application teardown receipts rather than expanding this matrix.