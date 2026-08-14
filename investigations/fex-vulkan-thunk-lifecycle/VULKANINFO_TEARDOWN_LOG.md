# Real x86 `vulkaninfo` teardown runtime log

Date: 2026-08-14

## Goal

Re-run the original application-level symptom with the real Ubuntu amd64 `vulkaninfo` binary, real generated FEX Vulkan guest/host thunks, llvmpipe, the already-established Vulkan callback/proc-routing diagnostic, and then the integrated thunk-lifetime candidate.

This is kept separate from [`APPLICATION_TEARDOWN_LOG.md`](./APPLICATION_TEARDOWN_LOG.md) because the minimal Vulkan application already established that create/enumerate/destroy/`dlclose` alone exits normally on stock FEX.

## Experimental isolation

The intended A/B holds generated Vulkan thunk binaries fixed between phases:

1. build FEX plus generated Vulkan thunks from the owned callback-routing branch;
2. retain stock `FEX`/`FEXServer` binaries;
3. assemble an amd64 Ubuntu guest rootfs containing the real `vulkan-tools` package and its user-space dependency closure;
4. replace only the rootfs Vulkan loader DSO with the generated FEX guest thunk;
5. run stock `vulkaninfo` controls;
6. apply the integrated lifetime changes and rebuild **only** `FEX`/`FEXServer`;
7. verify the thunk DSO hashes are unchanged;
8. run the identical candidate controls.

The callback/proc-routing diagnostic is present in both phases so the earlier known GIPA callback-routing SIGILL cannot mask the teardown comparison.

## Matrix

For each stock/candidate phase:

- `vulkaninfo --summary`, normal unload;
- `vulkaninfo --summary`, Vulkan guest thunk preloaded/pinned;
- `vulkaninfo --summary`, unrelated guest DSO preload;
- full `vulkaninfo`, normal unload;
- full `vulkaninfo`, Vulkan guest thunk preloaded/pinned;
- full `vulkaninfo`, unrelated guest DSO preload.

No display server is exposed; `DISPLAY`, `WAYLAND_DISPLAY`, and `XDG_RUNTIME_DIR` are cleared. The Vulkan ICD is host llvmpipe.

## Owned-fork branch/workflow

```text
teamleaderleo/FEX
branch: ci/vulkaninfo-teardown-20260814
workflow: .github/workflows/vulkaninfo-real-teardown-arm64.yml
```

The routed Vulkan source branch used for the stock phase is:

```text
fix/vulkan-callback-proc-routing
head observed by runs: c011366706eaf65a00380003989b3a10811212b6
base product snapshot: 71afe476751deac24adabd1adb575fd2337b6e0a
```

The routed branch is exactly two commits ahead of `71afe...`; the source delta is confined to:

```text
ThunkLibs/libvulkan/Guest.cpp
ThunkLibs/libvulkan/Host.cpp
```

so the stock phase carries the known Vulkan callback/proc-routing diagnostic without lifetime changes.

## Run 1 — harness failure before product build

Actions run:

```text
31777681344
carrier: 3cc4df50e37b9563d8bdaeaa9d7278f968e00390
```

Result: **non-evidentiary harness failure**.

The source checkout used `fetch-depth: 1`, while the provenance step attempted:

```text
git -C src diff 71afe476751deac24adabd1adb575fd2337b6e0a..HEAD -- ThunkLibs/libvulkan
```

The two routing commits' FEX-2608 base was absent from the shallow local checkout, producing:

```text
fatal: Invalid revision range 71afe476751deac24adabd1adb575fd2337b6e0a..HEAD
```

No FEX build, guest package assembly, `vulkaninfo` execution, or product comparison occurred.

Artifact retained by the failed run:

```text
id:      9210525502
sha256:  974f412763e5327aa567060912538f718e712c8985c6a575dd2640ab69b057a0
```

### Repair

The routed FEX checkout was changed to `fetch-depth: 3`, retaining the two routing commits plus their `71afe...` base so the local provenance diff is valid.

Repair commit:

```text
aaa031340e9c2e6bd9df3cfe8cd482549cd7b9fd
```

The runtime variables were not changed by this repair.

## Run 2 — package receipt matcher failure after successful FEX/thunk build

Actions run:

```text
31777991657
carrier: aaa031340e9c2e6bd9df3cfe8cd482549cd7b9fd
```

Result: **non-evidentiary harness failure** after substantially more setup succeeded.

Completed successfully before the failure:

- routed FEX provenance checkout/diff;
- llvmpipe ICD resolution;
- stock FEX and adjacent FEXServer build;
- generated Vulkan host thunk build;
- generated x86-64 Vulkan guest thunk build;
- isolated amd64 APT repository update;
- amd64 dependency resolution/download for real `vulkan-tools`.

The isolated amd64 APT state downloaded 19 packages. Its retained package table includes:

```text
vulkan-tools    1.3.275.0+dfsg1-1    amd64
```

The failure was a receipt assertion, not APT/package resolution. The workflow wrote tab-separated package rows and then used:

```text
grep -E '^vulkan-tools\t' "$R/amd64-packages.txt"
```

