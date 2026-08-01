# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Canonical upstream | `https://gitlab.mister-muffin.de/josch/mmdebstrap.git`, `main` |
| Canonical base | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Base `make_mirror.sh` blob | `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Controlled canonical snapshot | `teamleaderleo/mmdebstrap` branch `linux-fieldwork/upstream-main-snapshot` |
| Final candidate branch | `linux-fieldwork/unit-14-make-mirror-update-cache-upstream-main` |
| Final candidate head | `76728bbb8e084b54261713ba80762cd6f6ada79a` |
| Candidate source commit | `b2a9a09b36fd13f22a024ebf8522ac58543eac28` |
| Candidate source blob | `7d92a29a05ade7f5da397a1a9d03e601092f9465` |
| Native test commit | `76728bbb8e084b54261713ba80762cd6f6ada79a` |
| Linux Fieldwork packet branch | `upstream/unit-14-make-mirror-update-cache` |
| Privilege boundary | unprivileged shell processes and disposable files; no root, mount, APT, network mirror, or QEMU operation |

## Baseline negative controls

### Commands

```text
python3 -m unittest -v tests/test_make_mirror_update_cache_signal_ownership.py
python3 -m unittest -v tests/test_make_mirror_update_cache_cleanup_signals.py
```

### Observed distinguishing results

- worker-only TERM returned status 0;
- later worker and owner work executed;
- worker cleanup ran twice;
- the worker killed the parent-owned proxy;
- ordinary cleanup plus TERM stopped after cleanup `start` and retained APT state;
- explicit TERM followed by INT could exit by SIGINT, replacing 143.

Receipts: PR #286 CI `30624335126` / 842 and PR #324 CI `30630467076` / 916.

## Retained candidate matrix

```text
python3 -m unittest -v \
  tests/test_make_mirror_update_cache_signal_ownership.py \
  tests/test_make_mirror_update_cache_signal_matrix.py \
  tests/test_make_mirror_update_cache_cleanup_failure.py \
  tests/test_make_mirror_update_cache_cleanup_signals.py \
  tests/test_make_mirror_update_cache_cleanup_signals_rerun.py
