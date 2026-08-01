# Source map — unit 11

## Product source

| Surface | Exact identity | Role |
| --- | --- | --- |
| Canonical upstream | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` | intended contribution destination |
| Exact canonical base | `77ec9be5417ee44c96343d2347145585da1b1f94` | contribution base |
| Last commit touching `coverage.py` | `c82fc7e261c7a2fd85e499484108408fd42331d2` | source-history boundary |
| Base source | `coverage.py` blob `9a522484aef05deae514a98e4b6adf5feb6c886d` | wrapper-only baseline |
| Canonical null wrapper | `run_null.sh` blob `e0a8c106f9d3d636baea286d2ab33834748dffc9` | null and sudo boundary |
| Canonical QEMU wrapper | `run_qemu.sh` blob `426aeeb854173569b24e64d6eb85019f45bdf0b6` | QEMU-wrapper boundary |
| Retained packet patch | `patches/0001-coverage-own-selected-backend-group.patch` blob `f1a2c75adfa009b6f1ac29e5a31bef526400444f` | selected source hunk |
| Controlled repository | `teamleaderleo/mmdebstrap` | clean source and internal review |
| Exact snapshot branch | `linux-fieldwork/upstream-main-snapshot@77ec9be...` | controlled canonical base |
| Clean source branch | `linux-fieldwork/unit-11-coverage-backend-cancellation@431614b3af58ba4f70791aa1d42cf5b71c965dd2` | public-shaped candidate |
| Candidate source | `coverage.py` blob `9e31f21cf37228257b5e0705d9ecb13b7a66e40f` | exact final product source |
| Clean changed-file fence | `coverage.py` only, 8 additions and 3 deletions | final source diff |
| Clean review surface | `teamleaderleo/mmdebstrap#4` | eligible independent review |
| Packet review surface | `teamleaderleo/linux-fieldwork#401` | durable evidence and drafts |

## Exact baseline and candidate

Baseline:

```python
proc = subprocess.Popen(argv)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    break
```

Candidate:

```python
proc = subprocess.Popen(argv, start_new_session=True)
try:
    proc.wait()
except KeyboardInterrupt:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    proc.wait()
    print("interrupted by SIGINT", file=sys.stderr)
    raise SystemExit(130)
```

## Regression ownership

| Regression | Blob | Role |
| --- | --- | --- |
| parent-only status fixture | `9bedaa7cd2368f8679de9948d9fecb3fe75c6bd2` | shared status and launch fixture |
| null/process-group fixture | `1649c10f8d6639bd26a42b9ab3587b64d84e072c` | baseline/status/group controls |
| refined QEMU fixture | `0c2a050faf8e98320fc0c4fe4634d46bdf7f0dfa` | handler-entry causal ordering |
| sudo fixture | `8cc7cffb129595a5e4b967385616fbeede4814db` | actual passwordless-sudo topology |
| packet verifier | `scripts/test_current_import.py` | zero-fuzz application and six-control matrix |

These regressions remain in the packet/evidence carriers. The clean target contribution is source-only by explicit decision.

## Current execution surfaces

### Canonical packet execution

- workflow: `.github/workflows/unit-11-coverage-backend-cancellation.yml`;
- canonical run: `30689911760`;
- result: zero-fuzz application, compilation, 6/6 twice, 14/14 twice, no skips;
- artifacts: `8815289674`, `8815290820`.

### Controlled focused target execution

- closed PR: `teamleaderleo/mmdebstrap#2`;
- run: `30706007117`;
- result: exact target byte equivalence, compilation, 6/6 twice, 14/14 twice;
- artifacts: `8820336271`, `8820337503`.

### Controlled ordinary source execution

- closed PR: `teamleaderleo/mmdebstrap#3`;
- run: `30706633832`;
- native path: `coverage.sh help man version`;
- result: 3/3 twice;
- artifact: `8820528312`.

The exact base has a pre-existing Black failure on canonical `tarfilter` blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; the successful ordinary gate isolates only that exact blob.

## Carrier lineage

| Carrier | Identity | Disposition |
| --- | --- | --- |
| issue #141 / PRs #143 and #204 | status-only history | retained comparator |
| issue #306 / PR #313 | mechanism and historical execution | PR closed after evidence transfer |
| PRs #332 and #336 | carrier repairs | closed superseded |
| PR #339 | refined QEMU evidence | closed after evidence transfer |
| issue #341 / PRs #347 and #353 | stronger cleanup policy | retained, no escalation selected |
| PR #406 | current-main ancestry restack | closed superseded |
| PR #401 | canonical durable packet | active |
| controlled PR #2 | focused target runner | closed after evidence transfer |
| controlled PR #3 | ordinary source runner | closed after evidence transfer |
| controlled PR #4 | clean source diff | ready for independent review |

## Patch relationship

- packet patch blob: `f1a2c75adfa009b6f1ac29e5a31bef526400444f`;
- historical prefixed patch blob: `4f2a749e50d42655ebb6519ca6550d2f666985bc`;
- clean candidate blob: `9e31f21cf37228257b5e0705d9ecb13b7a66e40f`.

Run `30706007117` proved the upstream-root patch applies with zero fuzz and produces byte-identical clean target source.

## Destination map

- canonical contribution repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`;
- canonical branch: `main`;
- Debian packaging VCS: `https://salsa.debian.org/debian/mmdebstrap.git`;
- controlled repository: `teamleaderleo/mmdebstrap`;
- proposed delivery: Forgejo fork and pull request after explicit authorization;
- current public authority: absent;
- public upstream contact made: none.
