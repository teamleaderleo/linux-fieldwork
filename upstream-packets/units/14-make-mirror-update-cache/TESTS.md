# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | `josch/mmdebstrap` `main` `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Upstream source blob | `make_mirror.sh` `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Candidate head | `NEEDS BRANCH` |
| Linux Fieldwork branch | `upstream/unit-14-make-mirror-update-cache` |
| Platform/distribution | retained hosted Linux Fieldwork CI; this pass used the assistant container for patch-carrier arithmetic only |
| Architecture | hosted runner architecture recorded by the CI service; current local check architecture was not used as product evidence |
| Shell/runtime | retained matrices: real `/bin/sh`; local patch command: GNU `patch` |
| Privilege boundary | unprivileged disposable files/processes; no root, mount, APT, network mirror, or QEMU operation |
| Important tool versions | exact hosted run IDs below; local combined-patch SHA-256 below |

## Baseline reproducer

### Command

```text
python3 -m unittest -v tests/test_make_mirror_update_cache_signal_ownership.py
python3 -m unittest -v tests/test_make_mirror_update_cache_cleanup_signals.py
```

### Expected distinguishing result

The ownership baseline returns status 0 after worker-only TERM, executes later work, cleans twice, and kills the parent-owned proxy. The cleanup-time predecessor exits by the later/default signal after cleanup `start`, leaves APT state, or replaces explicit TERM 143 with later INT.

### Observed result

- status: ownership baseline 0; cleanup-time predecessor terminates by SIGTERM or SIGINT in the designated cases;
- stdout/stderr: retained fixtures record event logs rather than relying on prose output;
- changed state: later-work marker present and duplicate cleanup in the ownership baseline; cleanup reaches only `start` and leaves APT state in cleanup-time predecessor cases;
- surviving processes/files/resources: parent-owned proxy is killed by the baseline worker; predecessor cleanup-time state remains;
- artifact or receipt: PR #286 CI `30624335126` / 842 and PR #324 CI `30630467076` / 916.

## Candidate reproducer

### Command

```text
python3 -m unittest -v \
  tests/test_make_mirror_update_cache_signal_ownership.py \
  tests/test_make_mirror_update_cache_signal_matrix.py \
  tests/test_make_mirror_update_cache_cleanup_failure.py \
  tests/test_make_mirror_update_cache_cleanup_signals.py \
  tests/test_make_mirror_update_cache_cleanup_signals_rerun.py
```

### Expected result

INT/QUIT/TERM return 130/131/143; worker APT cleanup completes once; later work is absent; the parent owns proxy stop/wait; first cleanup-time signal survives later handled signals; ordinary or explicit-signal failure outranks cleanup-time signal; cleanup-time signal outranks cleanup failure; success plus cleanup failure returns 74; immediate reruns return 0.

### Observed result

- status: all retained candidate cases passed under the exact-head hosted runs;
- stdout/stderr: focused modules reported successful unittest cases and repository discovery;
- changed state: APT state removed, one complete cleanup, no later marker;
- surviving processes/files/resources: no retained worker state or proxy leak in the focused models;
- artifact or receipt: CI `30624335126` / 842 for PR #286 and CI `30630467076` / 916 for PR #324.

## Matrix

