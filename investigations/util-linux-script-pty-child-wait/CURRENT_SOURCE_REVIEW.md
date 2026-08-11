# Current-source review — util-linux `script(1)` PTY child wait

Date: 2026-08-11

Internal tracking: `teamleaderleo/linux-fieldwork#579`

## TL;DR

The PTY child-wait defect remains present on current util-linux `master` at `53e442154c97b872b529a9f61e335d150ad0f742`. The relevant `lib/pty-session.c` blob is still `5b3d60dead322772eba323efcefb35139305924c`, matching the earlier investigation, so the source mechanism has not changed since the previous exact-source pass.

The adjacent review strengthens the repair boundary. The running path's `waitpid(pty->child, ..., WNOHANG)` can return `0` when the tracked PTY child is still alive. Current code treats every result other than `-1` as a reap, invokes `child_die` with a status value that was not produced by a reap, sets the tracked child to `-1`, and loops. The next iteration therefore becomes `waitpid(-1, ..., WNOHANG)`, widening ownership to unrelated children.

The final path also uses `waitpid(-1, ...)`, so even without the spin it can reap an inherited child that the PTY helper does not own. Both `script(1)` and `scriptlive(1)` use the generic default helper while tracking one forked PID. `su --pty` installs its own `child_wait` callback, so changing the default helper to target-only waiting does not replace `su`'s custom child-wait policy.

The retained source candidate therefore uses one selector throughout: `pty->child`. While the proxy is running it uses `WNOHANG`; after signal cleanup it performs a blocking wait. It publishes child death only when the returned PID equals the tracked PID. A blocking `EINTR` is retried; `WNOHANG == 0` leaves the tracked child untouched.

## Explain like I'm five

The PTY helper owns one child and remembers that child's number.

Linux can answer a nonblocking wait with `0`, which means: “your child is still alive.” Current code reads that answer as if the child died, erases the child's number, and starts waiting for anybody. That is how Bash's process-substitution helper gets pulled into `script`'s wait loop.

The repair keeps asking about the one child the PTY helper owns.

## Why care

The current behavior has two observable consequences already retained in this investigation:

- a Bash process-substitution consumer can keep `script(1)` spinning at full CPU after the real PTY child exits;
- an unrelated inherited child can be reaped by the generic PTY helper while the tracked PTY child is still running.

The first is the user-visible hang reported upstream. The second shows that the bug is an ownership error in the generic helper rather than something specific to `>(...)` syntax.

## Exact current source

