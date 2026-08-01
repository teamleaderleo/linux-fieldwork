# Tests and receipts — unit 11

## Evidence policy

Exact current-upstream receipts are authoritative for application and focused behavior. Historical CI remains useful for carrier lineage and full Linux Fieldwork repository coverage.

## Exact current-upstream gate — final selected receipt

### Identity

| Field | Exact value |
| --- | --- |
| Linux Fieldwork branch head tested | `83efaa3b3baee05c6b8f96138a3ee619942ce984` |
| Draft internal PR | #401 |
| Workflow run | `30689911760` |
| Canonical null job | `91342674259` |
| Canonical refined topology job | `91342674164` |
| Canonical mmdebstrap commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Last commit touching canonical `coverage.py` | `c82fc7e261c7a2fd85e499484108408fd42331d2` |
| Canonical/imported `coverage.py` blob | `9a522484aef05deae514a98e4b6adf5feb6c886d` |
| Canonical `run_null.sh` blob | `e0a8c106f9d3d636baea286d2ab33834748dffc9` |
| Canonical `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Packet patch blob | `f1a2c75adfa009b6f1ac29e5a31bef526400444f` |
| Historical prefixed group patch blob | `4f2a749e50d42655ebb6519ca6550d2f666985bc` |
| PR #313 mechanism commit | `e90fc438f530f7bd78ffd6fd1ba24c665bd96913` |
| PR #339 refined test commit | `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` |
| Refined QEMU test blob | `0c2a050faf8e98320fc0c4fe4634d46bdf7f0dfa` |

### Canonical source and packet-patch job

The job cloned the canonical repository read-only, checked out exact commit `77ec9be...`, verified its `coverage.py` blob equals the Linux Fieldwork import, copied canonical source and `run_null.sh` into the test checkout, and ran:

```sh
python3 -m py_compile \
  upstream-packets/units/11-coverage-backend-cancellation/scripts/test_current_import.py
python3 upstream-packets/units/11-coverage-backend-cancellation/scripts/test_current_import.py -v
python3 upstream-packets/units/11-coverage-backend-cancellation/scripts/test_current_import.py -v
```

The verifier itself:

```sh
patch --batch --forward --fuzz=0 -p1 \
  -i patches/0001-coverage-own-selected-backend-group.patch
python3 -m py_compile baseline-coverage.py status-only-coverage.py group-owned/coverage.py
```

Result on both passes:

```text
Ran 6 tests
OK
patch_application=success fuzz=0
source_blob=9a522484aef05deae514a98e4b6adf5feb6c886d
patch_blob=f1a2c75adfa009b6f1ac29e5a31bef526400444f
```

Assertions passed twice:

- imported baseline returned 0 and left a nested pipeline alive until deliberate release;
- status-only comparator returned 130 and left that nested pipeline alive until deliberate release;
- group candidate returned 130, drained the responsive group, and produced no later-work marker;
- imported foreground-group SIGINT remained clean;
- unsignaled group candidate succeeded;
- source-shape controls distinguished all three variants.

Artifact:

- ID `8815289674`;
- name `unit-11-canonical-upstream-gate`;
- size `1366` bytes;
- SHA-256 `25e62dec929f27e628816568d6264f2bee45474c00b00c3c047f53209608ef1d`;
- expiry `2026-10-30T07:31:33Z`.

### Canonical refined topology job

The job materialized exact PR #339 commit `8253ab2...`, verified four exact regression blobs, replaced its imported `coverage.py`, `run_null.sh`, and `run_qemu.sh` with files from canonical commit `77ec9be...`, compiled the source and tests, then ran these modules twice:

```sh
python3 -m unittest -v \
  tests.test_mmdebstrap_coverage_process_group \
  tests.test_mmdebstrap_coverage_qemu_process_group \
  tests.test_mmdebstrap_coverage_sudo_process_group
