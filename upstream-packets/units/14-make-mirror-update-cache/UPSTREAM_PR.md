# Upstream pull request draft

Status: `DRAFT — technically complete; authorization and canonical delivery route pending`  
Proposed destination: canonical mmdebstrap Forgejo repository  
Proposed base branch: `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`  
Controlled candidate: `teamleaderleo/mmdebstrap` branch `linux-fieldwork/unit-14-make-mirror-update-cache-upstream-main`, head `76728bbb8e084b54261713ba80762cd6f6ada79a`  
External contact authorized: `false`

## Proposed title

`make_mirror.sh: make update_cache cleanup worker-owned and signal-safe`

## Draft

### Summary

This change confines `update_cache()` cleanup to worker-owned APT state and routes every worker result through one finalizer. INT, QUIT, and TERM return 130, 131, and 143. The first handled signal arriving during ordinary cleanup is retained while later handled signals are ignored until bounded cleanup completes. Existing command or explicit-signal failure remains authoritative, followed by a cleanup-time signal, cleanup failure, and success.

A focused native regression is registered in `coverage.txt`. It extracts the actual candidate functions from `make_mirror.sh` and executes real shell signals, cleanup barriers, precedence cases, state removal, and a clean rerun.

### Before

`update_cache()` runs in a pipeline subshell but installs one `EXIT INT TERM` trap that kills `$PROXYPID` and calls `cleanupapt`. `$PROXYPID` belongs to the top-level shell. A worker-only signal can therefore kill the wrong owner's process, resume later work, return status 0, and run cleanup again through EXIT.

A simple terminating finalizer closes those failures but, when handled signals are restored to default before cleanup, a signal during cleanup can interrupt cleanup or a later signal can replace an already selected result.

### After

The worker cleans its APT root once and leaves proxy stop/wait to the top-level owner. Ordinary failure, implicit EXIT, explicit INT/QUIT/TERM, ordinary success, cleanup failure, and cleanup-time signals converge through the same result selection. Bounded cleanup completes after the first handled cleanup-time signal, and immediate reruns start from clean worker state.

The result order is:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

### Implementation

- add a worker-local cleanup-signal status slot;
- record only the first cleanup-time INT/QUIT/TERM and ignore later handled signals;
- centralize APT cleanup and result selection in `update_cache_finish()`;
- preserve implicit EXIT `$?`;
- make explicit INT/QUIT/TERM handlers select 130/131/143 and terminate through the finalizer;
- remove `$PROXYPID` signaling from the worker;
- route successful completion through `update_cache_finish 0`;
- register `tests/make-mirror-update-cache-worker-lifecycle` in `coverage.txt`.

### Tests

The final controlled candidate is two commits over exact canonical Forgejo `main`, zero commits behind. The complete diff contains three paths:

- `make_mirror.sh`: +46/-6;
- `coverage.txt`: +2;
- `tests/make-mirror-update-cache-worker-lifecycle`: +261.

Executed on the exact canonical-ancestry candidate:

- zero-fuzz patch dry-run and application;
- `/bin/sh -n make_mirror.sh`;
- `git diff --check`;
- source ownership assertions excluding `$PROXYPID` from `update_cache()`;
- ten candidate-facing lifecycle tests: all passed in 3.459 seconds;
- native test `sh -n`;
- native test shellcheck with the project's exclusions;
- native test shfmt with the project's options;
- direct native regression execution: `make_mirror update_cache worker lifecycle: PASS`;
- complete two-commit, three-path diff review.

The matrix covers:

- baseline false success, later work, duplicate cleanup, and wrong-owner proxy termination;
- INT/QUIT/TERM results 130/131/143;
- one worker cleanup and parent-only proxy ownership;
- ordinary failure 42 over cleanup failure 74;
- explicit TERM 143 over cleanup failure and later INT;
- cleanup-time signal over cleanup failure;
- first cleanup-time signal retention and later-signal suppression;
- APT-state removal, absence of later work, and immediate clean rerun.

A complete mirror generation was deliberately omitted from the focused gate because it requires network and package/mirror state unrelated to the shell lifecycle discriminator. The native regression runs without root, APT, QEMU, or network access.

### Compatibility

The product change adds no external command, package dependency, process group, or supervisor. APT command order and top-level proxy launch behavior stay unchanged. Cleanup is treated as bounded and allowed to finish after the first handled signal. Prompt descendant cancellation, HUP, escalation, hostile descendants, and permanently blocking cleanup remain outside this pull request.

The regression uses Python's standard library inside the project's shell-test convention. The project test runner is already Python-based; this adds no product runtime dependency.

### Related issue

No upstream issue is selected. The pull request contains the complete reproduction and evidence unless project practice requires issue-first discussion.

## Proposed commits

1. `make_mirror: make update_cache cleanup worker-owned`
2. `tests: cover make_mirror update_cache worker lifecycle`

## Reviewer notes

The subtle point is ownership plus precedence. The pipeline worker owns `$newcachedir/apt`; the top-level shell owns `$PROXYPID`. Cleanup-time signal recording is installed before EXIT is cleared, and handled signals are ignored after a result is selected so bounded cleanup can complete without replacing the first result.

## Submission checklist

- [x] Current canonical upstream history cloned and mirrored to the controlled repository.
- [x] Exact base commit and source blob pinned.
- [x] Composed source patch applied with zero fuzz.
- [x] Shell syntax and diff hygiene passed.
- [x] Baseline negative controls and exact-candidate dynamic matrix passed.
- [x] Upstream-native test registered and passed formatting/direct execution gates.
- [x] Cleanup and immediate rerun passed.
- [x] Complete two-commit, three-path candidate diff reviewed.
- [x] Draft contains no private credentials or Linux Fieldwork routing in the proposed external body.
- [ ] Live canonical overlap receipt reviewed and any keyword match classified.
- [ ] Canonical Forgejo-compatible fork/branch or accepted patch route created.
- [ ] Explicit authorization recorded.
- [ ] Public submission and exact submitted identity recorded.
