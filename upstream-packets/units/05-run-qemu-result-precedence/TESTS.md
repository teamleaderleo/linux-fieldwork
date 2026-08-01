# Tests and receipts — unit 05

## Exact candidate

Date: 2026-08-01  
Controlled repository: `teamleaderleo/mmdebstrap`  
Base: `574048f2a720057b75e56622003932f344dc700a`  
Candidate branch: `linux-fieldwork/unit-05-run-qemu-result-precedence`  
Candidate head: `6efe6945f9f89cff57fe84086ede7bda747c3879`

| Identity | Value |
| --- | --- |
| Base `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Base bytes | 2,029 |
| Base SHA-256 | `da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300` |
| Candidate `run_qemu.sh` blob | `1fc816d6fe982351f6519fd1458329112eebdcfb` |
| Candidate bytes | 3,095 |
| Candidate SHA-256 | `434e7b6b9c32e30b506ea6af121608414c42b668c329e6395e75e19dc09ff276` |
| Compare | five ahead, zero behind, one file, 64 additions, 10 deletions |

## Ordered application and syntax

Patches 1–4 applied to the exact base with `git apply --check` and `git apply`, all status 0. The four-commit result passed `/bin/sh -n` and matched controlled fork blob `3e8d4dc07f91d246a372749eb49ff9489c21c7b7`.

Patch 5 is retained at:

```text
patches/0005-close-signal-handler-setup-windows.patch
blob f7e906d915c34db6e7546e4a9b1e4024e19d98d1
```

The exact fifth-commit source passed `/bin/sh -n` and is GitHub blob `1fc816d6fe982351f6519fd1458329112eebdcfb`.

## Controlled-fork lifecycle matrix

Execution: real `/bin/sh` reduced fixtures, disposable directories, real PID-targeted INT/TERM delivery.

Result:

```text
58 passed
0 failed
```

The matrix covers:

- baseline host failure overwritten by guest failure;
- host, guest, malformed/missing guest, cleanup failure, and success selection;
- baseline explicit INT/TERM guest-dependent results and cleanup re-entry;
- repaired explicit 130/143 results and once-only cleanup;
- first explicit signal through competing signals;
- ordinary cleanup signal retention;
- completed guest before later cleanup signal;
- signal before cleanup failure;
- cleanup completion and immediate clean rerun.

Raw receipt: [`artifacts/2026-08-01-controlled-fork-lifecycle-matrix.txt`](artifacts/2026-08-01-controlled-fork-lifecycle-matrix.txt).

## Preliminary fixture interruptions

Two preliminary harness runs were excluded from product evidence:

1. A synchronization barrier was awaited before sending the signal that enters cleanup.
2. Ordinary baseline EXIT cleanup was incorrectly expected to re-enter; re-entry belongs to the explicit-signal baseline path.

Failure owner: fixture/classifier. Product code stayed unchanged. The corrected authoritative matrix is the 58/58 result above.

## Complete-diff handler setup-window review

### Four-commit losing controls

| Context | Exact event order | Observed | Required | Result |
| --- | --- | ---: | ---: | --- |
| Explicit handler entry | TERM, then INT before trap replacement | 130 | 143 | fail on head `457095c6…` |
| Ordinary EXIT entry | completed guest 1, then TERM before recorder installation | 143 | 1 | fail on head `457095c6…` |

Both losing fixtures completed cleanup. The failure is precedence ownership.

### Fifth-commit repaired controls

| Context | Exact event order | Observed | Required | Cleanup |
| --- | --- | ---: | ---: | --- |
| Explicit handler entry | TERM, then INT during delayed trap action | 143 | 143 | `rm`, `rmdir`; tmpdir removed |
| Ordinary EXIT entry | completed guest 1, then TERM during delayed setup | 1 | 1 | `rm`, `rmdir`; tmpdir removed |
| First writer across transition | early TERM, recorder installation, later INT | 143 | 143 | `rm`, `rmdir`; tmpdir removed |

Raw receipt: [`artifacts/2026-08-01-handler-setup-window-repair.txt`](artifacts/2026-08-01-handler-setup-window-repair.txt).

## Checked-in regression ownership

New module:

```text
tests/test_run_qemu_handler_setup_windows.py
Git blob: a58eb89029729a89208c72e30164bcfe3c0aa139
```

It retains the old losing controls, repaired controls, first-writer transition case, cleanup assertions, and source contract.

The exact module was reviewed from the branch. Equivalent fixtures executed in this pass. Running the checked-in module through a complete checkout or hosted CI remains queued because this runtime cannot fetch the repository through its GitHub network endpoint.

## Historical exact-head execution

Historical four-patch composition PR #319:

```text
head: 2fe3f99364df29de217536dc35a4d03b10f49640
merge: b196d6b45f496d8eb2d763922532ad257f24bba8
CI run: 30628645668
job: 889
result: success
repository tests: 276 passed
```

That run owns the historical five focused modules. It does not validate the later fifth commit by itself.

## Project-native test mapping

mmdebstrap `README.md` documents:

```sh
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh
```

Individual tests can run through `coverage.py`. Its QEMU classification executes:

```text
./run_qemu.sh
```

Therefore the authoritative integration gate is a current canonical checkout with prepared mirror/cache and QEMU capability, running the relevant QEMU-classified cases on the exact rebased candidate.

## Behavior matrix selected by the candidate

| Earlier authoritative result | Later event | Final result |
| --- | --- | --- |
| host timeout 124 | guest failure | 124 |
| host failure 42 | malformed/missing guest | 42 |
| explicit INT | later handled signal or guest outcome | 130 |
| explicit TERM | later handled signal or guest outcome | 143 |
| completed guest failure | later cleanup signal | 1 |
| guest success | first cleanup signal | 130 or 143 |
| guest success | cleanup signal then cleanup failure | signal result |
| host and guest success | cleanup failures | first cleanup failure |
| all success | none | 0 |

## Cleanup and rerun

Demonstrated in reduced fixtures:

- later cleanup actions run after the first cleanup failure;
- repaired signal cases execute `rm` then `rmdir`;
- repaired successful cleanup removes the temporary directory;
- later workload after explicit cancellation does not run;
- immediate rerun succeeds and cleans its own temporary directory.

No mount, image, network service, credential, or external system state was created.

## HOLD gates

1. Resolve current canonical Salsa `master` and live `run_qemu.sh` identity.
2. Search current Salsa issues, branches, and merge requests for equivalent work.
3. Rebase/restack the five logical changes on that exact canonical head.
4. Execute `tests/test_run_qemu_handler_setup_windows.py` from a complete checkout or hosted CI.
5. Run current mmdebstrap QEMU-classified focused and ordinary project tests.
6. Clean the checkout and rerun focused controls on the exact final candidate.
7. Refresh the final merge-request draft with exact commands and run identities.

The user has no local fetch or test command to perform.