GNU `grep -E` does not interpret `\t` as a literal tab in this expression, so the command returned 1 even though the `vulkan-tools` row was present. The step stopped before rootfs extraction and before any `vulkaninfo` execution.

Therefore run 2 has **no product exit code**.

Artifact:

```text
id:      9210704577
sha256:  a3c7016a207c922044c64dad175ea73e18b454f2edfe863cd43fc903d8f0c8dc
```

The artifact retains the successful stock build/configuration receipts, routed source delta, thunk hashes, amd64 APT logs, and package table.

### Repair

The package assertion now uses an explicit tab field separator:

```text
awk -F '\t' '$1 == "vulkan-tools" { print }' "$R/amd64-packages.txt" | tee "$R/vulkan-tools-package.txt"
test -s "$R/vulkan-tools-package.txt"
```

Repair commit:

```text
4ce03d842f345045871af1663b8a48316de7be79
```

Again, the FEX source, generated thunk inputs, rootfs recipe, and runtime matrix were not changed by this harness repair.

## Run 3 — complete real `vulkaninfo` stock/candidate matrix

Actions run:

```text
31778563827
job:    94699137822
carrier: 4ce03d842f345045871af1663b8a48316de7be79
fex_source: c011366706eaf65a00380003989b3a10811212b6
lifetime helper: 96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2
job conclusion: success
```

Artifact:

```text
id:      9210948707
name:    real-vulkaninfo-teardown-31778563827
sha256:  1a43ea6beb4c4cab177c5d43bad4ae88a7b8b7e2234dd01077e5744f9e336f25
```

The real guest binary receipt identifies:

```text
/usr/bin/vulkaninfo: ELF 64-bit LSB pie executable, x86-64
interpreter /lib64/ld-linux-x86-64.so.2
BuildID 3417733...
stripped
```

The generated Vulkan guest/host thunk hashes are unchanged between the stock and candidate phases; the retained `thunk-sha256.diff` is empty. Thus only the FEX/FEXServer lifetime behavior changed for the A/B phase.

### Exit matrix

Every application case completed with exit 0:

```text
stock-summary-normal=0
stock-summary-pin=0
stock-summary-bogus=0
stock-full-normal=0
stock-full-pin=0
stock-full-bogus=0
candidate-summary-normal=0
candidate-summary-pin=0
candidate-summary-bogus=0
candidate-full-normal=0
candidate-full-pin=0
candidate-full-bogus=0
```

Both stock and candidate summary runs enumerate one llvmpipe device. Retained output identifies:

```text
GPU0
apiVersion = 1.4.318
deviceName = llvmpipe (LLVM 20.1.2, 128 bits)
driverName = llvmpipe
driverInfo = Mesa 25.2.8-0ubuntu0.24.04.2 (LLVM 20.1.2)
```

### Candidate retirement activity validates the controls

The candidate was not idle in this matrix. Each case activates 582 dynamic H claims, with seven compatible standby claims observed during registration.

For normal and unrelated-bogus-preload cases, teardown produces 582 retirements and 582 revoked-H installations. For the Vulkan pin cases, those retirement/revocation events are absent because the guest Vulkan thunk remains live through process return.

Conceptually:

```text
normal / bogus:
  582 active H claims
  -> final guest Vulkan ownership disappears
  -> 582 retire/revoke transitions

pin:
  582 active H claims
  -> guest Vulkan thunk remains referenced
  -> 0 retire/revoke transitions before process return
```

That confirms the pin control is exercising the lifetime dimension intended by the original field experiment, even though this hosted application run exits normally in all cases.

### Interpretation

This is a **negative reproduction of the original field exit-139 symptom**, not evidence against the lower-level lifetime bug.

The hosted reconstruction differs from the original environment in loader/package versions, full process image, runner kernel/runtime details, and likely exact teardown ordering. Under this reconstructed environment:

- real Ubuntu amd64 `vulkaninfo` enumerates llvmpipe and exits 0 on routed stock FEX;
- pinning the guest Vulkan thunk does not change the exit code because stock already exits 0;
- unrelated preload also exits 0;
- the lifetime candidate exits 0 in all identical cases;
- candidate diagnostics show that normal/bogus teardown really does retire the dynamic thunk claims while pinning suppresses that retirement.

So the application-level 139 remains environment/order-sensitive. The strongest causal evidence continues to be the forced-different Vulkan PFN reload A/B and exact LinkAddress retirement tests, where stale H -> old guest-invoker state is consumed after the old owner disappears.

The real `vulkaninfo` matrix is still valuable as a compatibility regression: the current integrated candidate survives summary/full enumeration and process teardown with real Vulkan-Tools under llvmpipe across all six controls.

## Evidence rules

A failed package-resolution or rootfs-construction step is a harness result only. A `vulkaninfo` exit status becomes product evidence only after:

- real amd64 `vulkaninfo` is present and identified;
- generated FEX Vulkan guest thunk is installed as guest `libvulkan.so.1`;
- adjacent `FEXServer` is present;
- llvmpipe ICD is resolved;
- stock/candidate thunk hashes are retained for isolation.

Run 3 satisfies those requirements.

## External-contact state

No third-party/upstream issue, pull request, comment, review, reaction, workflow, or repository write was performed. All work remains in repositories owned by `teamleaderleo`.