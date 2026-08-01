# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: canonical mmdebstrap Forgejo repository  
Proposed base branch: `main`  
Candidate branch or patch series: `NEEDS FORK` / `NEEDS BRANCH`  
External contact authorized: `false`

## Proposed title

proxysolver: preserve solver exit and signal results

## Draft

### Summary

This change makes `proxysolver` report the completed APT solver's result faithfully after forwarding and retaining its output.

The wrapper now waits explicitly after draining solver stdout. Positive child failures become the same wrapper exit code. Signal-derived negative return codes cause the wrapper to flush stdout, restore and unblock the signal, and terminate by that same signal after the subprocess and dump-file contexts close.

### Before

A solver that emitted a partial response and exited 7 left the wrapper at status 0. An ordinary-status-only repair using `SystemExit(returncode)` converted solver SIGTERM into ordinary wrapper exit 241 and SIGINT into 254.

### After

- solver exit 0 leaves wrapper status 0;
- solver exit 7 leaves wrapper status 7;
- solver SIGTERM leaves the wrapper terminated by SIGTERM;
- solver SIGINT leaves the wrapper terminated by SIGINT;
- stdout and dump content remain identical;
- solver stderr remains inherited;
- an inherited blocked SIGTERM is unblocked before replay;
- completed fake solver processes are gone.

### Implementation

The source records `p.wait()` after stdout forwarding. For a negative return code, it flushes wrapper stdout, derives the signal number, restores the default disposition and unblocks catchable signals, then signals itself. Positive nonzero values use `SystemExit(returncode)`.

The result decision belongs in one patch because signal handling depends on the explicit wait and occupies the same adjacent source path as positive status propagation.

### Tests

The retained focused regression uses disposable exact source copies and a fake solver with independently controlled stdout, stderr, ordinary exit, and signal termination. It covers exit 0, exit 7, SIGTERM, SIGINT, inherited blocked SIGTERM, output/dump equality, stderr passthrough, source assertions, compilation, and child cleanup. The five-test matrix passed twice and passed again from a simulated repository layout.

Before submission, record the exact current-upstream candidate head and replace this paragraph with gates executed in that checkout. The full upstream coverage suite and package gates remain unexecuted.

### Compatibility

The success and positive failure contracts remain numeric. Signals remain signals. The exact replay path uses POSIX `pthread_sigmask`, fitting this Linux helper. An outer supervisor can translate the signal. A failure while explicitly flushing wrapper stdout can replace the signal result. Parent interruption while the solver is still running remains outside this change.

## Proposed commits or patch order

1. `proxysolver: preserve solver exit and signal results`

## Reviewer notes

Please review the exact signal replay policy, Linux/POSIX dependency, output-closure ordering, and the explicit stdout-flush failure boundary. The patch deliberately leaves wrapper-interruption/process-group ownership outside scope.

## Submission checklist

- [ ] Candidate rebased onto current intended upstream base.
- [ ] Complete upstream diff reviewed.
- [x] Baseline regression loses and local composed candidate passes.
- [ ] Upstream-native focused tests pass.
- [x] Cleanup and immediate rerun pass in the retained local matrix.
- [x] Public active equivalent work searched on 2026-07-31; no match surfaced.
- [ ] Fork and candidate branch exist.
- [x] Draft contains no credentials or private data.
- [ ] Explicit authorization recorded.
- [ ] Public reference and exact submitted head recorded after submission.
