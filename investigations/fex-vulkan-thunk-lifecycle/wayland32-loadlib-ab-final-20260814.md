# Wayland32 load-time baseline/candidate A/B — final receipt — 2026-08-14

## Question

Does the resident per-library split at clean candidate source `1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a` introduce the 32-bit SIGILL observed while loading the Wayland guest thunk, or is the stop already present at baseline `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`?

## Workflow

Diagnostic branch:

`diagnostic/wayland32-resident-array-compat-20260814`

Diagnostic-only carrier commit:

`4af45d928a80865756a3a2f2ec74c8fd6c6bf1b4`

Workflow:

`.github/workflows/wayland32-loadlib-ab.yml`

Run:

`31816834661`

The two jobs independently build FEX/FEXServer, `wayland-client-host-32`, the corresponding ELF32 guest Wayland wrapper, a minimal native arm64 Wayland target, and the same i386 `dlopen` probe. The i386 rootfs contains the cross-toolchain loader, libc, libm, libstdc++, and libgcc in the multilib search paths.

The probe installs a guest SIGILL handler, prints `LOADLIB32_BEGIN ptr=4`, and performs `dlopen("libwayland-client.so.0", RTLD_NOW | RTLD_LOCAL)`.

## Candidate

Source:

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

Job:

`94820432054`

All setup/build/rootfs/probe steps passed. Runtime then exited with signal-derived code 132:

```text
LOADLIB32_BEGIN ptr=4
timeout: the monitored command dumped core
```

The shell recorded `Illegal instruction` for the FEX invocation. The guest-installed SIGILL handler did not print `SIGILL_CAUGHT`, so this receipt does not provide a guest EIP or instruction-byte capture.

Artifact:

- ID: `9225473876`
- SHA-256: `b50290597ab25397ca40df10562a4941a3b164b5320f4c3a355931725d6d7f15`

## Baseline

Source:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

Job:

`94820432046`

The baseline also passed all setup/build/rootfs/probe steps. Its wrapper is a valid ELF32 Intel 80386 shared object, BuildID `548ca29e442178b998daf20ca4bef0609d28c460`.

Runtime then produced the same result:

```text
LOADLIB32_BEGIN ptr=4
timeout: the monitored command dumped core
```

The shell again recorded `Illegal instruction`, exit code 132. The baseline guest SIGILL handler also did not print `SIGILL_CAUGHT`.

Artifact:

- ID: `9225491018`
- SHA-256: `691fcfd3c133e0b93668ec9ede555eb9302688cdd93c27539683da1e8cc798cf`

The baseline wrapper has no resident companion and directly needs only libstdc++, libgcc, and libc; the candidate additionally needs the per-library resident companion. Both converge on the same load-time failure before the Wayland listener path executes.

## Classification

The resident per-library split is not the differentiator for this 32-bit load-time stop. Exact pre-tranche baseline and exact clean candidate both reach the same probe marker and terminate with SIGILL during Wayland `dlopen` after the i386 runtime dependencies are complete.

This closes the candidate-regression question for the observed load failure. There is no evidence from this A/B that `libfex-wayland-client-bridge.so`, its NODELETE policy, or the wrapper's NEEDED edge introduced the SIGILL.

The guest SIGILL handler not running is also relevant: the receipt localizes the failure to FEX execution during thunk-library initialization, but it does not establish the exact guest instruction address. A deeper FEX thunk-dispatch diagnostic can investigate that separately if useful.

## Effect on the resident bridge source stack

No product change is justified by this A/B result.

The clean source branch remains:

`integration/per-library-resident-bridges-drm-f3ab-20260814`

at:

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

The consolidated clean-source build/ELF matrix remains green for all five 64-bit wrapper/companion pairs plus the ELF32 Wayland wrapper/companion pair. Wayland32 callback execution itself remains unproven because execution stops earlier at a baseline-equivalent 32-bit thunk load condition.

## Wayland32 gate status

Closed as a compatibility build/ELF proof with a separately classified runtime blocker:

- ELF32 wrapper/companion build: green;
- wrapper/companion NODELETE boundary: green;
- 32-bit `wl_array` layout: observed as `size_t=4`, pointer=4, `wl_array=12`;
- resident array unpacker present in the candidate companion: green;
- real `"a"` callback execution through `CallGuestPtrWithWaylandArray`: not reached;
- reason callback is not reached: baseline and candidate both SIGILL during Wayland guest thunk `dlopen` in the minimal 32-bit runtime setup.

Do not report `WAYLAND32_RESIDENT_ARRAY_COMPAT_OK`; that runtime marker was never observed.
