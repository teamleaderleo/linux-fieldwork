# Source map — unit 11

## Product source

| Surface | Exact identity | Role |
| --- | --- | --- |
| Canonical upstream | `josch/mmdebstrap` Forgejo, `main` | intended contribution destination |
| Exact upstream base executed | `77ec9be5417ee44c96343d2347145585da1b1f94` | selected contribution base |
| Last commit touching `coverage.py` | `c82fc7e261c7a2fd85e499484108408fd42331d2` | source-history boundary |
| Canonical/imported source | `coverage.py` blob `9a522484aef05deae514a98e4b6adf5feb6c886d` | exact baseline |
| Canonical null wrapper | `run_null.sh` blob `e0a8c106f9d3d636baea286d2ab33834748dffc9` | null and sudo execution boundary |
| Canonical QEMU wrapper | `run_qemu.sh` blob `426aeeb854173569b24e64d6eb85019f45bdf0b6` | synthetic QEMU-wrapper boundary |
| Changed product file | `coverage.py` | backend launch and SIGINT handling |
| Retained packet patch | `patches/0001-coverage-own-selected-backend-group.patch` blob `f1a2c75adfa009b6f1ac29e5a31bef526400444f` | upstream-root selected candidate |
| Durable null verifier | `scripts/test_current_import.py` | zero-fuzz application and six-control matrix |
| Actions carrier | `.github/workflows/unit-11-coverage-backend-cancellation.yml` | exact canonical and refined topology execution |
| Internal review surface | PR #401 | packet and execution review |

## Exact baseline source

```python
proc = subprocess.Popen(argv)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
```

Canonical upstream `77ec9be...` and Linux Fieldwork's import have the same `coverage.py` blob `9a522484...`.

## Carrier lineage

| Carrier | Identity | Disposition and useful evidence |
| --- | --- | --- |
| Issue #141 | parent-only SIGINT false success | status 0 defect and status-130 requirement |
| PR #143 | `96ddac76ab9dead7875937a6edfa37137bc52eb9` | historical status-only candidate; retired |
| PR #204 | head `b5efc8faf35c1da725a3b995a344fadc078ad5d2`, merge `23522b7f7d39ee3a237820e46168720edafb4d0a` | merged internal status-only evidence |
| Issue #306 | group ownership finding | wrapper-survival distinction and narrow selection |
| PR #313 | mechanism `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`; evidence head `dfc6d0503fb844f4c428ce16a567a9fdcd35280a` | selected group-delivery product carrier |
| PR #332 | `e860c94f99854b77975b3176c5bf593759fc2714` | superseded patch-context repair |
| PR #336 | `6ea1487d602a2cb3932cf31748e820bc261e0429` | superseded QEMU evidence repair |
| PR #339 | `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` | selected QEMU handler-entry refinement |
| Issue #341 | escalation research | selected no stronger product policy |
| PR #347 | `615bd4f5256d9851f682e48e037169ceeb7bb98c` | retained synthetic resistant/repeated-SIGINT comparison |
| PR #353 | `55bf9e9c8b511399647658139c006afc4ed1fc52` | final-publication and containment successor |
| PR #401 | branch `upstream/unit-11-coverage-backend-cancellation` | current internal unit workspace and canonical execution surface |

## Exact regression ownership

| Regression | Blob | Executed use |
| --- | --- | --- |
| `tests/test_mmdebstrap_coverage_parent_sigint.py` | `9bedaa7cd2368f8679de9948d9fecb3fe75c6bd2` | shared status fixture |
| `tests/test_mmdebstrap_coverage_process_group.py` | `1649c10f8d6639bd26a42b9ab3587b64d84e072c` | null/source/status controls |
| PR #339 `tests/test_mmdebstrap_coverage_qemu_process_group.py` | `0c2a050faf8e98320fc0c4fe4634d46bdf7f0dfa` | refined QEMU-wrapper controls |
| `tests/test_mmdebstrap_coverage_sudo_process_group.py` | `8cc7cffb129595a5e4b967385616fbeede4814db` | actual passwordless-sudo controls |

## Current canonical execution

Workflow run `30689911760` on exact branch head `83efaa3b3baee05c6b8f96138a3ee619942ce984`:

| Job | Result | Artifact |
| --- | --- | --- |
| canonical source + packet patch | six controls twice, zero-fuzz application, compilation, success | `8815289674`, SHA-256 `25e62dec929f27e628816568d6264f2bee45474c00b00c3c047f53209608ef1d` |
| PR #339 refined null/QEMU/sudo topology | fourteen controls twice, no skips, success | `8815290820`, SHA-256 `63634782bfd230129238ee71aa60ad83ae5b43dfcf3291123cfdbd0770bdf63e` |

The topology job copied canonical `coverage.py`, `run_null.sh`, and `run_qemu.sh` into the exact PR #339 test carrier before execution.

## Patch relationship

The packet patch is the product hunk from PR #313's `0001-own-backend-process-group.patch`, rebased as an upstream-root patch against `coverage.py`.

- packet patch blob: `f1a2c75adfa009b6f1ac29e5a31bef526400444f`;
- Linux Fieldwork-prefixed historical patch blob: `4f2a749e50d42655ebb6519ca6550d2f666985bc`.

The older PR #204 patch is a strict semantic subset: it changes `break` to a diagnostic plus `SystemExit(130)` while retaining immediate-child-only termination.

## Destination map

- canonical repository and issue tracker: `https://gitlab.mister-muffin.de/josch/mmdebstrap`;
- canonical branch: `main`;
- Debian packaging VCS: `https://salsa.debian.org/debian/mmdebstrap.git`;
- proposed delivery: controlled Forgejo fork and pull request;
- controlled fork: `NEEDS FORK`;
- explicit external authorization: absent;
- external contact made: none.
