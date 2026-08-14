# CUDA resident-bridge runtime scope correction — 2026-08-14

## Correction

The `local_unpacker=139 / resident_unpacker=139` matrix from owned-fork run [`31787029666`](https://redirect.github.com/teamleaderleo/FEX/actions/runs/31787029666) must **not** be treated as a valid resident-sidecar falsifier.

The run did reach the deferred callback boundary, but the two runtime arms were not isolated from each other's FEX/rootfs state.

## Concrete evidence

The workflow intended to run:

- a local-unpacker wrapper from `rootfs-local`;
- then a resident-sidecar wrapper from `rootfs-resident`.

However, the supposed resident arm's own `/proc/self/maps`-derived marker reports generation 1 as:

```text
GEN1 wrapper=/home/runner/work/FEX/FEX/rootfs-local/usr/lib/x86_64-linux-gnu/libcuda.so.1 ...
```

The local arm reports the same pathname.

The supposed resident arm therefore did **not** prove execution using `rootfs-resident/libcuda.so.1`. Its runtime callback address/behavior is consequently not evidence about the derived resident CUDA unpacker.

The sidecar build portion of the same lane remains useful:

- ordinary CUDA wrapper remained non-NODELETE;
- wrapper carried a `DT_NEEDED` edge to `libfex-cuda-bridge.so`;
- the bridge carried `DF_1_NODELETE`;
- normal generated CUDA signature set and derived bridge set matched at `364 / 364` unique signatures.

Only the runtime comparison is contaminated.

## Replacement discriminator

The replacement workflow now executes the local and resident arms as separate GitHub Actions matrix jobs on **different fresh hosted runners**.

Each job independently:

1. checks exact product provenance;
2. builds only its own callback-unpacker variant;
3. creates only its own guest rootfs;
4. runs a fresh FEX/FEXServer environment;
5. requires the guest's `/proc/self/maps` marker to equal that job's expected rootfs pathname before accepting any callback result.

Replacement run:

[`31787821035`](https://redirect.github.com/teamleaderleo/FEX/actions/runs/31787821035)

That run is the first eligible CUDA local-vs-resident deferred-callback A/B after the contamination was identified.

## Impact on the resident-bridge proposal

The CUDA section of `resident-bridge-proposal-20260814.md` currently describes run `31787029666` as an implementation falsifier and proposes tracing the retained trampoline's `GuestUnpacker` as the immediate next step.

That conclusion is premature because the purported resident arm never loaded the resident wrapper rootfs.

Until the isolated replacement matrix completes, CUDA resident-sidecar runtime status should be classified as:

> build/ELF/signature derivation proven; deferred moved-reload runtime A/B pending a correctly isolated resident arm.

This correction does not weaken the separate pristine CUDA callback defect, the generated `callback_member` repair, or the DRM/Vulkan resident-bridge runtime evidence.