| Case | Baseline/predecessor | Candidate | Exact command or test | Result identity |
| --- | --- | --- | --- | --- |
| Worker-only TERM | 0, later work, cleanup twice, proxy killed | 143, no later work, worker cleanup once, parent proxy cleanup | `test_make_mirror_update_cache_signal_ownership.py` | PR #286 CI 842 |
| Direct INT/QUIT/TERM | cleanup-only handler resumes | 130/131/143 | `test_make_mirror_update_cache_signal_matrix.py` | PR #286 CI 842 |
| Ordinary failure 42 plus cleanup 74 | cleanup may obscure/re-enter | 42 | ownership/precedence case | PR #286 CI 842 |
| TERM 143 plus cleanup 74 | cleanup may obscure/re-enter | 143 | ownership/precedence case | PR #286 CI 842 |
| Success plus cleanup 74 | duplicate EXIT cleanup possible | 74 after one cleanup | `test_make_mirror_update_cache_cleanup_failure.py` | PR #286 CI 842 |
| Explicit TERM then later INT during cleanup | later INT replaces result and interrupts cleanup | 143; cleanup `start,end` | `test_make_mirror_update_cache_cleanup_signals.py` | PR #324 CI 916 |
| Ordinary cleanup plus INT/QUIT/TERM | default signal interrupts cleanup | 130/131/143; later signal ignored | same module | PR #324 CI 916 |
| Host failure 42 plus cleanup-time TERM | cleanup-time signal can interfere | 42 | same module | PR #324 CI 916 |
| Cleanup-time TERM plus cleanup 74 | default signal/cleanup ordering undefined | 143 | same module | PR #324 CI 916 |
| Explicit TERM, cleanup 74, later INT | later signal can replace first | 143 | `test_make_mirror_update_cache_cleanup_signals_rerun.py` | PR #324 CI 916 |
| Unsignaled success plus cleanup 74 after patch 2 | regression risk | 74 | rerun module | PR #324 CI 916 |
| Immediate rerun after cleanup-time signal | retained state can poison rerun | 0 | rerun module | PR #324 CI 916 |
| Two-patch full-source application | baseline plus two retained patches | zero fuzz; shell syntax passes | focused modules/repository CI | PR #324 CI 916 |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Full-tree patch check | `git apply --check --verbose upstream-packets/units/14-make-mirror-update-cache/patches/0001-update-cache-worker-lifecycle.patch` from upstream checkout | NOT RUN — controlled checkout unavailable in this environment | NEEDS BRANCH |
| Shell syntax | `/bin/sh -n make_mirror.sh` after combined patch | NOT RUN on the new single carrier; passed for exact two-patch composition in PR #324 | NEEDS BRANCH |
| Focused native test | select and run the smallest upstream entry point after branch creation | NOT RUN | NEEDS BRANCH |
| Complete mirror generation | `./make_mirror.sh` | NOT RUN — network/mirror integration and time cost; decide after focused gates | NEEDS BRANCH |
| Relevant suite | `CMD=./mmdebstrap ./coverage.sh` or selected `coverage.py` case | NOT RUN | NEEDS BRANCH |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| PR #286 exact-head repository CI | run `30624335126` / 842 | PASS; 249 tests | head `2c85afa8c947ff040b4c6d876d9b88cf545dbb59` |
| PR #324 exact-head repository CI | run `30630467076` / 916 | PASS; repository discovery plus all five lifecycle modules | head `0906573b434710032f44807bfb5d6bb017a510f6` |
| PR #324 executable predecessor head | run `30630113839` / 911 | PASS; 303 tests | head `d33871b6c05947384d1c235c653a40b57772d82d` |
| Combined packet patch digest | `sha256sum 0001-update-cache-worker-lifecycle.patch` | PASS | `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42` |
| Combined hunk arithmetic | synthetic exact-position source plus `patch --fuzz=0 --no-backup-if-mismatch -p1` | PASS; both hunks applied at declared lines | local receipt: first new symbol line 156, terminal call line 298 |
| Current source identity | official upstream main and Debian dgit/current import comparison | MATCH | blob `6c4be092edcf23b56b63a3befe238c099c45f590` |

## Patch application and rebase

- base identity: upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94`, `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590`;
- provenance application: retained patches 0001 and 0002 applied with zero fuzz to the full imported source in PR #324 CI;
- combined patch application: hunk grammar/count/positions verified locally on an exact-position synthetic carrier; full-tree command remains pending;
- fuzz/offset result: provenance composition zero fuzz; combined full-tree offset result pending;
- conflict resolution: none expected because current upstream source blob is identical;
- complete diff reviewed: component diffs reviewed in PRs #286 and #324; new collapsed one-file diff requires final branch review;
- active overlap searched: indexed official issue/PR search on 2026-07-31 found no equivalent carrier; direct freshness check remains pending before authorization.

## Cleanup and rerun

The retained tests use temporary directories, short-lived shell processes, owned proxy models, signal barriers, waits, and event logs. Candidate cases remove APT state, reap owned processes through the correct owner, omit later work, and pass immediate unsignaled reruns. The local synthetic patch check retained only `/tmp/unit14` files during analysis; no process, socket, mount, container, or source checkout survived.

## Tests not run

- full-tree application of the new collapsed carrier, due direct DNS failure before repository retrieval;
- upstream-native focused/integration tests, because no controlled upstream branch exists yet;
- complete mirror generation, which requires network mirror access and a deliberate integration run;
- full coverage suite on the collapsed branch;
- HUP, escalation, hostile descendant, permanently blocked cleanup, and process-group cases, which remain outside this unit.

## Failure classification

- direct `git clone` and direct `curl` retrieval failed at DNS resolution before source retrieval: environment/tooling failure;
- `container.download` reached the raw source but rejected `text/x-shellscript` as a disallowed materialization type: tooling/materialization failure;
- the first local synthetic patch invocation targeted a file named `synthetic` while the patch names `make_mirror.sh`; after renaming the fixture, both hunks applied cleanly: local fixture setup failure, then pass;
- historical malformed hunk packaging in PR #238 was a patch-carrier defect repaired before canonical composition;
- historical duplicate unittest discovery in PR #286 was a test import defect repaired before the exact green head.

## Final evidence statement

The current upstream source is the exact blob exercised by the retained Linux Fieldwork matrices. Those matrices establish the complete two-stage worker lifecycle: ownership separation, terminating signal statuses, once-only cleanup, cleanup-failure precedence, first cleanup-time signal retention, later-signal suppression, state removal, and immediate rerun. This pass created one upstream-facing patch with fixed digest and verified its hunk arithmetic. Full-tree application of that newly collapsed carrier and upstream-native execution remain the first technical gate.
