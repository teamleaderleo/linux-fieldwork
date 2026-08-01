# Deep dive

## Question and observed failure

The bounded question is whether the top-level `make_mirror.sh` process owns cancellation, both proxy children, private cache deletion, QEMU temporary cleanup, and active-cache preservation across the complete top-level lifecycle.

The imported source installs cleanup-only actions for ordinary exit and signals:

```sh
./caching_proxy.py "$oldcachedir" "$newcachedir" &
PROXYPID=$!
trap 'kill "$PROXYPID" || :' EXIT INT TERM
...
trap 'kill "$PROXYPID" || :;cleanup_newcachedir' EXIT INT TERM
```

The QEMU path installs another cleanup-only action. A shell signal handler returns to interrupted control flow unless it exits or re-raises. For parent-PID-only delivery while the shell waits for a foreground command, the shell can defer the handler, perform cleanup after the foreground command returns, and continue later mirror work. The baseline reduced harness recorded later work, a second EXIT cleanup, and status 0 after TERM.

The top-level owner also used raw `kill` without an asserted `wait`, and both proxy launches created a child before storing `$!`. A signal accepted in either launch/registration interval could run cleanup while the newly created proxy still lacked an owned PID.

These are product-owner defects. The losing baseline uses the exact trap form from `make_mirror.sh`, and the candidate tests extract the exact patched functions and traps from a patched complete source copy. Earlier carrier defects were classified separately as patch hunk, fixture path, assertion, and ownership-model errors.

## Source mechanism

The relevant source path is:

1. startup preflight chooses `oldcache` and `newcache`, removing an abandoned alternate cache only when both cache directories exist and the active symlink identifies the survivor;
2. the top-level shell starts `caching_proxy.py` and records `PROXYPID` in a separate command;
3. readiness checks run before the new cache marker is created;
4. after readiness, the shell owns failed-private-cache cleanup;
5. `update_cache()` workers run in pipeline subshells while the top-level proxy remains parent-owned;
6. the first proxy stops before publication work continues;
7. the QEMU path starts a readonly proxy with the same two-step launch/registration sequence;
8. QEMU temporary files become top-level cleanup state;
9. the second proxy stops, QEMU temporary state is cleaned, and the cache is eventually selected through `shared/cache`.

The candidate gives each state transition an explicit owner:

- `PROXYPID` identifies the one currently owned top-level proxy;
- `PENDING_SIGNAL` retains the first signal accepted during proxy registration;
- `CLEANUP_PROXY_CACHE` begins as `no`, becomes `yes` only after first readiness, and returns to `no` when the cache is observed as published;
- `CLEANUP_TMPDIR` identifies active QEMU temporary state;
- `stop_proxy()` handles signal, wait, and PID clearing;
- `cleanup_owner()` invokes state-specific cleanup once;
- `signal_exit()` clears traps, cleans, and exits with 130, 131, or 143;
- `launch_proxy()` keeps temporary launch handlers active until the child PID is owned and any retained signal has been dispatched.

## Reproduction narrative

The smallest primary reproducer starts a long-lived child, installs either the baseline trap or candidate lifecycle, enters a foreground wait, and receives TERM at the owner PID only. A marker after the wait detects continuation. Cleanup counters detect duplicate cleanup, and PID checks detect an unreaped or surviving child.

Baseline:

- TERM is deferred while the foreground child runs;
- cleanup kills the proxy;
- the trap returns;
- later work executes;
- ordinary EXIT invokes cleanup again;
- final status is 0.

Candidate:

- TERM reaches `signal_exit 143` after shell delivery;
- traps are cleared;
- owner cleanup runs once;
- proxy is signaled and waited;
- later work remains absent;
- final status is 143.

The launch-window matrix stops the owner at deterministic points around child creation and PID assignment. It delivers TERM before registration, then releases the owner. A competing-signal case delivers INT after assignment but before ordinary trap restoration. The retained first TERM remains authoritative, producing 143.

Two ownership states are modeled separately:

- first launch before readiness: cache-deletion ownership is `no`; owner cleanup and proxy stop occur, retained cache state survives signal-time cleanup, and the immediate rerun's startup preflight removes it;
- second launch during QEMU: cache-deletion ownership is `yes`; owner cleanup stops the proxy and removes private cache state.

## Approach history

### Approach A — reuse one cleanup-only trap for EXIT and signals

- mechanism: retain the original shared `EXIT INT TERM` action;
- evidence: exact baseline reduced harness;
- result: TERM cleanup returns to shell flow, later work runs, EXIT cleanup repeats, and status becomes 0;
- compatibility cost: cancellation becomes false success or a later unrelated failure;
- disposition: rejected.

### Approach B — terminate after cleanup and wait for the proxy

