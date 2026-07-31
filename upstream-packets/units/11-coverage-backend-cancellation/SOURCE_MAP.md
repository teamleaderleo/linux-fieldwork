# Source map — unit 11

## Product source

| Surface | Exact identity | Role |
| --- | --- | --- |
| Canonical upstream | `josch/mmdebstrap` Forgejo, `main` | intended contribution destination |
| Current upstream head observed 2026-08-01 | `77ec9be5417ee44c96343d2347145585da1b1f94` | required rebase base |
| Imported source | `upstream/mmdebstrap/coverage.py` blob `9a522484aef05deae514a98e4b6adf5feb6c886d` | current local baseline |
| Changed product file | `coverage.py` | backend launch and SIGINT handling |
| Retained packet patch | `patches/0001-coverage-own-selected-backend-group.patch` | selected candidate |

## Current local source evidence

Linux Fieldwork `main` lines 413–421 remain:

```python
proc = subprocess.Popen(argv)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
```

The retained patch's import and backend-loop contexts match blob `9a522484...` exactly.

## Carrier lineage

| Carrier | Identity | Disposition and useful evidence |
| --- | --- | --- |
| Issue #141 | parent-only SIGINT false success | owns status 0 defect and focused status-130 requirement |
| PR #143 | head `96ddac76ab9dead7875937a6edfa37137bc52eb9` | historical four-file status-only candidate; retired after clean restack |
| PR #204 | head `b5efc8faf35c1da725a3b995a344fadc078ad5d2`, merge `23522b7f7d39ee3a237820e46168720edafb4d0a` | merged internal status-only evidence and regression |
| Issue #306 | group ownership finding | owns wrapper-survival distinction and narrow selection |
| PR #313 | head `dfc6d0503fb844f4c428ce16a567a9fdcd35280a`; executed mechanism `e90fc438f530f7bd78ffd6fd1ba24c665bd96913` | canonical group-delivery product carrier |
| PR #332 | head `e860c94f99854b77975b3176c5bf593759fc2714` | superseded patch-context repair; exact blob already composed into #313 |
| PR #336 | head `6ea1487d602a2cb3932cf31748e820bc261e0429` | superseded divergent QEMU evidence repair |
| PR #339 | head `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` | current one-file QEMU negative-control refinement |
| Issue #341 | escalation research | selected no stronger product policy |
| PR #347 | head `615bd4f5256d9851f682e48e037169ceeb7bb98c` | retained synthetic TERM-resistant/repeated-SIGINT comparison |
| PR #353 | head `55bf9e9c8b511399647658139c006afc4ed1fc52`, composed merge `615bd4...` | final-publication and unrelated-session containment successor |

## Historical test ownership

PR #313 owns three executable modules:

- `tests/test_mmdebstrap_coverage_process_group.py` — null topology and source/status controls;
- `tests/test_mmdebstrap_coverage_qemu_process_group.py` — QEMU-wrapper topology and losing controls;
- `tests/test_mmdebstrap_coverage_sudo_process_group.py` — actual passwordless-sudo topology.

PR #339 changes only the QEMU module to record exact Python SIGINT-handler entry before releasing a deliberate survivor.

## Patch relationship

`0001-coverage-own-selected-backend-group.patch` is the product hunk from PR #313's `0001-own-backend-process-group.patch`, rebased as an upstream-root patch against `coverage.py` instead of Linux Fieldwork's `upstream/mmdebstrap/coverage.py` path.

The older PR #204 patch is a strict semantic subset: it changes `break` to a diagnostic plus `SystemExit(130)` while retaining immediate-child-only termination.

## Destination map

- Canonical upstream homepage and repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`.
- Canonical branch: `main`.
- Public issue tracker: same Forgejo repository.
- Debian packaging VCS: `https://salsa.debian.org/debian/mmdebstrap.git`.
- Proposed source destination: canonical Forgejo pull request after controlled fork creation and explicit authorization.
- External-contact state: unauthorized; none made.
