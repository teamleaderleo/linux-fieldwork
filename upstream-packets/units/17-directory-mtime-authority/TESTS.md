# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Imported source base | Linux Fieldwork `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`; mmdebstrap 1.5.7 blob `41aa46f989a2660cebdb0138e0847cde25b269a3` |
| Current pathname carrier | PR #395 live head `74c996394819c3a717d55193d84336c2e06b3b7c` |
| Descriptor carrier | PR #389 `0319755b71ec594f2019cf40cd3cf9ee68ad7d60` |
| Authority matrix | PR #394 `cffc0ce00f57050539a0e11f11e609d13e9ca604` |
| Packet branch base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Local platform for packet probe | Linux 6.12.13 x86_64 GNU/Linux |
| Runtime | Python 3.13.5 |
| Privilege boundary | unprivileged synthetic `/proc` process controls |

## Real package baseline anchor

- PR #361 head: `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`
- workflow: `30640356619` / 999
- generated merge: `8c2c057a9fd2b3bfc09994e009cf7957e0883691`
- artifact: `8798679560`
- digest: `sha256:50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244`
- package status: 6
- completed package tests: 154
- first failure: `(242/284) chrootless`
- distinguishing result: the same 123 paths differed, all directories, with timestamp fields as the only reported delta.

## Retained carrier gates

| Carrier | Exact execution | Result |
| --- | --- | --- |
| PR #383 | CI `30655487591` / 1057; generated merge `2c3aa47067319163ac84512d01454fcfac08da50` | 432 retained tests passed; four-policy matrix established directory-only selection |
| PR #386 | CI `30653850491` / 1043 | symlink identity repair passed before composition into #383 |
| PR #389 | CI `30656680618` / 1069; generated merge `1d1e5c68fd6defa530ee88e0c734ac3eeb1ade2f` | descriptor candidate repository gates passed |
| PR #390 | CI `30655508564` / 1059 | xattr and sparse-source controls passed |
| PR #391 | repository CI `30656548403` / 1067; dedicated workflow `30656548394` / 1 | real tmpfs, ACL, capability, cleanup, and rerun passed; artifact `8803444764`, digest `sha256:60ae20d7b19d0e690bac39233f273517b16e70c52c10d8428771e3e946bdc548` |
| PR #394 | run `30657891185`, job `91246734757`; generated merge `0ccc162df2fcf4a9a63332eea40bebe88de0f9f3` | 439/439 authority/source controls passed |

## Packet probe command

```text
python3 -m py_compile \
  upstream-packets/units/17-directory-mtime-authority/scripts/archive_boundary_process_probe.py \
  upstream-packets/units/17-directory-mtime-authority/scripts/test_archive_boundary_process_probe.py

python3 -m unittest -v \
  upstream-packets/units/17-directory-mtime-authority/scripts/test_archive_boundary_process_probe.py
```

The executed local command used an equivalent temporary path before commit:

```text
cd /tmp/unit17
python3 -m unittest -v scripts/test_archive_boundary_process_probe.py
```

## Packet probe result

Status: 0

```text
test_cli_excludes_probe_process_and_writes_atomic_json ... ok
test_live_descendant_with_root_references_is_detected ... ok
test_parse_proc_stat_handles_spaces_in_comm ... ok
test_zombie_descendant_is_classified_separately ... ok

Ran 4 tests in 1.662s
OK
```

Hashes from the exact locally executed files:

```text
0df525f641a5632f6cee23a20372ac695f08def14665cc9fe7418dd8a0875e54  archive_boundary_process_probe.py
b409ef7614b2a69414d99f035015c41edfedbf2a7199dddc7492eccae1c63c9c  test_archive_boundary_process_probe.py
af284d8df31844bd556a1627aa41cea9cce7b6c1b12f399429f30a7ca5236043  test-output.txt
```

The committed text matches the executed files. No hosted artifact was produced for this local synthetic run.

## Packet probe focused matrix

| Case | Losing behavior | Required behavior | Result |
| --- | --- | --- | --- |
| process name parser | split `/proc/PID/stat` at spaces in `(comm)` | parse names containing spaces and retain ppid/pgrp/session/starttime | PASS |
| live descendant | omit a helper that holds cwd/fd below temporary root | classify it as live with descendant and root-reference evidence | PASS |
| zombie | count a zombie as a live actor or lose it entirely | list it separately under zombie candidates | PASS |
| probe self-effect | count the synchronous probe child as an owned actor | label and exclude probe PID; retain atomic JSON only | PASS |
| atomic output | leave a partial receipt on interruption/failure | write a unique temporary file, fsync, and replace | PASS |

