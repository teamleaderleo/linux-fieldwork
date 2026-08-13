# Hosted ARM64 lane for Finding A

## Purpose

This note records the disposable GitHub-hosted ARM64 path for the FEX Vulkan callback-routing Finding A work. It is internal investigation machinery and evidence. It is separate from any eventual FEX contribution history.

Authority boundary for this lane:

- owned repositories may be mutated for experiments;
- no FEX upstream contact or mutation is part of this work;
- any third-party FEX GitHub reference used in interaction text should use `https://redirect.github.com/FEX-Emu/FEX/...`;
- AI-generated experiment code in this lane is internal diagnostic material only.

## Exact source identity

The reviewed FEX source under test is:

```text
teamleaderleo/FEX main
71afe476751deac24adabd1adb575fd2337b6e0a
```

The disposable owned-fork CI branch is:

```text
ci/agent-c-finding-a-arm64-20260814
```

The first Agent C workflow commit on that disposable branch is:

```text
df00c0e017e0547f59cd57e9e44ae854971bd4a8
.github/workflows/agent-c-finding-a-arm64.yml
```

The workflow checks out `71afe476751deac24adabd1adb575fd2337b6e0a` again into a separate source directory and asserts `git rev-parse HEAD` before compiling. The workflow commit itself therefore does not become part of the FEX source revision being tested.

## What hosted ARM64 has already proven

The existing Fieldwork callback-probe lane has already executed on GitHub's `ubuntu-24.04-arm` hosted runner and established all of the following:

1. A real hosted ARM64 runner is available for this workload. The observed machine was AArch64 / Neoverse-N2 with four CPUs and about 16 GiB RAM.
2. FEX at exact reviewed source `71afe476751deac24adabd1adb575fd2337b6e0a` configures and builds on the hosted ARM64 runner.
3. The FEX Vulkan host and guest thunks build there.
4. Native ARM64 Lavapipe works there. The native callback probes can create Vulkan debug-report/debug-utils callbacks and receive forced callbacks successfully.
5. An amd64 Ubuntu 24.04 filesystem can be created without executing amd64 container code: pull `ubuntu:24.04` with `--platform=linux/amd64`, `docker create`, then `docker export | tar`. The observed image digest was `sha256:561618e2c15bf2397621dd04f96926663a3b5616c189cf7e38db7e82f5c538ea`.
6. FEX can enter the x86-64 Vulkan test path on that hosted ARM64 runner. A previous callback probe reached SIGILL / exit 132 in x86-under-FEX execution.

The earlier broad callback run was:

```text
Fieldwork Actions run: 31727031022
job: 94537864515
artifact: 9191874452
artifact name: fex-vulkan-callback-probe-31727031022
artifact zip SHA-256: 3159b5913d2b7839582f26a8a681aa1c83780b9af26d66652216f2127f879115
```

That run is useful execution evidence, with one important CI wiring defect described below.

## Earlier CI defects that are not product evidence

### Wrong host thunk selected in the broad callback baseline

The broad callback workflow discovered the host thunk with:

```sh
find "$GITHUB_WORKSPACE/fex-install" -type f -name libvulkan-host.so | head -1
```

The installed tree contained both:

```text
lib/fex-emu/HostThunks/libvulkan-host.so
lib/fex-emu/HostThunks_32/libvulkan-host.so
```

The loose `find | head -1` selected the 32-bit host thunk for the baseline even though the guest workload was x86-64. The later candidate rebuild explicitly targeted `vulkan-host-64`, so the baseline/candidate comparison from that job is contaminated by different host-thunk bitness.

Owner: CI wiring.

Action: every new hosted Finding A run names `build/HostLibs_64/libvulkan-host.so` explicitly. No recursive `find` chooses thunk bitness.

### Guest phase-probe compile failure

A later phase-discriminator run was:

```text
Fieldwork Actions run: 31728112714
job: 94541471368
```

Its exact FEX build completed successfully, then the x86 phase helper failed at compile time because the helper ignored the return value of `write(2, ...)` while compiling with `-Werror`:

```text
error: ignoring return value of ‘write’ declared with attribute ‘warn_unused_result’ [-Werror=unused-result]
```

No x86 execution occurred in that job.

Owner: probe harness.

Action: the Agent C focused workflow uses a corrected phase helper that consumes the `write()` result and adds a separate static x86-64 smoke test.

## Focused dependency strategy

FEX's existing GitLab ARM64 job is a useful upper bound, but it builds much more than Finding A needs. The hosted Finding A lane drops the i686 toolchain and unrelated guest-thunk dependencies first.

Current focused explicit apt delta:

```text
cmake
ninja-build
clang
lld
libclang-dev
llvm-dev
pkg-config
gcc-x86-64-linux-gnu
g++-x86-64-linux-gnu
libcap-dev
libgl-dev
libx11-dev
libx11-xcb-dev
libxcb1-dev
libxrandr-dev
libxrender-dev
mesa-vulkan-drivers
vulkan-tools
```

Why some apparently unrelated development packages remain:

- host-thunk CMake config evaluates X11/XCB include discovery for Vulkan;
- the HostLibs CMake file also performs an OpenGL package check while configuring the thunk set, even when the requested build target is Vulkan;
- `libcap-dev` is retained as a FEX runtime/build dependency from the successful hosted recipe until a clean pruning run proves it can disappear.

The first focused run is deliberately allowed to fail at configure/build if this delta is too small. Such a failure is a dependency/build owner and should be fixed by adding only the package identified by the first error.

## Focused build targets

### Host side

Configure the exact FEX checkout once with thunks enabled, then build:

```sh
cmake --build fex-src/build --target vulkan-host-64 -- -j"$(nproc)" -v
```

This is the useful cut because `vulkan-host-64` depends on the host FEX runtime and `thunkgen`; it avoids the default whole-project build and avoids the 32-bit Vulkan thunk.

Expected relevant outputs:

```text
fex-src/build/Bin/FEX
fex-src/build/Bin/thunkgen
fex-src/build/HostLibs_64/libvulkan-host.so
```

### Guest side

Configure `ThunkLibs/GuestLibs` independently for 64-bit x86 and build only:

```sh
cmake --build guest-build --target vulkan-guest -- -j"$(nproc)" -v
```

The guest CMake uses:

```text
BITNESS=64
Data/CMake/toolchain_x86_64.cmake
GENERATOR_EXE=<exact build>/Bin/thunkgen
X86_DEV_ROOTFS=/
```

`X86_DEV_ROOTFS=/` intentionally lets thunk generation see the runner's architecture-independent development headers while the GNU x86-64 cross compiler supplies the guest target runtime. It also avoids the private `/mnt/AutoNFS/rootfs` convention entirely.

Expected output:

```text
guest-build/libvulkan-guest.so
SONAME: libvulkan.so.1
```

## Runtime rootfs strategy

Build sysroot and runtime rootfs are separate resources.

For execution:

```sh
docker pull --platform=linux/amd64 ubuntu:24.04
cid="$(docker create --platform=linux/amd64 ubuntu:24.04 /bin/true)"
docker export "$cid" | tar -C "$ROOTFS_DIR" -xf -
```

This creates a normal x86-64 Ubuntu userspace without running `/bin/sh`, `apt`, or any other amd64 process under Docker/QEMU.

The focused experiment then copies:

```text
libvulkan-guest.so -> $ROOTFS_DIR/usr/lib/x86_64-linux-gnu/libvulkan.so.1
```

directly into the runtime filesystem. This intentionally removes FEX ThunksDB overlay discovery from the first Finding A discriminator. The x86 program's `dlopen("libvulkan.so.1")` therefore loads the generated FEX guest thunk by the same SONAME it advertises.

## Software Vulkan strategy

The host side uses Mesa Lavapipe selected explicitly from the runner's ICD directory:

```sh
LVP_ICD="$(find /usr/share/vulkan/icd.d -maxdepth 1 -type f -name 'lvp_icd*.json' | head -1)"
VK_DRIVER_FILES="$LVP_ICD" ...
```

The workflow first runs native ARM64 `vulkaninfo --summary` and the native ARM64 callback reproducer. FEX execution begins only after that native control succeeds.

Finding A therefore does not depend on a physical GPU, Venus, virtio-gpu, Apple silicon, or a display server.

## Runtime phase discriminators

The focused workflow runs these in order with the same rootfs and explicit 64-bit host thunk:

```text
1. static x86-64 binary under FEX
2. dynamically linked x86-64 binary under FEX
3. x86-64 dlopen("libvulkan.so.1") under FEX
4. x86-64 Vulkan debug-report callback through direct symbol lookup
5. x86-64 Vulkan debug-report callback through vkGetInstanceProcAddr
6. same GIPA callback case after one diagnostic host-thunk routing edit
```

The callback reproducer calls `_exit()` after the discriminator. That keeps Finding B's guest-thunk unload/teardown behavior out of the Finding A result.

## Diagnostic A/B

Baseline source remains the exact reviewed Git commit.

After baseline receipts are captured, the workflow makes one dirty-worktree diagnostic edit in `ThunkLibs/libvulkan/Host.cpp`: add `vkCreateDebugReportCallbackEXT` to `LookupCustomVulkanFunction()` so the already-existing custom callback-sanitizing implementation can be selected by dynamic lookup.

The workflow records:

```text
git rev-parse HEAD = 71afe476751deac24adabd1adb575fd2337b6e0a
git diff -- ThunkLibs/libvulkan/Host.cpp = finding-a-diagnostic.diff
```

and rebuilds only:

```text
vulkan-host-64
```

The edit is diagnostic evidence. It is not represented as FEX contribution code.

## First-owner classification

The workflow classifies the first incomplete checkpoint in this order:

| Checkpoint | First owner if it fails |
| --- | --- |
| Hosted runner starts | GitHub Actions availability |
| focused apt delta | CI dependency set |
| native Lavapipe callback control | runner Mesa/Vulkan |
| exact FEX configure | FEX build dependency |
| `vulkan-host-64` | FEX host build/thunkgen |
| `vulkan-guest` | guest cross build/sysroot |
| static x86 smoke | FEX runtime/rootfs |
| dynamic x86 plain | x86 dynamic rootfs |
| Vulkan `dlopen` | guest Vulkan thunk staging/loading |
| direct callback | Vulkan direct thunk path |
| GIPA baseline dies, candidate succeeds | Finding A dynamic callback routing |
| all phase controls succeed, baseline and candidate both die | FEX Vulkan callback runtime; inspect product logs |

This prevents a setup failure from being reported as product behavior.

## Artifact plan

Every run uploads a receipt bundle even on failure. The bundle includes:

- requested and actual FEX SHA;
- disposable CI branch SHA;
- pinned Fieldwork probe SHA;
- recursive submodule SHAs;
- runner CPU/kernel/OS/RAM/disk receipt;
- apt update/install logs and complete `dpkg-query -W` inventory;
- Lavapipe ICD path and JSON;
- native `vulkaninfo` output;
- native callback output;
- host CMake configure log;
- verbose `vulkan-host-64` build log;
- guest CMake configure log;
- verbose `vulkan-guest` build log;
- `file`/`readelf` identity for FEX and both thunks;
- Docker version, OCI image inspect JSON, rootfs loader/OS/size receipt;
- each x86 phase stdout/stderr/exit code;
- baseline callback matrix;
- exact dirty diagnostic diff;
- candidate rebuild log;
- candidate stdout/stderr/exit;
- generated first-owner classification.

## Current focused run

Agent C launched the first focused owned-fork workflow as:

```text
repository: teamleaderleo/FEX
branch: ci/agent-c-finding-a-arm64-20260814
workflow: .github/workflows/agent-c-finding-a-arm64.yml
workflow commit: df00c0e017e0547f59cd57e9e44ae854971bd4a8
Actions run: 31729297543
job: 94545383909
source under test: 71afe476751deac24adabd1adb575fd2337b6e0a
```

At note creation time the job was in progress. Update this section with the first failing owner or complete A/B matrix when the run finishes.

## Smallest remaining human-only test

If hosted ARM64 reaches the callback discriminator cleanly, the hosted lane covers the CPU emulator, x86 rootfs, generated Vulkan guest thunk, ARM64 host thunk, and software Vulkan callback path.

The only hardware-specific confirmation then needed for the Apple path is a final current-head run on the Apple M5/Venus environment:

```text
same FEX source/candidate identity
same small x86 callback reproducer
Venus selected instead of Lavapipe
plus optional vulkaninfo --summary integration control
```

The prior fieldwork already proved that a pinned FEX Vulkan guest thunk can enumerate `Virtio-GPU Venus (Apple M5)` and exit successfully. The final human run would refresh that hardware receipt against the current reviewed head/candidate.

## ELI5

FEX has a little x86 Vulkan library inside the fake x86 computer and a matching ARM Vulkan library on the real ARM machine. Those two libraries pass Vulkan calls across the CPU-language boundary.

GitHub now gives us a real ARM computer for CI, so we can build both halves there. For the fake x86 Linux installation, we unpack an ordinary amd64 Ubuntu container image into a folder. For the GPU, we use Mesa's CPU Vulkan driver, Lavapipe, so the experiment needs no actual GPU.

Finding A is about a Vulkan callback. The x86 program says, roughly, "when Vulkan has a debug message, call this x86 function." FEX already contains special ARM-side code that knows it must keep that x86 function pointer away from native ARM Vulkan. The dynamic function lookup path appears to skip that special code. Native ARM code then receives an x86 function address and the ARM CPU hits illegal instructions.

The hosted test walks to that exact doorway in small steps: x86 program, x86 dynamic loader, Vulkan library load, direct Vulkan callback path, then dynamic callback lookup. After each step works, we change only the host thunk's dynamic lookup routing and run the same callback again.

So the hosted CI box can do nearly the whole experiment. Apple M5/Venus is the final hardware-flavored confirmation, not the place where we need to discover basic build, rootfs, or callback failures.
