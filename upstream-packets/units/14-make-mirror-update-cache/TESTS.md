# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Canonical upstream base | `josch/mmdebstrap` `main` `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Canonical/base source blob | `make_mirror.sh` `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Controlled staging base | `teamleaderleo/mmdebstrap` `master` `574048f2a720057b75e56622003932f344dc700a` |
| Candidate head | `c94132e344f97cee95901623552df6bcde5039bb` |
| Candidate source blob | `make_mirror.sh` `7d92a29a05ade7f5da397a1a9d03e601092f9465` |
| Linux Fieldwork branch | `upstream/unit-14-make-mirror-update-cache` |
| Platform/distribution | retained Linux Fieldwork hosted CI plus GitHub-hosted branch builder on `ubuntu-latest` |
| Architecture | GitHub-hosted runner default architecture; retained component runs use their recorded hosted runner identities |
| Shell/runtime | real `/bin/sh`; GNU `patch`; GitHub Actions checkout and Git |
| Privilege boundary | unprivileged disposable files/processes; no root, mount, APT, network mirror, or QEMU operation |
| Important tool versions | exact hosted run IDs and commit/blob identities below |

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

### Retained dynamic matrix

```text
python3 -m unittest -v \
  tests/test_make_mirror_update_cache_signal_ownership.py \
  tests/test_make_mirror_update_cache_signal_matrix.py \
  tests/test_make_mirror_update_cache_cleanup_failure.py \
  tests/test_make_mirror_update_cache_cleanup_signals.py \
  tests/test_make_mirror_update_cache_cleanup_signals_rerun.py
```

### Controlled source construction

```text
sh linux-fieldwork/apply-unit-14.sh --check
sh linux-fieldwork/apply-unit-14.sh --apply
```

The GitHub branch builder preserved the patch, switched to controlled `master`, verified the exact base blob and patch SHA-256, applied with `patch --fuzz=0 -p1`, ran `/bin/sh -n`, ran `git diff --check`, enforced source ownership assertions, committed only `make_mirror.sh`, and pushed the source branch only after every preceding command succeeded.

### Expected result

INT/QUIT/TERM return 130/131/143; worker APT cleanup completes once; later work is absent; the parent owns proxy stop/wait; first cleanup-time signal survives later handled signals; ordinary or explicit-signal failure outranks cleanup-time signal; cleanup-time signal outranks cleanup failure; success plus cleanup failure returns 74; immediate reruns return 0.

### Observed result