- mechanism: split ordinary EXIT cleanup from INT/QUIT/TERM, add `stop_proxy()`, cleanup flags, and `signal_exit STATUS`;
- evidence: PR #159 exact-head matrix and PR #205 current-main restack;
- result: correct signal statuses, once-only cleanup, proxy reaping, successful rerun, and active-cache preservation;
- compatibility cost: ordinary primary failure now remains authoritative when cleanup also fails; retained state can remain after cleanup failure;
- disposition: accepted as the parent repair, then superseded as the complete top-level candidate after launch-window review.

### Approach C — delete the new cache at every normal proxy stop

- mechanism: make `stop_proxy()` also perform failed-cache cleanup;
- evidence: source-order review before CI;
- result: the first normal pre-publication stop would delete a successfully constructed candidate cache;
- compatibility cost: destroys intended output on success;
- disposition: rejected. Proxy shutdown and cache deletion remain separate operations.

### Approach D — infer private-cache status only from an ownership flag

- mechanism: leave `CLEANUP_PROXY_CACHE=yes` through publication;
- evidence: complete-diff review and post-publication harness;
- result: a late EXIT or signal can delete the cache already selected by `shared/cache`;
- compatibility cost: active mirror loss;
- disposition: rejected. The candidate checks exact symlink identity and clears private ownership.

### Approach E — repair signal result and cleanup while leaving launch-to-PID gaps

- mechanism: PR #205 parent repair with direct proxy start followed by `PROXYPID=$!`;
- evidence: post-merge self-review;
- result: either new proxy can exist before cleanup can identify it;
- compatibility cost: surviving port-8080 proxy, rerun interference, and false completion;
- disposition: superseded by #224.

### Approach F — temporary launch traps, then restore ordinary traps before pending dispatch

- mechanism: record a signal during launch, assign PID, restore terminating handlers, then dispatch retained status;
- evidence: complete review at intermediate #224 head `dc9222d8d03e51da60b993010c845ec41ea83e61`;
- result: a later signal can overtake the retained first signal between restoration and dispatch;
- compatibility cost: first-signal identity changes;
- disposition: rejected. Pending dispatch now occurs while launch handlers remain active.

### Approach G — model both launch windows with cache deletion ownership enabled

- mechanism: set `CLEANUP_PROXY_CACHE=yes` for both deterministic launch controls;
- evidence: independent ownership review of intermediate #224 head;
- result: the first-launch test exercised a state the product has only after readiness and overclaimed signal-time cache deletion;
- compatibility cost: concealed retained-state behavior and bypassed the real startup preflight contract;
- disposition: rejected. Final controls use `no` for launch one and `yes` for launch two.

### Approach H — compose `update_cache()` worker lifecycle into the same patch

- mechanism: add PR #305/#324 subshell finalizer changes to the top-level patch;
- evidence: source ownership review;
- result: the code overlaps one file yet belongs to a separate process, state owner, test matrix, and result-precedence contract;
- compatibility cost: broadens review and mixes top-level proxy ownership with worker-owned APT cleanup;
- disposition: split to unit 14.

## Selected correction

The selected correction is the exact patch merged through PR #224 and retained on Linux Fieldwork `main`. It combines the parent repair from #159/#205 with both launch-registration repairs and their ownership-accurate regressions.

The patch:

1. initializes top-level owner state;
2. installs ordinary terminating signal traps;
3. launches each proxy through a temporary first-signal recorder;
4. assigns `$!` before dispatching any retained signal;
5. stops and waits for owned proxies through one idempotent helper;
6. separates proxy, cache, and QEMU temporary cleanup;
7. begins private-cache deletion ownership only after first readiness;
8. preserves a cache already selected by the exact active symlink;
9. exits 130, 131, or 143 after signal cleanup.

This is the smallest coherent upstream unit for top-level ownership because every changed top-level trap and raw proxy stop participates in the same invariant: cancellation leaves no owned proxy, performs only currently owned cleanup, preserves the first signal result, and never resumes later work.

## Why the changes belong together

The first and second proxy starts share `PROXYPID`, signal actions, normal stop logic, and EXIT cleanup. Repairing only one launch leaves the same child-ownership gap in the other. Adding `wait` without PID clearing leaves later EXIT paths able to act on a stale or reused PID. Adding terminating traps without publication-state tracking risks deleting the active cache. The focused tests compose these facts into one owner-lifecycle matrix.

The `update_cache()` worker differs: it executes in a pipeline subshell, owns only its APT root, and returns a pipeline result to the top-level shell. Its cleanup-time signal precedence forms unit 14.

## Compatibility analysis

### Status, signal, stderr, and continuation

- Parent-only INT, QUIT, and TERM produce conventional statuses 130, 131, and 143 after cleanup.
- The first handled signal accepted during proxy registration remains authoritative.
- Later work after cancellation stays absent.
- Ordinary command failure remains authoritative over a cleanup failure because cleanup helpers contain their own failures.
- The candidate reports numeric shell status and does not re-raise the original kernel signal.
- Parent-only delivery can remain deferred during an unrelated foreground wait; this unit repairs the result and continuation after delivery.

### Process and socket state

