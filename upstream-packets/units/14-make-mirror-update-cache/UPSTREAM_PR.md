# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: canonical mmdebstrap Forgejo repository  
Proposed base branch: `main`  
Candidate branch or patch series: `NEEDS FORK` / `NEEDS BRANCH`; retained patch `patches/0001-update-cache-worker-lifecycle.patch`  
External contact authorized: `false`

## Proposed title

`make_mirror.sh: make update_cache cleanup worker-owned and signal-safe`

## Draft

### Summary

This change confines `update_cache()` cleanup to worker-owned APT state and routes every worker result through one finalizer. INT, QUIT, and TERM return 130, 131, and 143. The first handled signal arriving during ordinary cleanup is retained while later handled signals are ignored until bounded cleanup completes. Existing command or explicit-signal failure remains authoritative, followed by a cleanup-time signal, cleanup failure, and success.

### Before

`update_cache()` runs in a pipeline subshell but installs one `EXIT INT TERM` trap that kills `$PROXYPID` and calls `cleanupapt`. `$PROXYPID` belongs to the top-level shell. A worker-only signal can therefore kill the wrong owner's process, resume later work, return status 0, and run cleanup again through EXIT.

A simple terminating finalizer closes those failures but, when handled signals are restored to default before cleanup, a signal during cleanup can interrupt cleanup or a later signal can replace an already selected result.

### After

The worker cleans its APT root once and leaves proxy stop/wait to the top-level owner. Ordinary failure, implicit EXIT, explicit INT/QUIT/TERM, ordinary success, cleanup failure, and cleanup-time signals converge through the same result selection. Bounded cleanup completes after the first handled cleanup-time signal, and immediate reruns start from clean worker state.

### Implementation

- add a worker-local cleanup-signal status slot;
- record only the first cleanup-time INT/QUIT/TERM and ignore later handled signals;
- centralize APT cleanup and result selection in `update_cache_finish()`;
- preserve implicit EXIT `$?`;
- make explicit INT/QUIT/TERM handlers select 130/131/143 and terminate through the finalizer;
- remove `$PROXYPID` signaling from the worker;
- route successful completion through `update_cache_finish 0` instead of direct cleanup followed by trap clearing.

The complete result order is:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

### Tests

Retained real-`/bin/sh` regressions on the exact current source blob establish:

- baseline worker-only TERM returns 0, executes later work, cleans twice, and kills the parent-owned proxy;
- candidate INT/QUIT/TERM return 130/131/143 through the parent pipeline;
- worker cleanup runs once and the parent alone stops/reaps the proxy;
- ordinary failure 42 and explicit TERM 143 outrank cleanup failure 74;
- successful work plus cleanup failure returns 74;
- predecessor cleanup-time signals interrupt cleanup or replace the first result;
- candidate retains the first cleanup-time signal, ignores later handled signals, completes cleanup, removes APT state, and omits later work;
- immediate unsignaled reruns succeed;
- the two provenance patches apply with zero fuzz and the complete source passes `/bin/sh -n`.

Exact Linux Fieldwork receipts:

- CI `30624335126` / 842 for the ownership/finalizer repair;
- CI `30630467076` / 916 for the cleanup-time signal successor and full retained matrix.

The collapsed one-patch carrier still needs full-tree application, shell syntax, and the selected upstream-native gate on a controlled upstream branch.

### Compatibility

The change adds no external command, package dependency, process group, or supervisor. APT command order and proxy launch behavior stay unchanged. Cleanup is treated as bounded and allowed to finish after the first handled signal. Prompt descendant cancellation, HUP, escalation, hostile descendants, and permanently blocking cleanup remain outside this pull request.

### Related issue

No upstream issue is currently selected. The pull request can carry the complete reproducer and evidence unless upstream practice requires issue-first discussion.

## Proposed commits or patch order

1. `make_mirror.sh: make update_cache cleanup worker-owned and signal-safe`

## Reviewer notes

The subtle point is ownership plus precedence. The pipeline worker owns `$newcachedir/apt`; the top-level shell owns `$PROXYPID`. Cleanup-time signal recording occurs before EXIT is cleared, and handled signals are ignored after a result is selected so bounded cleanup can complete without replacing the first result.

## Submission checklist

- [x] Current upstream base commit and source blob pinned.
- [x] Complete internal component diffs reviewed.
- [x] Baseline regressions fail and component candidates pass.
- [x] Cleanup and immediate rerun pass in retained matrices.
- [x] Indexed active equivalent work searched on 2026-07-31.
- [x] Draft contains no Linux Fieldwork routing links or private data in the proposed external body.
- [ ] Controlled fork and branch created.
- [ ] Collapsed patch applied to the full upstream tree with zero fuzz/offset.
- [ ] `/bin/sh -n make_mirror.sh` passed on the collapsed candidate.
- [ ] Upstream-native focused test passed.
- [ ] Complete one-file upstream diff reviewed.
- [ ] Live overlap rechecked immediately before submission.
- [ ] Explicit authorization recorded.
- [ ] Public PR and exact submitted head recorded after submission.