- Project: `util-linux/util-linux`
- Current `master` observed: `53e442154c97b872b529a9f61e335d150ad0f742`
- Relevant file: `lib/pty-session.c`
- Relevant blob: `5b3d60dead322772eba323efcefb35139305924c`
- `script.c` blob: `d84b61111773e8b84e9ea43ac9ec2a7f470a1b7e`
- `scriptlive.c` blob: `95bcbb5c70392ec859a07871751518daea35ebcc`
- Earlier source pass: `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Current-source comparison: the relevant PTY wait and `script` caller blobs are unchanged from the earlier pass

Open upstream reports remain:

- https://github.com/util-linux/util-linux/issues/2562
- https://github.com/util-linux/util-linux/issues/3409

No upstream interaction was made.

## Current running-path defect

Current code conceptually does:

```c
options = WNOHANG;
for (;;) {
        pid = waitpid(pty->child, &status, options);
        if (pid != -1) {
                child_die(..., pty->child, status);
                pty->child = -1;
        } else
                break;
}
```

For `waitpid(..., WNOHANG)`, `0` is a normal result. It means that a matching child exists but has not changed state. It is not a reap and does not supply a child-exit status.

This produces two distinct wrong paths:

1. **Tracked child actually exits first**
   - wait returns the tracked PID;
   - helper publishes the correct death and sets `pty->child = -1`;
   - loop repeats with selector `-1`;
   - an unrelated live child makes `waitpid(-1, ..., WNOHANG)` return `0` forever.

2. **Unrelated child generates SIGCHLD while tracked child is still alive**
   - signalfd reports a child exit event;
   - default helper asks specifically about the tracked PTY child;
   - wait returns `0` because that child is still alive;
   - current code nevertheless invokes `child_die`, uses a non-reap status value, and clears the tracked PID;
   - subsequent iterations can wildcard-reap the unrelated child and spin until another child changes state.

The second path is the adjacent context that sharpens the source defect beyond the original hang.

## Final-wait ownership

After `ul_pty_proxy_master()` returns, `script` and `scriptlive` call the same helper if their tracked child is still present.

Current generic code uses blocking `waitpid(-1, ...)` in this phase and loops over all children until it happens to reap the tracked PID or there are no more children.

That wildcard behavior is unnecessary for a helper whose state consists of one `pty->child` PID and whose `child_die` callback reports that child's status. It can also consume an inherited child that belongs to the surrounding application or shell arrangement.

The retained candidate instead blocks on `pty->child` only.

## Shared-consumer review

### `script(1)`

`script` forks one command child, stores that PID in the PTY object, uses the generic `child_die` callback, and performs a final default wait if the child remains tracked.

Target-only waiting matches this ownership model.

### `scriptlive(1)`

`scriptlive` also forks one child, stores that PID in the PTY object, does not install a custom `child_wait`, and calls the generic helper for its final wait.

Target-only waiting matches this ownership model too.

### `su --pty`

`su-common.c` installs a custom `child_wait` callback. SIGCHLD handling dispatches to that callback instead of the generic default helper while the PTY proxy is active.

This review therefore does not propose replacing `su`'s custom wait policy with the default helper.

## History review

The defect appears in the generic helper introduced by `bdd43357062e7c84a4c9d60516c0f4cb28aedf1d`, after `script` was consolidated onto `lib/pty-session` by `ec10634e7ec41c05865f04aa8a62ec854dd66b9d`.

The singular callback contract was part of that change: `child_die()` reports the status of the tracked child. The problem is the return-value predicate and the later selector widening, not the consolidation itself.

Closed PR https://github.com/util-linux/util-linux/pull/922 considered `EINTR` in the running path. Maintainer review noted that the running/signalfd path uses `WNOHANG` with signals blocked, so interruption is not the central concern there. A target-only candidate still needs an `EINTR` retry for the **blocking final wait**, because signal cleanup restores the application's original signal mask before that wait.

## Candidate

Retained patch: `SOURCE_CANDIDATE.patch`.

Core behavior:

```text
selector = tracked PTY child for both phases
running phase -> WNOHANG
final phase   -> blocking wait
EINTR         -> retry
0             -> child still alive; publish nothing
tracked PID   -> publish child_die once, then clear tracked PID
other/error   -> publish nothing
```

This keeps the existing callback interface and running/final distinction while removing wildcard ownership.

## Regression-test direction

The existing `tests/ts/script/options` test surface already exercises `script` command/return behavior. A focused regression should preserve the shell ownership difference that triggers the bug rather than merely test a normal file:

```sh
# failure case: Bash can exec the final command, leaving process substitution
# as a direct child of script
timeout ... bash -c 'script -q -c "echo test" >(wc -c)'

# negative control: trailing command keeps Bash alive, so the process
# substitution remains Bash's child
timeout ... bash -c 'script -q -c "echo test" >(wc -c); :'
```

A second helper-level or shell fixture should arrange an inherited child that exits before the PTY child and assert that the tracked command's exit status remains authoritative without the PTY helper reaping the unrelated child.

The exact upstream test harness form still needs execution against a built tree.

## Execution interruption

A source branch was created in the owned fork at exact current upstream head:

```text
teamleaderleo/util-linux:linux-fieldwork/script-pty-child-wait
base: 53e442154c97b872b529a9f61e335d150ad0f742
```

Local checkout attempts against both GitHub and kernel.org failed at DNS resolution in the execution container. This is an environment/hosted-execution failure, separate from product behavior.

The branch is intentionally left at the exact base rather than using repository automation to materialize the change. The Fieldwork patch is the current source candidate until a normal writable Git checkout or equivalent patch-capable source surface is available.

## Evidence boundary

Proven or source-established:

- current util-linux master still carries the exact relevant PTY wait blob;
- `WNOHANG == 0` is classified by current code as if it were a reap;
- changing the tracked PID to `-1` inside the loop widens the next wait to any child;
- final generic wait also uses wildcard child selection;
- earlier runtime trace reproduces the target-reap -> wildcard-zero spin;
- earlier inherited-child fixture demonstrates wildcard reaping outside the tracked PTY child;
- `script` and `scriptlive` both use the generic helper around one tracked PID;
- `su --pty` has a separate custom child-wait callback path.

Still open:

- compile exact current source with the retained patch;
- run upstream `script` and PTY tests on the candidate;
- add the final upstream-style regression test;
- exercise stopped/continued children and delivered termination signals on the built candidate;
- settle behavior for an externally reaped tracked child (`ECHILD`) if a supported caller can create that state.

## Current disposition

- State: `REPAIR`
- Current upstream head reviewed: `53e442154c97b872b529a9f61e335d150ad0f742`
- Candidate artifact: `SOURCE_CANDIDATE.patch`
- Owned source branch: exact-base only, no source commit yet
- Source-write blocker: execution DNS + connected GitHub contents surface requires complete-file replacement rather than an ordinary patch operation
- Next safe action: apply the retained patch in a normal checkout, build `script`/PTY consumers, and run the two ownership differentials plus focused upstream tests
- External-contact state: no upstream interaction authorized or made
