# Wayland 32-bit resident `wl_array` compatibility — 2026-08-14

## Source and goal

Clean source under test:

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

Diagnostic branch:

`diagnostic/wayland32-resident-array-compat-20260814`

The compatibility question is narrow: keep the existing 32-bit host-side `CallGuestPtrWithWaylandArray` packer and prove it interoperates with the already-resident guest listener unpacker in `libfex-wayland-client-bridge.so`.

This gate does not introduce another resident guest executable family.

## First run — negative result before 32-bit source compilation

Workflow:

`.github/workflows/wayland32-resident-array-compat.yml`

Carrier head:

`3bfa8d5cc275db94558579c65f1d8433be72755e`

Run:

`31799488314`

Job:

`94763840019` (`wayland32-array`)

Result:

`failure`

Artifact:

- name: `wayland32-resident-array-compat-31799488314`
- ID: `9218713033`
- SHA-256: `ec3afdb1a0356a1f37fd8e5c31fdb8a57df8353633cb81475a966d46794211ba`

Exact clean-source provenance passed before the runtime-only diagnostic hook was added.

The job then stopped during the main host CMake configure, before `wayland-client-host-32`, the 32-bit guest wrapper, or the resident companion compiled. The artifact contains `cmake-host.log`, `pre-patch-product-source-diff.txt`, and `runtime-only.diff`; there is no host build log or guest CMake/build log.

Exact configure failure:

```text
CMake Error at /usr/local/share/cmake-3.31/Modules/FindPackageHandleStandardArgs.cmake:233 (message):
  Could NOT find OpenGL (missing: OPENGL_opengl_LIBRARY OPENGL_glx_LIBRARY
  OPENGL_INCLUDE_DIR)
Call Stack (most recent call first):
  /usr/local/share/cmake-3.31/Modules/FindPackageHandleStandardArgs.cmake:603 (_FPHSA_FAILURE_MESSAGE)
  /usr/local/share/cmake-3.31/Modules/FindOpenGL.cmake:579 (FIND_PACKAGE_HANDLE_STANDARD_ARGS)
  ThunkLibs/HostLibs/CMakeLists.txt:168 (find_package)

-- Configuring incomplete, errors occurred!
```

## First-run classification

This is a diagnostic workflow dependency failure. The workflow installed `libwayland-dev` but omitted `libgl-dev`; the top-level FEX host configure traverses the thunk host CMake and requires OpenGL even when the requested build target is the 32-bit Wayland host thunk.

No conclusion about 32-bit Wayland source compatibility, ELF32 packaging, host `wl_array` relocation, resident unpacker execution, or callback correctness follows from this run.

## Second run — production ELF32 pair green, fake-native declaration mismatch

Run:

`31799902805`

Carrier head:

`a9caf9d44843a196c24dc2e647280387168f9147`

Artifact:

- ID: `9218945515`
- SHA-256: `6ebbe3b57a06bc64ba52615ff882421d0736e7a5f79b56020d751bbc50001d0b`

The real 32-bit product build and ELF checks completed before the diagnostic fake-native compile failed.

Observed production pair:

- `libwayland-client-guest.so`: ELF32, Intel 80386, BuildID `8a503d6eb142353337c8c81a2af039b805e30e84`;
- `libfex-wayland-client-bridge.so`: ELF32, Intel 80386;
- wrapper has `NEEDED libfex-wayland-client-bridge.so` and `$ORIGIN` and no `NODELETE`;
- companion has `NODELETE`;
- marker: `WAYLAND32_BUILD_ELF_OK`.

The stop was in diagnostic C code: the fake declared `wl_proxy_get_listener` as `void *`, while the Wayland declaration is `const void *`. The harness declaration was corrected without changing product source.

## Third run — fake native green, container image unavailable

Run:

`31800575153`

Carrier head:

`44f97b2ca0e14f9463498fd37977ec5f529058a6`

Artifact:

- ID: `9219208665`
- SHA-256: `7fc8f0e6df79f62b7c735ba00cb9cf4ef74383fce03729a5ba9e87940d7b052f`

The corrected fake-native Wayland target compiled. The job then stopped while trying to obtain an Ubuntu `24.04` `linux/386` container image; that manifest is unavailable. This was another diagnostic packaging boundary after the real product pair had already built.

## Minimal-rootfs run 2 — actual FEX execution reaches 32-bit `dlopen`, then SIGILL

A separate workflow replaced the unavailable container image with a small i386 rootfs assembled from the installed cross toolchain:

`.github/workflows/wayland32-resident-array-minrootfs.yml`

Run:

`31804656203`

Carrier head:

`47027f9958e031392285e00f45ca1dc932fe68ea`

Artifact:

- ID: `9220781210`
- SHA-256: `b3c431a8fce04aff19ddc620a6c001af44ef27cb5535ec91b1daf48e361afeeb`