## Intended real integration

The probe must run synchronously in the mmdebstrap worker at two points using the same worker PID and temporary root:

```text
python3 archive_boundary_process_probe.py \
  --root "$MMDEBSTRAP_ROOT" \
  --worker-pid "$MMDEBSTRAP_WORKER_PID" \
  --phase after-setup \
  --output receipts/root-run-N-after-setup.json

python3 archive_boundary_process_probe.py \
  --root "$MMDEBSTRAP_ROOT" \
  --worker-pid "$MMDEBSTRAP_WORKER_PID" \
  --phase before-tar \
  --output receipts/root-run-N-before-tar.json
```

Repeat for root and chrootless from clean disposable state. The source integration edit remains absent pending exact review of the selected execution carrier.

## PR #395 live-head complete-diff review

Review record: [`LIVE_HEAD_REVIEW.md`](LIVE_HEAD_REVIEW.md).

All nine live changed paths were read. Two product blockers were confirmed:

1. the helper calls `utime($mtime, $mtime, $File::Find::name)`, assigning the epoch to directory access time and modification time;
2. path-based `lstat` followed by path-based `utime` retains the check-to-mutation replacement and authority gap.

The candidate test positively requires the two-epoch `utime` call and contains no directory-atime reversing control. The real metadata probe also lacks a directory-atime assertion.

### Exact current-head executions

| Run | Exact head/merge | Result |
| --- | --- | --- |
| Linux Fieldwork CI `30659899178` / 1099 | head `74c996394819c3a717d55193d84336c2e06b3b7c` | SUCCESS |
| dedicated workflow `30659899105` / 25, job `91253360438` | generated merge `a7fa7fe838e499ee52912c7be276cc89cfad4dec` | FAILURE |

Dedicated job step results:

| Step | Result |
| --- | --- |
| exact patch context, synthetic matrix, and product candidate | PASS |
| current Debian sid formatting | FAIL |
| exact product helper on real metadata matrix twice | SKIPPED |
| upload receipts | completed; no files found |

The sid container applied the retained patch exactly and `perl -c` passed. Whole-source `perltidy` comparison then failed:

```text
/tmp/.../mmdebstrap /tmp/mmdebstrap.tdy differ: char 1676, line 42
```

Classification: formatting-gate ownership failure. The live head has no real product-helper metadata receipt. PR #391's earlier artifact cannot be silently inherited as execution of PR #395's exact helper.

## Patch application and rebase

- packet branch base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- product patch application in this packet: NOT RUN
- probe source integration patch: NOT WRITTEN
- PR #395 live complete diff: REVIEWED; see `LIVE_HEAD_REVIEW.md`
- current upstream rebase: NOT RUN
- public upstream overlap: NOT SEARCHED in this pass

## Cleanup and rerun

The synthetic probe tests terminated live helper processes, reaped the zombie helper through its worker, removed temporary roots and receipt directories, and left no packet runtime residue. No mounts, sockets, containers, package roots, or imported-source changes were created by this packet pass.

The dedicated PR #395 job created no real-boundary receipt directory because execution stopped before the real metadata step. GitHub's artifact action reported no files found.

## Tests not run

- real root-mode mmdebstrap boundary snapshots;
- real chrootless-mode boundary snapshots;
- adjacent uninstrumented package result control;
- repeated clean executions at both phases;
- source integration patch application, syntax, and formatting;
- directory-atime losing control against PR #395;
- repaired access-time-preserving candidate execution;
- selected product candidate focused sid `chrootless` execution;
- immediate real package rerun;
- complete package matrix;
- current upstream native tests and current-base rebase;
- non-Linux behavior;
- no-tree-mutation archive compatibility matrix.

## Failure classification

The first local probe execution failed because the live-child test sampled `/proc` before the child announced that `chdir` and file open had completed. The harness was repaired with a readiness line from the child. The production probe logic was unchanged. The repaired command passed all four tests.

A later local test-edit attempt introduced an indentation error while replacing cleanup code; the file was repaired before the recorded hashes. No failing version was committed.

PR #395 dedicated run `30659899105` failed at whole-source sid formatting. That red result belongs to the formatting gate and prevented the real product-helper matrix from running.

## Final evidence statement

The packet probe can record the process identity signals demanded by issue #392, and its controls lose when live/zombie/self-exclusion behavior is wrong. Complete PR #395 review proves the live helper overwrites directory atime and still uses unsafe pathname authority. Real mmdebstrap quiescence and a winning product implementation remain unproved.
