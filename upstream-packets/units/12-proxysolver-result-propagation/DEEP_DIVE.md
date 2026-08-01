# Deep dive

## Question and observed failure

The bounded question is how `proxysolver` reports the completed real APT solver's result while preserving the output it forwards and retains.

The imported wrapper iterates over `p.stdout` and writes each line to its stdout and dump. `Popen.__exit__()` waits, yet the wrapper never inspects the result. A fake solver that emits a partial response and exits 7 therefore yields wrapper status 0. PR #134 added an explicit wait and `SystemExit(returncode)`. Python uses negative subprocess return codes for signal termination, so a SIGTERM child produces `-15`; `SystemExit(-15)` becomes ordinary exit 241. Both defects live in the wrapper's completed-child result decision.

## Source mechanism

The relevant path is compact:

1. validate `/usr/lib/apt/solvers/apt` and `APT_EDSP_DUMP_FILENAME`;
2. open the dump file;
3. start the real solver with inherited stdin and stderr, piped stdout, text mode, and no buffering;
4. forward each stdout line and retain the same line;
5. leave the subprocess and file contexts;
6. reach Python end-of-file.

The candidate records `p.wait()` after the forwarding loop. Context exit then closes the child and dump scopes. Positive values are raised as ordinary exits. Negative values are interpreted as signals, with stdout flushed before the wrapper replays the signal to itself.

## Reproduction narrative

A disposable fake solver consumes the EDSP request, records its PID, emits selected stdout and stderr, and either exits or signals itself. Temporary wrapper copies replace only the two hard-coded real-solver path literals.

Distinguishing results:

- baseline child exit 7: wrapper 0;
- composed candidate child exit 7: wrapper 7;
- ordinary-only child SIGTERM: wrapper 241;
- composed candidate child SIGTERM: parent observes `-15`;
- ordinary-only child SIGINT: wrapper 254;
- composed candidate child SIGINT: parent observes `-2`.

In every executed case, stdout equals the expected solution bytes, the dump equals stdout, stderr contains the inherited diagnostic, and the fake solver PID disappears.

## Approach history

### Approach A — propagate every nonzero value with `SystemExit`

- added explicit `p.wait()` and raised its return value;
- fixed positive exit 7 and preserved success 0;
- produced 241 for SIGTERM and 254 for SIGINT;
- accepted as the ordinary-status component through PR #134;
- superseded as a complete result contract.

### Approach B — map signals to `128 + signum`

- would produce familiar shell numbers such as 143 and 130;
- would make POSIX `WIFSIGNALED` false and lose exact signal termination;
- rejected because the selected contract is faithful child result identity.

### Approach C — close output, flush stdout, and replay the signal

- detects negative return codes;
- restores `SIG_DFL` and unblocks catchable signals;
- signals the wrapper itself after both context managers close;
- preserves actual signal termination and complete retained output;
- selected and retained by PR #207.

### Approach D — own wrapper cancellation while the solver runs

- would install wrapper signal handlers and forward termination to the child or process group;
- addresses a different timeline: parent interruption before child completion;
- excluded from this unit to keep ownership and review bounded.

## Selected correction

One patch adds the explicit completed-child result decision. The code treats positive and negative values according to Python's subprocess contract. Output closure happens before exact signal replay, and explicit stdout flushing covers the loss of normal interpreter-shutdown flushing.

## Why the changes belong together

The two historical patches touch the same source path and adjacent lines after the same wait. Shipping only the positive branch leaves a known misleading signal result. Shipping only the negative branch cannot apply without the explicit wait. One patch expresses one invariant: the wrapper reports the completed solver's result faithfully.

## Compatibility analysis

### Bytes and streams

- stdout content remains unchanged for success, positive failure, SIGTERM, and SIGINT;
- dump content remains identical to stdout;
- stderr stays inherited from the solver and is neither captured nor rewritten;
- explicit stdout flush can itself fail, which remains an output-path boundary.

### Status and signal

- 0 remains 0;
- positive exit 7 remains 7;
- SIGTERM and SIGINT are observed as actual signal termination;
- blocked SIGTERM inherited by the wrapper is unblocked before replay;
- SIGKILL and SIGSTOP skip handler restoration because they cannot be caught.

### Process and cleanup state

- `p.wait()` establishes child completion before result translation;
- dump closure occurs before self-signal;
- all fake solver PIDs disappeared in the executed matrix;
- Python code after `os.kill()` is unavailable as a cleanup path when the default action terminates the wrapper.

### Platform

- `signal.pthread_sigmask` is POSIX and used here for a Linux-specific helper;
- Windows and Python runtimes without this API remain outside the candidate contract.

## Negative controls and losing mutations

The detector loses against the exact imported baseline for exit 7. It also loses against the ordinary-only repair for SIGTERM and SIGINT, producing 241 and 254. Removing the unblock call loses the inherited blocked-SIGTERM case. Removing the explicit stdout flush previously lost piped stdout while the dump remained complete. These controls prevent an always-green result classifier.

## Current upstream and historical review

The public canonical listing observed on 2026-07-31 points main at `77ec9be5417ee44c96343d2347145585da1b1f94` and says `proxysolver` last changed in 2021. Public issue search surfaced no equivalent proxysolver result work. Linux Fieldwork PR #207's post-merge review accepted the narrow mechanism while holding public preparation for current-upstream composition, human policy review, and explicit acceptance or coverage of broader signal/output cases.

## Remaining questions

1. **Exact upstream source identity:** materialize commit `77ec9be5417ee44c96343d2347145585da1b1f94` and compare `git hash-object proxysolver` with `5cd51fab89104d30b8b12bff18a49d38d9be0003`.
2. **Native-context gate:** apply the composed patch in that checkout and run the packet regression from the checkout boundary.
3. **Project-native placement:** decide whether the focused regression belongs in upstream `tests/`, `coverage.py`, or a smaller accepted harness.
4. **Signal policy review:** obtain human acceptance of exact replay, Linux/POSIX dependency, and stdout-flush failure precedence.

## Evidence boundary

The dynamic matrix ran on Linux x86_64, kernel 6.12.13, Python 3.13.5, and GNU patch 2.8 without privilege, APT transactions, mounts, network, or persistent process state. It uses exact imported source and a fake solver. It does not invoke the real APT solver, materialize the current upstream checkout, run mmdebstrap's full coverage suite, or establish parent-interruption ownership.

## Reopen triggers

- current upstream `proxysolver` differs from imported blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`;
- an active equivalent upstream issue or pull request appears;
- upstream rejects exact signal replay or `pthread_sigmask`;
- a native test reveals different buffering, descriptor, or signal behavior;
- external-contact authorization changes.
