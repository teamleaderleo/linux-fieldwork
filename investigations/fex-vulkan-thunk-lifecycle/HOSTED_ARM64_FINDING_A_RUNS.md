# Hosted ARM64 Finding A run receipts

This file records the disposable owned-fork CI runs separately from interpretation. Source under test in every focused run was exactly:

```text
teamleaderleo/FEX
71afe476751deac24adabd1adb575fd2337b6e0a
```

## Focused run 1 — omitted FEXServer

```text
branch: ci/agent-c-finding-a-arm64-20260814
workflow commit: df00c0e017e0547f59cd57e9e44ae854971bd4a8
Actions run: 31729297543
job: 94545383909
artifact id: 9192696708
artifact name: agent-c-finding-a-arm64-31729297543
artifact digest: sha256:6f9689dd41101d944bf2c7e087dd4fe776c2bc2eadac86e724c7561b1f29aff7
```

Passed before runtime:

- focused apt dependency delta;
- native ARM64 Lavapipe `vulkaninfo` control;
- native ARM64 positive debug-report callback control;
- exact-head FEX configure;
- focused `vulkan-host-64` build;
- standalone 64-bit `vulkan-guest` build;
- amd64 Ubuntu 24.04 OCI rootfs export;
- x86-64 probe compilation;
- diagnostic-only host-thunk rebuild;
- receipt upload.

Observed x86 matrix:

```text
static-smoke=255
dynamic-plain=255
dynamic-vulkan=255
report-direct=255
report-gipa-baseline=255
report-gipa-candidate=255
first_owner=fex-runtime-or-rootfs
```

Representative stderr:

```text
E Couldn't execute: FEXServer
E FEXServerClient: Failure to setup client
E This means the squashFS rootfs won't be mounted.
E Expect errors!
```

Interpretation: `vulkan-host-64` builds the FEX interpreter and thunk generator, while direct execution also needs the separate `FEXServer` executable. This run contains no guest-program execution evidence.

## Focused run 2 — FEXServer fixed, stale phase-helper warning

The disposable branch was updated to include `FEXServer` explicitly. Compact v2 receipt:

```text
CI commit: 2e304b03dee0b6d3028d7c12129b427116e7015c
Actions run: 31730358268
job: 94549010055
artifact id: 9193096674
artifact name: agent-c-finding-a-arm64-v2-31730358268
artifact digest: sha256:b31bb845a1ef1a82758715dd849a8704d8c44a834918d7eeab7970db76b998db
```

This run proved the corrected focused host target set:

```sh
cmake --build fex-src/build --target FEXServer vulkan-host-64 -- -j"$(nproc)" -v
```

and verified:

```text
fex-src/build/Bin/FEX
fex-src/build/Bin/FEXServer
fex-src/build/Bin/thunkgen
fex-src/build/HostLibs_64/libvulkan-host.so
guest-build/libvulkan-guest.so
```

The next failure came while compiling the temporary x86 phase helper:

```text
error: ignoring return value of ‘write’ declared with attribute ‘warn_unused_result’ [-Werror=unused-result]
```

Owner: internal probe harness. The generated amd64 rootfs had already exported successfully and the loader path existed. No x86 execution occurred in this v2 run.

## Focused run 3 — clean execution boundary

The phase helper was corrected to assign the `write()` result to a variable. Final focused receipt:

```text
workflow: .github/workflows/agent-c-finding-a-arm64-v3.yml
CI commit: 703aba05f73721194ebbbd1415283c68311fb6ff
Actions run: 31730826384
job: 94550630116
artifact id: 9193286936
artifact name: agent-c-finding-a-arm64-v3-31730826384
artifact size: 39938 bytes
artifact digest: sha256:3a79b0afddba07f8d01856120b91928bb6ab8e2eb5ceba454be0eeaa5690f392
source under test: 71afe476751deac24adabd1adb575fd2337b6e0a
result: workflow success
```

Every job phase completed successfully, including native Lavapipe, focused FEX runtime build, standalone 64-bit Vulkan guest thunk build, amd64 OCI rootfs export, x86 probe build, baseline phase matrix, diagnostic host-thunk rebuild, candidate execution, and receipt upload.

Exact execution matrix:

```text
static=0
plain=0
vulkan=132
direct=132
gipa_baseline=132
gipa_candidate=132
first_owner=vulkan-guest-load
```

The distinguishing stderr markers were:

```text
static:
STATIC_SMOKE_MAIN

plain:
PHASE_MAIN
PHASE_PLAIN_EXIT

vulkan:
PHASE_MAIN
PHASE_BEFORE_DLOPEN
```

The Vulkan phase never printed `PHASE_AFTER_DLOPEN`. Exit `132` is the SIGILL class. Direct callback, GIPA baseline, and the diagnostic GIPA candidate all hit the same earlier SIGILL, so they do not distinguish Finding A in this focused staging path.

Interpretation:

- GitHub-hosted ARM64 executes real x86-64 programs under the exact FEX head: static and dynamic controls both exit `0`.
- Native ARM64 software Vulkan works before FEX execution.
- The focused 64-bit host and guest Vulkan thunk targets build successfully.
- The first incomplete owner is the generated guest Vulkan thunk load/staging path: `dlopen("libvulkan.so.1")` enters the generated `libvulkan-guest.so` and reaches SIGILL before returning to the probe.
- The one-line Finding A diagnostic host-thunk route cannot affect this earlier failure, which is why baseline and candidate both remain `132`.

This clean boundary complements the earlier broad Fieldwork hosted run, which used FEX's normal installed thunk/overlay setup and reached the x86 Vulkan callback SIGILL. The broad run's callback A/B was contaminated by accidental 32-bit host-thunk selection, so it remains evidence that hosted x86 Vulkan execution can reach the callback area, not a valid baseline/candidate comparison.

## Focused dependency set that passed

The smallest set actually tested successfully for this focused build lane was:

```text
cmake ninja-build clang lld libclang-dev llvm-dev pkg-config
gcc-x86-64-linux-gnu g++-x86-64-linux-gnu
libcap-dev libgl-dev
libx11-dev libx11-xcb-dev libxcb1-dev libxrandr-dev libxrender-dev
mesa-vulkan-drivers vulkan-tools
```

This is the smallest tested passing set, rather than a proof that every package is irreducible. It removes the broad recipe's i686 toolchain and unrelated SDL, Wayland, DRM, ALSA, GLFW, epoxy, and EGL development packages.

## Runtime rootfs receipt

The hosted runtime filesystem was created without executing an amd64 process in Docker:

```sh
docker pull --platform=linux/amd64 ubuntu:24.04
cid="$(docker create --platform=linux/amd64 ubuntu:24.04 /bin/true)"
docker export "$cid" | tar -C "$ROOTFS" -xf -
```

The focused lane then placed the generated thunk directly at:

```text
$ROOTFS/usr/lib/x86_64-linux-gnu/libvulkan.so.1
```

That direct placement is now the first staging difference to investigate. A next hosted discriminator should switch to FEX's normal ThunksDB/GuestThunks overlay path while preserving the same exact FEX SHA, rootfs, 64-bit host thunk, Lavapipe driver, and small callback probe.

## Current bounded result

Hosted ARM64 is practical for Finding A work. It can cover build, software Vulkan, amd64 rootfs creation, FEX runtime startup, and ordinary x86-64 execution. The focused direct-placement variant stops one phase before the callback boundary at guest Vulkan thunk loading. The earlier normal-overlay hosted run demonstrates that the callback boundary itself is reachable on the same class of runner.