- component dynamic status: all retained candidate cases passed under exact-head hosted runs;
- controlled source construction: source branch created at `c94132e344f97cee95901623552df6bcde5039bb`, proving all guarded builder commands before `git push` succeeded;
- candidate diff: one commit ahead, zero behind controlled `master`; exactly `make_mirror.sh`, 46 additions, 6 deletions;
- candidate source blob: `7d92a29a05ade7f5da397a1a9d03e601092f9465`;
- exact-candidate dynamic lifecycle rerun: pending.

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
| Collapsed patch exact-base application | baseline blob `6c4be092...` | zero fuzz, source-only commit | controlled branch builder | candidate `c94132e...` |
| Shell syntax | baseline syntax valid | candidate syntax valid | `/bin/sh -n make_mirror.sh` | builder prerequisite to push |
| Ownership source assertion | worker references `PROXYPID` | no `PROXYPID` in `update_cache()` | guarded `sed`/`grep` check | builder prerequisite to push |
| Complete candidate diff | n/a | one file, 46 additions, 6 deletions | compare controlled `master...source` | reviewed `c94132e...` |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Full-tree patch check | guarded `patch --dry-run --fuzz=0 -p1` followed by application | PASS | `c94132e344f97cee95901623552df6bcde5039bb` |
| Shell syntax | `/bin/sh -n make_mirror.sh` | PASS before source branch push | `c94132e344f97cee95901623552df6bcde5039bb` |
| Diff hygiene | `git diff --check -- make_mirror.sh` | PASS before source branch push | `c94132e344f97cee95901623552df6bcde5039bb` |
| Complete one-file review | compare controlled `master` to source candidate and inspect commit diff | PASS; expected one-file lifecycle change only | `c94132e344f97cee95901623552df6bcde5039bb` |
| Focused native test | select the smallest upstream entry point that exercises this shell lifecycle | NOT RUN | `c94132e...` |
| Complete mirror generation | `./make_mirror.sh` | NOT RUN — network/mirror integration and time cost | `c94132e...` |
| Relevant suite | `CMD=./mmdebstrap ./coverage.sh` or selected `coverage.py` case | NOT RUN | `c94132e...` |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| PR #286 exact-head repository CI | run `30624335126` / 842 | PASS; 249 tests | head `2c85afa8c947ff040b4c6d876d9b88cf545dbb59` |
| PR #324 exact-head repository CI | run `30630467076` / 916 | PASS; repository discovery plus all five lifecycle modules | head `0906573b434710032f44807bfb5d6bb017a510f6` |
| PR #324 executable predecessor head | run `30630113839` / 911 | PASS; 303 tests | head `d33871b6c05947384d1c235c653a40b57772d82d` |
| Combined packet patch digest | `sha256sum 0001-update-cache-worker-lifecycle.patch` | PASS | `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42` |
| Current/base source identity | canonical upstream, Linux Fieldwork import, and controlled base | MATCH | blob `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Controlled source candidate identity | source branch commit and file readback | MATCH | head `c94132e...`; blob `7d92a29a...` |

## Patch application and rebase

- canonical base identity: upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94`, `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590`;
- controlled staging base: `teamleaderleo/mmdebstrap` `master` `574048f2a720057b75e56622003932f344dc700a`, same `make_mirror.sh` blob;
- patch application command: `patch --dry-run --fuzz=0 -p1` then `patch --fuzz=0 -p1` using the fixed packet patch;
- fuzz/offset result: zero fuzz; candidate commit created only after success;
- conflict resolution: none;
- complete diff reviewed: yes, one source file only, expected 46 additions and 6 deletions;
- active overlap searched: indexed official issue/PR search on 2026-07-31 found no equivalent carrier; direct freshness check remains pending before authorization.

## Cleanup and rerun

The retained tests use temporary directories, short-lived shell processes, owned proxy models, signal barriers, waits, and event logs. Candidate cases remove APT state, reap owned processes through the correct owner, omit later work, and pass immediate unsignaled reruns. The controlled branch builder left only the two intentional branches and commits in `teamleaderleo/mmdebstrap`; no test process, socket, mount, container, or generated mirror state was retained.

## Tests not run

- the five retained lifecycle modules have not yet been rerun against exact candidate head `c94132e...` as a source-branch identity gate;
- no upstream-native focused test currently targets `update_cache()` lifecycle directly;
- complete mirror generation and full coverage remain unexecuted because they require a deliberate network/mirror integration run;
- HUP, escalation, hostile descendant, permanently blocked cleanup, and process-group cases remain outside this unit;
- final canonical Forgejo branch CI remains unavailable until a delivery-compatible fork or route exists.

## Failure classification

- direct assistant-container Git/DNS retrieval failures remain environment/tooling failures and no longer block controlled source construction;
- the controlled GitHub repository has downstream history, but the changed file base matched canonical upstream exactly; this is a repository-ancestry caveat, not source drift for unit 14;
- historical malformed hunk packaging in PR #238 was a patch-carrier defect repaired before canonical composition;
- historical duplicate unittest discovery in PR #286 was a test import defect repaired before the exact green head.

## Final evidence statement

The canonical upstream source, Linux Fieldwork import, and controlled staging base share the exact `make_mirror.sh` blob exercised by the retained component matrices. The collapsed patch now applies with zero fuzz to that full file and produces a source-only candidate commit with valid shell syntax, clean diff hygiene, correct ownership assertions, and no unrelated changes. The retained dynamic matrices establish the complete worker lifecycle on the canonical component compositions. The first incomplete technical gate is rerunning the relevant dynamic lifecycle evidence against exact candidate head `c94132e...`, followed by the smallest credible upstream-native check.
