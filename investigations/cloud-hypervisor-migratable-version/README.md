# Cloud Hypervisor selectable live-upgrade source versions

## TL;DR

`MIGRATABLE_VERSION` was an intentional Cloud Hypervisor test-tool contract and survived several refactors, including the merge of live-migration tests into the normal integration runner. Current `main` has no dynamic version path: `dev_cli.sh`, the integration runners, and `fetch_workloads.py` do not consume the variable, while `test_assets.yaml` fixes both previous-release binaries to v39.0. The next step is a host-side asset-selection candidate that preserves v39.0 as the default and keeps verification explicit.

Tracking issue: [linux-fieldwork #497](https://github.com/teamleaderleo/linux-fieldwork/issues/497)  
Canonical report: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8616

## Explain like I'm five

A live-upgrade test needs two Cloud Hypervisor programs: an old one and the one being tested. The tooling used to let you say "use release v47.0 as the old one." The newer downloader now has a shopping list that simply says "download v39.0," so the caller's requested version never reaches the download step.

```text
old path:
MIGRATABLE_VERSION=v47.0 -> dev_cli -> test runner -> download v47.0

current path:
static asset manifest -> download v39.0 -> test runner
MIGRATABLE_VERSION      ─────────────X
```

## Why care

The original override was added specifically to make MSHV migration tests usable after breaking compatibility changes. Losing the selection knob can make `dev_cli` choose an unsuitable old binary and prevent a meaningful upgrade test even though the repository previously supported a later migration source version.

## Current state

- State: `SCOPING`
- Exact working head: documentation branch only; no owned-fork source candidate yet
- Latest authoritative gate or artifact: source/history map plus retained no-network boundary probe
- First incomplete step: select the smallest host-side dynamic asset boundary
- Cleanup state: no runtime state
- Next safe action: write source-level regression tests for default/override/invalid version selection
- External-contact state: `false; none occurred`

## Intent and precedent

The override was introduced deliberately:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/1ca6c159ef4cca6ffa94f24daa75e7971e8dbd16

That commit added `MIGRATABLE_VERSION` forwarding in `dev_cli.sh` and used it to select the previous-release download, explicitly citing MSHV compatibility and CI.

When live migration was folded into the normal x86 integration runner, the contract was intentionally preserved:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/c118606d645f210d3eded192c6eb73d88c8696d6

The aarch64 runner was separately standardized on the same variable:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/5909ce85edfc35ae61bd090d778bed9b718bf20f

A later `dev_cli.sh` environment-argument deduplication still preserved the integration-specific variable, so it was not an accidental shell detail:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/339d0a84f98de7d36a2ed5345ce173e4800507df

Workload fetching then moved to the host side before entering the container:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/4442d3b09bbf521298132bf640d0e0871a59f65c

## Question

What is the smallest host-side change that restores selectable previous-release binaries for live-upgrade tests while keeping v39.0 as the default and preserving clear asset-integrity behavior?

## Source

- Project: `cloud-hypervisor/cloud-hypervisor`
- Requested revision: current `main` at scout time
- Resolved commit: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Candidate source commit: none yet
- Primary paths:
  - `scripts/dev_cli.sh`
  - `scripts/fetch_workloads.py`
  - `scripts/test_assets.yaml`
  - `scripts/run_integration_tests_x86_64.sh`
  - `scripts/run_integration_tests_aarch64.sh`
- Fieldwork scout: https://github.com/teamleaderleo/fieldwork/pull/772

## Environment

The source-boundary probe is no-network and requires only Python plus a Cloud Hypervisor checkout. End-to-end MSHV validation will require an MSHV-capable runner.

## Baseline behavior

At the resolved current source:

- `dev_cli.sh` contains no `MIGRATABLE_VERSION` reference;
- x86 and aarch64 integration runners contain no version-selection block;
- both runners consume a previous-release binary that is expected to exist in `~/workloads`;
- `test_assets.yaml` points those binaries directly at v39.0 release URLs;
- `fetch_workloads.py` treats the manifest URL and checksum as static asset metadata.

Therefore setting `MIGRATABLE_VERSION` cannot currently select a different previous-release binary through the normal source path.

## Hypothesis or candidate

The repair belongs **before the integration container starts**, because the current architecture pre-fetches workloads on the host.

Candidate boundaries to compare:

1. `fetch_workloads.py --migratable-version vNN.0` substitutes only the previous-release binary URL/name metadata;
2. a dedicated dynamic fetch function handles only the live-upgrade binary outside the static manifest;
3. `dev_cli.sh` performs that one dynamic fetch, then lets the normal manifest path verify all static assets.

The candidate must make checksum behavior explicit. The static v39.0 asset has a known checksum; arbitrary releases cannot inherit that checksum.

## Reproduction

Retained Fieldwork probe:

```sh
python3 programmes/open-source-ecosystems/scouts/foundational-systems/artifacts/cloud-hypervisor-migratable-version-boundary.py /path/to/cloud-hypervisor
```

It checks current source for a dynamic version consumer and identifies whether the previous-release assets remain hard-pinned to v39.0.

The expected current-source classification is:

```text
dynamic_version_path_present=False
manifest_hard_pinned_v39=True
result=REGRESSION_SHAPE_PRESENT
```

The probe intentionally exits non-zero for that source shape so a candidate can use it as a regression check.

## Results

Source and history establish a continuous intended contract from the original override through the live-migration test consolidation. Current source has removed every consumer while retaining the fixed v39.0 asset entries.

No MSHV runtime claim has been executed yet.

## Interpretation

**Demonstrated source behavior:** the current normal tooling has no path from `MIGRATABLE_VERSION` to previous-binary selection.

**Intent evidence:** multiple accepted commits explicitly preserved that ability and tied it to MSHV migration compatibility.

**Design constraint:** restoring one environment variable inside the container is insufficient because the binary is now fetched on the host before container execution.

## Evidence boundary

- This establishes a test-tool plumbing regression, not that every alternate release is migration-compatible.
- No MSHV live-upgrade run has been executed by Linux Fieldwork.
- The exact later commit that finally removed the variable is not required to establish the current broken boundary; current source plus preserved intent is sufficient.
- Dynamic release checksum policy remains a design question.

## Next step

Create a small candidate around host-side previous-release selection with no-network unit/CLI tests for:

1. default v39.0 selection;
2. valid non-default version selection;
3. invalid version rejection;
4. unchanged verification for unrelated static assets.

Only after the source boundary is stable should the candidate be exercised on MSHV with a known-compatible non-v39 release.

## Authority

No upstream issue, pull request, comment, review, or other interaction has been authorized or created by this investigation.