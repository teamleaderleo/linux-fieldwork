# Hosted ARM64 Finding A run receipts

This file records the disposable owned-fork CI runs separately from interpretation.

## Focused run 1 — build/rootfs success, runtime preflight failure

```text
repository: teamleaderleo/FEX
branch: ci/agent-c-finding-a-arm64-20260814
workflow commit: df00c0e017e0547f59cd57e9e44ae854971bd4a8
Actions run: 31729297543
job: 94545383909
source checkout under test: 71afe476751deac24adabd1adb575fd2337b6e0a
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

Interpretation: the focused host target `vulkan-host-64` builds the FEX interpreter and thunk generator, but direct execution also requires the `FEXServer` runtime target. No guest program body executed in this run. This is a CI/runtime-target omission, not Finding A product behavior.

Source confirmation: `Source/Tools/FEXServer/CMakeLists.txt` defines `FEXServer` as its own executable target, so it must be included in the focused runtime build.

## Corrected rerun

The disposable workflow was updated at owned-fork commit:

```text
2e304b03dee0b6d3028d7c12129b427116e7015c
```

Focused host build now requests:

```sh
cmake --build fex-src/build --target vulkan-host-64 FEXServer -- -j"$(nproc)" -v
```

and asserts all of:

```text
fex-src/build/Bin/FEX
fex-src/build/Bin/FEXServer
fex-src/build/Bin/thunkgen
fex-src/build/HostLibs_64/libvulkan-host.so
```

Two disposable workflows on the branch received the correction. The compact v2 receipt run is:

```text
Actions run: 31730358268
job: 94549010055
source checkout under test: 71afe476751deac24adabd1adb575fd2337b6e0a
```

Status at file creation: running. Add its final phase matrix and artifact identity below when complete.