This run again built the real 32-bit wrapper and resident companion. Runtime-only instrumentation exposed the actual resident array unpacker with `FEXWaylandDiagArrayUnpacker()`.

The companion exported:

```text
00001210 T FEXWaylandAllocateResidentListener
000011f0 T FEXWaylandDiagArrayUnpacker
00001af0 W CallbackUnpack<void(void*, wl_proxy*, wl_array*)>::Unpack
```

The assembled guest rootfs contained the i386 loader, libc, libm, libstdc++, and libgcc in the multilib search paths. The guest probe was ELF32 with interpreter `/lib/ld-linux.so.2`.

Actual execution reached the probe and established the intended 32-bit layout:

```text
WAYLAND_ARRAY32_LAYOUT sizeof_size_t=4 sizeof_ptr=4 sizeof_wl_array=12
```

It then terminated with SIGILL during `dlopen("libwayland-client.so.0")`, before unpacker lookup, listener registration, or the host `wl_array` callback path:

```text
Illegal instruction
rc=132
WAYLAND_ARRAY32_LAYOUT sizeof_size_t=4 sizeof_ptr=4 sizeof_wl_array=12
timeout: the monitored command dumped core
```

This moves the open question earlier than `CallGuestPtrWithWaylandArray`: the 32-bit guest thunk library must first survive its load constructor.

## Load-time baseline/candidate A/B

The Wayland guest library ends with `LOAD_LIB_INIT(libwayland-client, OnInit)`. The common guest helper implements that constructor by invoking the FEX `loadlib` thunk and then `OnInit`; x86 guest thunk stubs begin with FEX's `0F 3F` magic instruction followed by the thunk hash.

To classify the SIGILL, a dedicated A/B workflow runs the same minimal 32-bit `dlopen` probe against:

- baseline `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`;
- candidate `1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`.

Workflow:

`.github/workflows/wayland32-loadlib-ab.yml`

The probe installs a SIGILL handler that records EIP, 24 instruction bytes, and the containing `/proc/self/maps` entry.

### A/B run 1 — inconclusive rootfs dependency omission

Run:

`31805294548`

Both baseline and candidate built FEX, the 32-bit Wayland host thunk, the guest wrapper, and the arm64 fake native target. Both probes started and then failed before Wayland thunk initialization because the A/B rootfs omitted `libm.so.6`:

```text
LOADLIB32_BEGIN ptr=4
LOADLIB32_AFTER handle=(nil) err=libm.so.6: cannot open shared object file: No such file or directory
```

Candidate artifact:

- ID: `9221037932`
- SHA-256: `8ab1845f68e348ca62be9f2c023f87d7a2ab3d1ae4caabb94ffcb5ce368be7e9`

Baseline artifact:

- ID: `9221039647`
- SHA-256: `00c044d64b555899b8289aaa75130147ffbdee23d79adae2ab666c0927bc472b`

This result is packaging-only and gives no baseline/candidate runtime distinction.

### A/B run 2 — active

Diagnostic-only workflow commit:

`4af45d928a80865756a3a2f2ec74c8fd6c6bf1b4`

Run:

`31816834661`

The workflow now copies `libm.so.6` and records direct `NEEDED` entries for the wrapper, libstdc++, and libgcc. Product source is unchanged.

At launch time this run was still building both exact source variants. The final classification must be appended after the two runtime receipts are available.

## Product-source isolation

The clean integration branch remains:

`integration/per-library-resident-bridges-drm-f3ab-20260814`

at:

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

The Wayland32 diagnostic head `4af45d928a80865756a3a2f2ec74c8fd6c6bf1b4` is seven commits ahead of that source tip, with changes limited to these workflow files:

- `.github/workflows/wayland32-loadlib-ab.yml`
- `.github/workflows/wayland32-resident-array-compat.yml`
- `.github/workflows/wayland32-resident-array-minrootfs.yml`

No product file has been changed by the Wayland32 runtime investigation.

## Remaining gate

The next receipt must classify the 32-bit load constructor first. If baseline and candidate exhibit the same load-time trap, the resident split is not the differentiator and the real `"a"` callback execution remains blocked by an earlier baseline 32-bit runtime condition. If candidate alone traps, investigate the resident companion/load interaction. If both load, rerun the complete `"a"` listener path immediately.

The complete callback success criteria remain:

1. resident `CallbackUnpack<void(void*, wl_proxy*, wl_array*)>::Unpack` maps inside `libfex-wayland-client-bridge.so`;
2. fake native interface reports one `"a"` event and stores the generated host trampoline;
3. host `wl_array {size=7, alloc=9, data=NULL}` crosses the existing 32-bit host packer;
4. guest callback receives data `0x12345678`, `size=7`, `alloc=9`, and `data=NULL`;
5. roundtrip returns `17`, callback count is one, and callback validation remains clean;
6. final marker is `WAYLAND32_RESIDENT_ARRAY_COMPAT_OK` with process exit 0.