```

Exact regression blobs:

| Module | Blob |
| --- | --- |
| parent-only status fixture | `9bedaa7cd2368f8679de9948d9fecb3fe75c6bd2` |
| null/process-group fixture | `1649c10f8d6639bd26a42b9ab3587b64d84e072c` |
| PR #339 refined QEMU fixture | `0c2a050faf8e98320fc0c4fe4634d46bdf7f0dfa` |
| actual sudo fixture | `8cc7cffb129595a5e4b967385616fbeede4814db` |

Result:

```text
first pass: Ran 14 tests in 3.874s — OK
immediate rerun: Ran 14 tests in 3.599s — OK
```

No skips occurred. The actual passwordless-sudo tests ran and proved root-worker survival in both losing variants plus group settlement in the selected candidate. The refined QEMU losing controls recorded handler entry before deliberate survivor release.

Artifact:

- ID `8815290820`;
- name `unit-11-canonical-refined-topology-gate`;
- size `1625` bytes;
- SHA-256 `63634782bfd230129238ee71aa60ad83ae5b43dfcf3291123cfdbd0770bdf63e`;
- expiry `2026-10-30T07:31:33Z`.

### Cleanup and rerun

Both jobs completed successfully on Ubuntu 24.04 runners. Every temporary Python `TemporaryDirectory` completed, all owned test groups settled, deliberate losing-control survivors were released and reaped, and GitHub's final cleanup reported orphan-process cleanup completion. Both complete matrices passed an immediate rerun.

## Distinguishing result

| Variant | Parent-only SIGINT status | Responsive backend state | Later work |
| --- | ---: | --- | --- |
| imported baseline | 0 after deliberate release | alive before release | yes |
| status-only predecessor | 130 after deliberate release | alive before release | yes |
| selected group candidate | 130 | no live in-group process | no |

## Historical executed matrix

### Status-only predecessor

| Evidence | Exact identity | Result |
| --- | --- | --- |
| PR #143 candidate | `96ddac76ab9dead7875937a6edfa37137bc52eb9` | source change reviewed |
| Linux Fieldwork CI | run `30577412842` | success |
| Clean internal carrier | PR #204 head `b5efc8faf35c1da725a3b995a344fadc078ad5d2` | merged internally |
| Execution carrier | PR #201 run `30579465025` | exact four-test matrix ran twice successfully |

### Selected group candidate

| Evidence | Exact identity | Result |
| --- | --- | --- |
| PR #313 executed mechanism | `e90fc438f530f7bd78ffd6fd1ba24c665bd96913` | product matrix executed |
| Linux Fieldwork CI | run `30632491641`, job `91161937871` | success |
| PR #313 evidence head | `dfc6d0503fb844f4c428ce16a567a9fdcd35280a` | current-head repository gate passed |
| Current-head repository gate | run `30633602052` / 943 | success |
| QEMU evidence refinement | PR #339 `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` | exact refinement now re-executed on canonical source |
| Refinement gate | run `30633578396` / 942 | historical success |

Historical mechanism CI also ran all 359 discovered Linux Fieldwork tests, Python compilation, shell syntax, and command-help checks.

### Stronger policy research

| Evidence | Exact identity | Result |
| --- | --- | --- |
| Issue #341 retained carrier | PR #347 head `615bd4f5256d9851f682e48e037169ceeb7bb98c` | closed, no product patch |
| Composed gate | run `30637202171` / 978 | success |
| Finalization successor | PR #353 head `55bf9e9c8b511399647658139c006afc4ed1fc52` | composed into research carrier |

The research proved synthetic TERM-to-KILL sufficiency while supplying no real-backend necessity, grace-period, or state-loss evidence. Escalation remains unselected.

## Reproducible internal commands

The durable verifier is:

```sh
python3 upstream-packets/units/11-coverage-backend-cancellation/scripts/test_current_import.py -v
```

The exact Actions carrier is:

```text
.github/workflows/unit-11-coverage-backend-cancellation.yml
```

## Unexecuted broad gates and claim limits

- real QEMU/debvm execution;
- full mirror-backed `coverage.py` matrix with prepared Debian mirror state;
- non-Linux execution;
- TERM-resistant or group-escaping descendant product policy;
- public upstream CI and maintainer review.

These remain evidence limits. They do not block the selected responsive-topology contribution.
