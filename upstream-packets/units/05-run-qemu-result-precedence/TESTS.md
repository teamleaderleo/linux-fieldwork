# Tests and receipts — unit 05

## Current extraction pass

Date: 2026-08-01  
Execution boundary: disposable local Git repository, exact imported source text, exact four retained patch texts, system `/bin/sh`.

### Base identity

| Check | Result |
| --- | --- |
| Imported path | `upstream/mmdebstrap/run_qemu.sh` |
| Git blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Byte count | 2,029 |
| SHA-256 | `da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300` |

### Exact command sequence

The disposable repository contained the imported path and packet patch names. The worker ran:

```sh
git init -q

git apply --check patches/0001-preserve-primary-result.patch
git apply patches/0001-preserve-primary-result.patch

git apply --check patches/0002-retain-first-signal-through-cleanup.patch
git apply patches/0002-retain-first-signal-through-cleanup.patch

git apply --check patches/0003-retain-signal-during-exit-cleanup.patch
git apply patches/0003-retain-signal-during-exit-cleanup.patch

git apply --check patches/0004-preserve-completed-guest-before-cleanup-signal.patch
git apply patches/0004-preserve-completed-guest-before-cleanup-signal.patch

/bin/sh -n upstream/mmdebstrap/run_qemu.sh
wc -c upstream/mmdebstrap/run_qemu.sh
sha256sum upstream/mmdebstrap/run_qemu.sh
```

### Results

| Gate | Exit status | Exact result |
| --- | ---: | --- |
| patch 1 `git apply --check` | 0 | clean |
| patch 1 `git apply` | 0 | applied |
| patch 2 `git apply --check` | 0 | clean |
| patch 2 `git apply` | 0 | applied |
| patch 3 `git apply --check` | 0 | clean |
| patch 3 `git apply` | 0 | applied |
| patch 4 `git apply --check` | 0 | clean |
| patch 4 `git apply` | 0 | applied |
| `/bin/sh -n` | 0 | syntax accepted |
| final byte count | — | 2,924 |
| final SHA-256 | — | `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f` |

The compact raw receipt is retained at `artifacts/2026-08-01-apply-and-syntax.txt`.

## Canonical historical execution

Canonical PR #319 exact head:

```text
2fe3f99364df29de217536dc35a4d03b10f49640
```

Linux Fieldwork CI:

```text
run 30628645668
job 889
result success
repository tests 276 passed
```

The run included all five focused modules once, the full four-patch zero-fuzz composition, complete `/bin/sh -n`, cleanup completion, immediate reruns, and repository discovery without duplicate imported tests.

## Focused behavioral matrix retained by the canonical tests

| Earlier result | Later event | Selected final result |
| --- | --- | --- |
| host timeout 124 | guest failure | 124 |
| host failure 42 | missing or malformed guest result | 42 |
| explicit INT | guest success or failure | 130 |
| explicit TERM | guest success or failure | 143 |
| TERM starts cleanup | later INT | 143; cleanup completes |
| INT starts cleanup | later TERM | 130; cleanup completes |
| ordinary success | INT during cleanup | 130 |
| ordinary success | TERM during cleanup | 143 |
| completed guest failure | later TERM during cleanup | 1 |
| completed malformed or missing guest result | later TERM during cleanup | 1 |
| guest success | cleanup-time signal and cleanup failure | signal result |
| host and guest success | first cleanup failure | first cleanup failure |
| all success | none | 0 |

## Negative controls retained

- original source: host 124 plus guest failure becomes 1;
- original source: parent-only INT/TERM becomes guest-dependent 0 or 1;
- patch 1: TERM followed by INT can terminate cleanup by SIGINT and retain temporary state;
- patches 1–2: TERM during ordinary EXIT cleanup can disappear as status 0;
- patches 1–3: completed guest failure plus later TERM can become 143;
- fixture variant: omitted recorder function causes candidate exit 127;
- substring fixture assertion aliases `cleanup_signal()` with `record_cleanup_signal()`.

## Cleanup and rerun evidence

The canonical tests use deterministic file barriers and real PID-targeted INT/TERM delivery to reduced `/bin/sh` fixtures. They assert:

- cleanup action order;
- completion after retained signals;
- temporary-directory removal on the successful cleanup path;
- no later workload after cancellation;
- first-signal identity;
- immediate clean rerun.

## Gates still required on live upstream

1. Clone or fetch canonical Salsa `master` and record its full SHA.
2. Record the live `run_qemu.sh` blob, SHA-256, and byte count.
3. Apply the packet series at repository-root `run_qemu.sh`; record fuzz, offsets, or conflicts.
4. Adapt paths only when current upstream layout requires it, preserving product behavior.
5. Run all five focused Linux Fieldwork modules against the rebased source or migrate equivalent tests into an upstream-appropriate harness.
6. Run upstream syntax, lint, and ordinary test targets associated with `run_qemu.sh`.
7. Run a bounded real QEMU/`debvm-run` smoke test only in an authorized environment with disposable images and explicit cleanup.
8. Clean the worktree and rerun the focused gate on the exact candidate head.

## Environment limitation

Direct GitLab cloning and raw/API retrieval failed in the execution environment because the GitLab host could not be resolved. Public Debian Sources and Salsa metadata views supplied package, tag, and file-size observations. This pass therefore records exact applicability to the imported blob and leaves live Salsa applicability as the first incomplete gate.
