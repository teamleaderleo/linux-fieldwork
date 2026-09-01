# Cloud Hypervisor selectable live-upgrade source versions

## TL;DR

The original Fieldwork lane has been overtaken by current upstream source. Cloud Hypervisor commit `d2282a7ca4b5087d5d0f3b655ec765cde5b00bc2` added a dedicated MSHV previous-release asset pinned to v50.2, taught the x86 integration runner to require that asset for MSHV, and taught the Rust test helper to select it when the `mshv` feature is enabled. Current `main` therefore addresses the concrete MSHV compatibility failure that motivated canonical issue 8616 without restoring a generic `MIGRATABLE_VERSION` override.

The useful disposition is now: retain the historical contract map, record upstream's narrower backend-specific design, and stop the generic source-candidate path unless a concrete need for arbitrary previous-release selection appears.

Tracking issue: [linux-fieldwork #497](https://github.com/teamleaderleo/linux-fieldwork/issues/497)  
Canonical report: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8616

## Explain like I'm five

The old test switch said “pick any older Cloud Hypervisor version.” The current code takes a simpler route: KVM keeps its normal v39.0 test binary, while MSHV gets its own known-compatible v50.2 binary.

```text
current x86 live-upgrade source selection

KVM  -> cloud-hypervisor-static      -> v39.0
MSHV -> cloud-hypervisor-static-mshv -> v50.2
```

That directly fixes the reported MSHV problem even though the old arbitrary-version knob is still gone.

## Why care

This changes the engineering decision. A new dynamic downloader would add version parsing, release lookup, and verification policy to solve a compatibility problem current upstream has already handled with a static, checksummed backend-specific asset.

A generic selector could still be useful for migration-matrix research, but it now needs its own demonstrated use case instead of inheriting issue 8616 as justification.

## Current state

- State: `SUPERSEDED BY UPSTREAM DESIGN / RETAINED NEGATIVE RESULT`
- Current upstream head inspected: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
- Superseding commit: `d2282a7ca4b5087d5d0f3b655ec765cde5b00bc2`
- Candidate source commit: none
- Latest distinguishing result: MSHV now selects a dedicated v50.2 previous-release asset in current source
- Cleanup state: no runtime state
- Next safe action: stop generic candidate work; reopen only for a concrete arbitrary-version requirement or a runtime counterexample against the v50.2 MSHV path
- External-contact state: `false; none occurred`

## Intent and history

The generic override was introduced deliberately:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/1ca6c159ef4cca6ffa94f24daa75e7971e8dbd16

It was preserved through later integration-test refactors:

- https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/c118606d645f210d3eded192c6eb73d88c8696d6
- https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/5909ce85edfc35ae61bd090d778bed9b718bf20f
- https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/339d0a84f98de7d36a2ed5345ce173e4800507df

Workload acquisition later moved to the host-side asset manifest:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/4442d3b09bbf521298132bf640d0e0871a59f65c

The 2026-08-10 upstream correction then chose a narrower policy:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/d2282a7ca4b5087d5d0f3b655ec765cde5b00bc2

Its commit message states that MSHV can only upgrade from v50.2 because of breaking MSHV ioctl changes.

## Current source boundary

Project: `cloud-hypervisor/cloud-hypervisor`

Current head inspected:
`a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`

Relevant current paths:

- `scripts/test_assets.yaml`
- `scripts/run_integration_tests_x86_64.sh`
- `cloud-hypervisor/tests/common/utils.rs`

Current source contains:

1. the existing x86 `cloud-hypervisor-static` v39.0 asset;
2. the existing AArch64 v39.0 asset;
3. a separate x86 `cloud-hypervisor-static-mshv` asset pinned to v50.2 with its own SHA-1;
4. x86 runner selection of the MSHV asset when `hypervisor=mshv`;
5. Rust test-helper selection of the MSHV path when built with the `mshv` feature.

`MIGRATABLE_VERSION` remains absent from current code search.

## Distinguishing result

The original Fieldwork question was whether loss of generic version selection leaves MSHV stuck on an incompatible v39.0 source binary.

Current upstream source answers that concrete question:

```text
old broken boundary:
MSHV -> generic previous-release asset -> v39.0

current boundary:
MSHV -> dedicated previous-release asset -> v50.2
```

That changes the old candidate from a repair to an optional broader feature.

## Adjacent contexts checked

### KVM

KVM continues to use the normal x86 v39.0 asset. The MSHV correction does not alter that default.

### AArch64

AArch64 continues to use its own v39.0 static binary. The superseding commit changes only x86 MSHV selection.

### Asset verification

The new MSHV asset is static manifest data with a pinned SHA-1, preserving the existing verification model. The unresolved dynamic-release digest design from the old candidate disappears from the immediate repair path.

### Generic migration-matrix testing

Current source still has no arbitrary previous-release selector. That is now a separate capability question. Reopen only with a named test or supported workflow that needs more than the fixed backend-specific baseline.

## Evidence boundary

- Source selection and asset identity are demonstrated from current upstream code.
- Linux Fieldwork did not execute an MSHV live-upgrade run against v50.2 in this pass.
- Canonical issue 8616 is still open at the time of this source inspection.
- This record does not claim that every MSHV migration combination works; it records that the specific v39.0 selection problem has a current upstream source correction.

## Disposition

Stop the generic host-side dynamic-selector candidate.

Reopen this lane if any of these appears:

1. the dedicated v50.2 path fails on a real MSHV integration run;
2. a supported workflow requires selecting multiple historical source versions;
3. upstream policy explicitly asks to restore arbitrary version selection;
4. the static backend-specific asset model becomes insufficient for migration compatibility coverage.

Otherwise retain this as a negative result: an earlier plausible repair became unnecessary after upstream selected a smaller backend-specific solution.

## Authority

No upstream issue, pull request, comment, review, or other interaction was created or modified by this Fieldwork pass.