- A live proxy receives TERM and is waited.
- An already-exited proxy is still waited.
- The stored PID is cleared after wait.
- Both port-8080 proxy launches cross PID registration under temporary signal handlers.
- TERM-to-KILL escalation is absent; a proxy that ignores TERM can leave `wait` blocked.

### Cache visibility and publication

- Before readiness, signal cleanup owns the proxy and owner dispatch while cache deletion ownership remains off.
- The next startup preflight handles retained alternate-cache state according to the existing active-symlink rule.
- After readiness, the top-level owner can remove the private failed cache.
- After `shared/cache` identifies `$newcache`, cleanup clears private ownership and preserves the active cache.
- Normal first-proxy shutdown never invokes failed-cache deletion.

### Filesystem cleanup

- QEMU temporary cleanup occurs only while `CLEANUP_TMPDIR=yes`.
- Cleanup helpers are idempotent across ordinary EXIT and signal paths.
- A cleanup helper failure can leave retained state while preserving the primary status; this is an intentional result-precedence change from the baseline trap behavior.

### Shell and platform boundary

- Focused regressions use real `/bin/sh` with disposable files and child processes.
- QUIT support is added alongside INT and TERM.
- The retained evidence does not establish behavior for HUP, process-group delivery, permanently blocking cleanup, hostile descendants, or non-POSIX shell extensions.

## Negative controls and losing mutations

The matrix includes several losing states:

- exact baseline cleanup-only trap resumes and exits 0 after TERM;
- predecessor launch-window implementation permits an unowned child;
- intermediate trap handoff allows later INT to overtake first TERM;
- intermediate ownership fixture grants early cache deletion and therefore fails source-fidelity review;
- pre-publication and post-publication cleanup cases distinguish private from active cache identity;
- ordinary unsignaled reruns prove the detector does not classify every execution as cancellation.

## Current upstream and historical review

The public Forgejo repository showed `main` at `77ec9be5417ee44c96343d2347145585da1b1f94` on 2026-08-01. The public and Debian dgit `make_mirror.sh` blob was `6c4be092edcf23b56b63a3befe238c099c45f590`, matching the Linux Fieldwork imported source exactly. The public file's latest listed `make_mirror.sh` change was dated 2025-01-09.

Public issue and pull-request searches found no visible equivalent top-level signal/proxy lifecycle carrier. This is an overlap search result, not proof that no private or unindexed work exists.

Historical Linux Fieldwork progression:

- #157 selected the cleanup-only trap defect;
- #159 built and repaired the first full parent candidate;
- #205 restacked it and exposed launch-registration gaps during post-merge review;
- #224 repaired both launch windows, first-signal precedence, and ownership-model fidelity;
- #305/#324 characterize the separate `update_cache()` cleanup-time boundary.

## Remaining questions

1. **Zero-fuzz application on a fresh current public checkout.**
   - Discriminator: retrieve upstream commit `77ec9be5417ee44c96343d2347145585da1b1f94`, verify file blob `6c4be092edcf23b56b63a3befe238c099c45f590`, apply the packet patch with `--fuzz=0`, and run `/bin/sh -n make_mirror.sh`.
2. **Focused executable rerun in the current unit branch.**
   - Discriminator: run the two retained unittest modules once each and record statuses, duration, shell identity, cleanup, and immediate rerun.
3. **Complete upstream diff review after creating a controlled fork/branch.**
   - Discriminator: compare the candidate branch to exact upstream base and confirm only the intended `make_mirror.sh` top-level lifecycle changes.
4. **Upstream-native full mirror gate.**
   - Discriminator: on an authorized and suitable Debian host, run the upstream `make_mirror.sh` workflow or a maintainer-accepted focused integration. The current reduced tests avoid network, APT, QEMU, and root.
5. **Proxy escalation policy.**
   - Discriminator: maintainer policy or an executable case proving TERM-only wait can hang under a realistic proxy failure. No current evidence selects an escalation change.

## Evidence boundary

Demonstrated by retained exact-head CI and complete review:

- baseline false continuation and status 0;
- candidate signal statuses and later-work suppression;
- once-only owner cleanup;
- child signal, wait, and PID clearing;
- both launch-registration intervals;
- first-signal precedence;
- ownership-accurate first and second launch cleanup;
- active-cache preservation;
- immediate clean reruns;
- complete shell syntax after patch application in the retained carrier.

Current-source byte identity is externally rechecked through the public dgit blob. This pass could not execute a fresh clone because the local runner failed DNS resolution before repository retrieval. No APT operation, network mirror build, QEMU run, privileged operation, process-group cancellation, HUP case, escalation case, hostile descendant, or permanently blocking cleanup was executed here.

## Reopen triggers

- public `make_mirror.sh` blob changes from `6c4be092edcf23b56b63a3befe238c099c45f590`;
- an equivalent public issue or pull request appears;
- zero-fuzz application or focused tests fail on a fresh checkout;
- a complete diff review finds an ownership or result-precedence gap;
- maintainers request one combined top-level/worker series;
- upstream contribution policy or destination changes;
- explicit authorization enables a controlled fork and submission preparation.
