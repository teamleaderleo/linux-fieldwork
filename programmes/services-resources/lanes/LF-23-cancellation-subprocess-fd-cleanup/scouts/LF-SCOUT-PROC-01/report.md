# LF-SCOUT-PROC-01 — Cancellation, subprocess, and descriptor cleanup

## In simple words

Three process-group interruptions behaved cleanly: before worker launch, while the worker had live mounts and IPC, and during final cleanup. Every interrupted run failed, every process group emptied, mounts and sockets disappeared, temporary roots were removed, and every immediate rerun succeeded.

A narrower probe found a promotion candidate in the exact imported `run_progress()` function. When only the process running `run_progress()` received `SIGTERM`, the function logged the interruption, waited for its child, returned normally, and the driver exited `0`. The interruption was therefore reported as success.

## Scout identity and home lane

- Scout-ID: `LF-SCOUT-PROC-01`
- Home lane: `LF-23`
- Assignment: issue `#12`
- Working branch: `scout/lf-scout-proc-01/lf-23-cancellation-cleanup`
- Pull request: `#16`
- Reviewer: `LF-SCOUT-ROOT-01`
- Cross-review completed: `LF-SCOUT-DEB-01` on LF-07, issue `#13`, PR `#18`

## Exact source or package boundary

The tested implementation is the repository import:

- path: `upstream/mmdebstrap/mmdebstrap`
- imported version family: `mmdebstrap` 1.5.7
- retained byte count: `404152`
- retained SHA-256: `836cfb54c804494e109646050e069a6cf752b746660b7ae5ed6bb4a6494eac75`

The harness reads that file at runtime and creates temporary instrumented copies under its output directory. It leaves the imported source unchanged. Every insertion uses an exact source marker and aborts when the marker count differs from one.

The required matrix covers top-level orchestration in root mode with a custom, empty, dry-run workload and null output. The targeted promotion probe calls the exact imported `run_progress()` function through a temporary driver and supplies a deterministic sleeping child.

## Environment and privileges

The retained run was GitHub Actions run `30515323482`, job `90783738451`, in a privileged `debian:sid-slim` container on `ubuntu-24.04`.

- Debian GNU/Linux forky/sid container userspace
- Linux `6.17.0-1020-azure`, x86-64
- uid/euid/gid/egid `0`
- Perl `5.42.2`
- Python `3.14.6`
- apt `3.3.1`
- dpkg `1.23.7`
- GNU tar `1.35`

Privilege was required to exercise root-mode setup and mounts. At the active-worker checkpoint, the worker root had live `devpts` and `tmpfs` mounts at `dev/pts` and `dev/shm`.

## Source and test map

### Top-level process tree

The parent creates three communication channels before worker launch:

- a pipe carrying output data toward the output child;
- a Unix socketpair used by the hook listener and worker;
- a pipe used for block-count or status communication.

It then creates the worker and hook-listener children, and may create an output child according to format. Signals `INT`, `HUP`, `PIPE`, and `TERM` are blocked across creation. Worker-side code restores default handlers and unblocks those signals. The parent records a received signal while waiting for setup or cleanup and converts that state into failure after children and output are handled.

### Temporary root, lock, mounts, and cleanup

For null or archive-like output, the parent creates a temporary root under `TMPDIR`, opens the directory, and holds an exclusive `flock` on that descriptor. Worker setup builds a LIFO list of mount and filesystem cleanup callbacks. Its signal handler runs those callbacks and exits with failure. The parent later removes the temporary root with a one-filesystem, preserve-root-aware removal command.

The active-worker checkpoint sits immediately after `setup_mounts()` returns. This gives the probe a stable point with the worker, hook listener, root lock, pipes, Unix socketpair, and root mounts alive.

### `run_progress()` signal path

`run_progress()` blocks the same signal set around child creation. Its command child restores defaults and unblocks signals. Its progress child ignores signals. The owning process installs a handler that logs the signal while waiting for the child.

A separate lexical signal variable is checked after the child wait, yet the installed handler does not assign that variable. The targeted probe distinguishes this path by signaling only the owning PID, allowing the child to finish, and checking whether the function returns normally.

### Output and partial-result boundary

The required matrix uses `--format=null` and `/dev/null`, so any interrupted run must fail without leaving an output path. The targeted `run_progress()` driver writes a success marker only after the exact function returns. That marker distinguishes a swallowed interruption from a propagated failure.

## Probe design and distinguishing outcomes

The reusable harness is `artifacts/cancellation_harness.py`. Each case receives a fresh process group, run directory, and `TMPDIR`.

Required command path:

```sh
perl upstream/mmdebstrap/mmdebstrap \
  --mode=root \
  --variant=custom \
  --format=null \
  --dry-run \
  --customize-hook=true \
  --skip=check/signed-by,update \
  '' /dev/null
```

The no-op customize hook makes the custom variant enter `setup_mounts()`; dry-run keeps package acquisition and hook execution out of scope.

Required interruption cases:

1. `before-child-launch` — after pipes, socketpair, temporary root, and root lock exist; before worker fork.
2. `active-worker` — inside the worker after `setup_mounts()` returns.
3. `cleanup` — in the parent after setup and output processing, immediately before final temporary-root removal.

For each case, the harness:

1. waits for the exact checkpoint;
2. captures process-group members, command lines, status, descriptors, mountinfo, `/proc/locks`, and `ss -ap`;
3. sends `SIGTERM` to the process group;
4. captures the same state shortly after the signal;
5. waits for exit and captures the final state;
6. records temporary paths and exit status;
7. runs the original, uninstrumented source again with a new `TMPDIR`.

A clean cancellation requires a non-zero interrupted exit, an empty process group after exit, no retained temporary paths, and a successful clean rerun.

The targeted `run_progress-parent-only` case starts the exact imported function with a deterministic child, waits until the owner has installed its handler, sends `SIGTERM` only to the owner PID, and records the log, return status, success marker, process group, and rerun.

## Commands or scripts

Run the harness from the repository root:

```sh
python3 programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/scouts/LF-SCOUT-PROC-01/artifacts/cancellation_harness.py
```

The dedicated workflow is `.github/workflows/lf-23-cancellation.yml`. It runs the harness in a disposable privileged Debian sid container and uploads the complete per-process evidence tree.

The durable retained subset is under `artifacts/retained-run-30515323482/`.

## Observed results

| Case | Signal scope | PIDs before | Live resources before | Interrupted exit | State after exit | Clean rerun |
|---|---|---:|---|---:|---|---:|
| `before-child-launch` | process group | 1 | root flock, two pipes, Unix socketpair, root FD | 25 | 0 PIDs; no locks, sockets, mounts, or temp paths | 0 |
| `active-worker` | process group | 3 | root flock, pipes, Unix socketpair, `dev/pts` and `dev/shm` mounts | 25 | 0 PIDs; no locks, sockets, mounts, or temp paths | 0 |
| `cleanup` | process group | 1 | root flock and root FD | 25 | 0 PIDs; no locks, sockets, mounts, or temp paths | 0 |
| `run-progress-parent-only` | owner PID only | 4 | owner, command child, progress child, sleeping grandchild, progress pipes | **0** | 0 PIDs | 0 |

### Required matrix

All three required interruptions logged the signal in the relevant phase and ended with failure. The active worker ran its signal cleanup callback, the two target mounts vanished before the parent exited, the hook socket disappeared, and the parent removed the temporary root. The final process-group snapshot was empty for every case.

All three immediate reruns of the original source completed successfully in approximately 0.14 seconds and left no paths in their per-run `TMPDIR`.

### Promotion candidate

The parent-only `run_progress()` case logged:

```text
I: run_progress() received signal TERM: waiting for child...
```

The child then completed, `run_progress()` returned, the driver wrote `run-progress-returned`, and the process exited `0`. The process group eventually emptied and a clean rerun also exited `0`. Resource cleanup succeeded while cancellation semantics failed.

## Interpretation

Top-level process-group cancellation is coherent for the tested phases. The parent records interruption, workers receive the group signal, worker cleanup unwinds mounts, the hook listener loses its socket cleanly, the root lock closes, and temporary-root removal finishes before failure is reported.

The targeted function-level result is different. `run_progress()` handles an owner-only `SIGTERM` as a status message, waits for successful child completion, and returns success. A caller or supervisor that signals only the mmdebstrap PID during a `run_progress()` operation can therefore receive a successful result even though cancellation was requested.

This is a promotion candidate because the behavior is deterministic, tied to the exact imported source, and distinguishes cleanup success from cancellation-reporting success. The next probe should reproduce it through a full mmdebstrap operation that spends controlled time inside a real `run_progress()` caller, then check output and transaction state.

## Evidence limits

- The required matrix uses an empty suite, custom variant, dry-run, skipped update, and null output.
- `dev/pts` and `dev/shm` were live in the active-worker case; `/proc` and `/sys` mounts were skipped because those target directories were absent in this dry-run root.
- Package download, extraction, dpkg execution, maintainer scripts, service actions, network activity, and archive creation are outside this run.
- Null output proves absence of a retained output path in the required matrix. It does not measure truncation or corruption of a real tar stream.
- The `run_progress()` promotion probe is function-level. It uses the exact imported function and real fork/pipe/signal behavior, with a purpose-built child command.
- Owner-only signaling represents supervisors that target one PID. Terminal process-group signaling follows the clean required-matrix path tested here.
- Snapshots are discrete `/proc` observations. The final group scans and clean reruns provide the durable orphan check.
- The workflow artifact retains complete raw snapshots for 14 days; the compact durable subset remains in the branch.

## Promotion or stop decision

**Decision: `promote`.**

Promote the `run_progress()` parent-only signal result to a deeper full-operation probe. Retain the three clean process-group cases as controls. Any external defect report requires the broader reproduction, output classification, and assigned upstream authority.

## Upstream authority state

No upstream contact is authorized. No external issue, email, patch, merge request, or maintainer interaction was made.