```

Established behavior:

- INT/QUIT/TERM return 130/131/143;
- worker APT cleanup completes once;
- later work is absent;
- the parent owns proxy stop/wait;
- command or explicit-signal failure outranks a cleanup-time signal;
- a cleanup-time signal outranks cleanup failure;
- success plus cleanup failure returns 74;
- the first cleanup-time signal survives later handled signals;
- state is removed and immediate reruns return 0.

## Canonical sync and source construction

Hosted receipt: `teamleaderleo/mmdebstrap` `linux-fieldwork/unit-14-canonical-sync-receipt.md`.

The job:

1. cloned current Forgejo `main`;
2. recorded upstream head `77ec9be...` and source blob `6c4be092...`;
3. mirrored the exact canonical history to `linux-fieldwork/upstream-main-snapshot`;
4. verified patch SHA-256 `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42`;
5. applied the patch with `patch --dry-run --fuzz=0 -p1` and `patch --fuzz=0 -p1`;
6. passed `/bin/sh -n make_mirror.sh`;
7. passed `git diff --check -- make_mirror.sh`;
8. required no `PROXYPID` reference inside `update_cache()`;
9. required the three signal-recording traps and terminal `update_cache_finish 0`;
10. ran ten exact-candidate lifecycle tests;
11. published source commit `b2a9a09b...` atop canonical history.

Exact-candidate result: 10 tests passed in 3.459 seconds.

## Upstream-native regression

Registered files:

- `tests/make-mirror-update-cache-worker-lifecycle`;
- `coverage.txt` entry `Test: make-mirror-update-cache-worker-lifecycle`.

Hosted receipt: `teamleaderleo/mmdebstrap` `linux-fieldwork/unit-14-native-test-receipt.md`.

Executed gates on the canonical-ancestry candidate:

| Gate | Result |
| --- | --- |
| `sh -n tests/make-mirror-update-cache-worker-lifecycle` | PASS |
| shellcheck with upstream exclusions | PASS |
| shfmt with upstream options | PASS |
| direct native test execution | PASS: `make_mirror update_cache worker lifecycle: PASS` |
| `git diff --check` | PASS |
| candidate test commit publication | PASS: head `76728bbb...` |

The native regression extracts the actual finalizer, recorder, wrappers, and traps from `make_mirror.sh`. It checks the worker/proxy ownership fence and drives real `/bin/sh` cases for:

- cleanup-time INT, QUIT, and TERM statuses 130/131/143;
- later handled signal suppression;
- explicit TERM over later INT and cleanup failure;
- host failure 42 over cleanup-time TERM;
- cleanup-time TERM over cleanup failure 74;
- unsignaled cleanup failure 74;
- complete cleanup and APT-state removal;
- absence of later work;
- immediate clean rerun 0.

## Complete candidate diff review

Compare `linux-fieldwork/upstream-main-snapshot` to `linux-fieldwork/unit-14-make-mirror-update-cache-upstream-main`:

- status: ahead;
- commits: 2;
- behind: 0;
- `make_mirror.sh`: +46/-6;
- `coverage.txt`: +2/-0;
- native test: +261/-0;
- no additional paths.

The source commit contains only the composed worker lifecycle. The test commit contains only native registration and the focused regression.

## Matrix summary

| Case | Baseline/predecessor | Final candidate | Evidence |
| --- | --- | --- | --- |
| Worker-only TERM | 0, later work, cleanup twice, proxy killed | 143, one worker cleanup, parent proxy ownership | retained ownership + exact-candidate matrix |
| Direct INT/QUIT/TERM | handler resumes | 130/131/143 | retained signal matrix |
| Failure 42 + cleanup 74 | result can be obscured/re-entered | 42 | retained/native precedence |
| TERM 143 + cleanup 74 | result can be obscured/re-entered | 143 | retained/native precedence |
| Success + cleanup 74 | duplicate cleanup possible | 74 after one cleanup | retained/native cleanup-failure case |
| TERM then INT during cleanup | later INT replaces result; cleanup partial | 143; cleanup complete | retained/native cleanup-time case |
| Ordinary cleanup + INT/QUIT/TERM | default signal interrupts cleanup | 130/131/143; later signal ignored | retained/native signal cases |
| Immediate rerun | retained state can poison run | 0 | retained/native rerun |

## Overlap gate

The live read-only Forgejo API scan is recorded in `linux-fieldwork/unit-14-overlap-scan-receipt.md`. Its exact result and any keyword matches control the final disposition. The scan searched open issues and pull requests for `make_mirror`, `update_cache`, `proxy`, `cleanup`, and `signal`.

## Cleanup and rerun

All focused tests use temporary directories and owned short-lived processes. Candidate cases remove APT state, finish cleanup once, omit later work, and pass immediate reruns. Hosted workflows retained only intentional Git branches, commits, and compact receipts. No test-created process, socket, mount, container, mirror cache, or package state remains.

## Tests deliberately not run

- complete `./make_mirror.sh` mirror generation: requires network and package/mirror state beyond the focused lifecycle discriminator;
- full `coverage.py` run: its global precondition requires a prepared mirror cache; the new registered native test passed directly with the same shellcheck/shfmt rules used by the harness;
- HUP, escalation, hostile descendants, permanently blocked cleanup, and process-group supervision: outside this unit;
- canonical Forgejo-hosted CI: requires an authorized delivery-compatible fork/branch.

## Failure classification

- assistant-container DNS/materialization failures: environment/tooling; superseded by hosted canonical clone;
- downstream `master` ancestry: repository-lineage caveat; superseded by the canonical snapshot/candidate branches;
- historical malformed patch hunk: carrier defect repaired before canonical composition;
- historical duplicate unittest discovery: test-import defect repaired before exact component heads;
- the first native workflow left no receipt: unclassified hosted run; the classified rerun produced the durable PASS receipt and candidate test commit.

## Final evidence statement

The final candidate is two commits over exact current canonical Forgejo `main`. The source patch applies with zero fuzz, passes syntax and diff checks, preserves the worker/proxy ownership fence, passes ten direct candidate lifecycle cases, and carries a registered native regression that passes project formatting and direct execution gates. The complete three-path diff has been reviewed. A full mirror build would add network and package-state variables without improving the focused lifecycle discriminator.
