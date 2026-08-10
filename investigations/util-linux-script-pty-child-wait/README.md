# util-linux `script(1)` PTY child wait spin

## TL;DR

`script(1)` can consume a CPU indefinitely when Bash process substitution leaves an extra child under the `script` process. Current `util-linux` master still has the mechanism: `ul_pty_wait_for_child()` uses `waitpid(..., WNOHANG)` and treats every return other than `-1` as if a child was reaped. A `0` return means the requested child is still running. After a real reap, the loop also changes the tracked PID to `-1` and therefore widens the next call to `waitpid(-1, ...)`, allowing unrelated children to enter the loop.

A local util-linux 2.41 runtime reproduces the hang from upstream issue #2562. A `waitpid` interposer records `tracked child -> reaped`, followed by repeated `waitpid(-1, WNOHANG) -> 0`. An experimental interposer that simulates target-only wait semantics makes the reproduction exit normally and removes the CPU spin from an adjacent case where an unrelated child exits first.

The repair candidate is small: wait only for `pty->child`, interpret `0` as “still running”, call `child_die` only for a positive return equal to the tracked PID, and use a blocking wait for that same PID in the final-wait path. Exact-current upstream build and test execution remain the next gate.

## Explain like I'm five

`script` starts one helper process: the shell or command running inside its pseudo-terminal. It keeps that helper's PID so it knows which child to wait for.

Bash can also leave another child behind for `>(wc -c)`. The current wait loop finishes waiting for the real `script` child, changes its remembered PID to `-1`, then asks Linux about “any child.” Linux answers `0`, meaning “there is a child, but it has not finished yet.” The loop reads that `0` as “finished” and asks again immediately, forever.

Literal example:

`script child exits -> waitpid returns its PID -> remembered PID becomes -1 -> waitpid(-1, WNOHANG) returns 0 -> loop repeats at full CPU`.

## Why care

This is a user-visible hang in `script(1)` with a small shell fixture and an open upstream report. The defect also crosses a process-ownership boundary: a generic PTY helper that tracks one child can wildcard-wait and reap a different child inherited by its caller.

The result gives `util-linux`, already an inbox Fieldwork target, a compact repair candidate with a clear regression test direction.

## Current state

- State: `REPAIR`
- Exact working head: upstream `util-linux/util-linux` master `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Fieldwork carrier: issue `#579`, branch `expedition/util-linux-script-pty-wait`
- Latest authoritative gate: local wait-semantics differential on util-linux 2.41; stock process-substitution case times out, simulated target-only semantics exits `0`; adjacent inherited-child case keeps exit `7` while CPU time falls from about `0.44s` to `0.00s` over a `0.51s` run
- First incomplete step: build exact upstream head, apply the source candidate, add an upstream-style regression test, and run the focused `script`/PTY tests
- Cleanup state: complete; local test processes and temporary preload objects removed
- Next safe action: materialize exact-current source in a writable test carrier and validate the real source patch
- External-contact state: no upstream comment, issue edit, pull request, review, or patch submission authorized or made

## Intent and precedent

Two open reports describe this family:

- https://github.com/util-linux/util-linux/issues/2562 — `script` hangs in `ul_pty_wait_for_child` with `>(wc)` and reports the regression beginning at `ec10634e7ec41c05865f04aa8a62ec854dd66b9d`.
- https://github.com/util-linux/util-linux/issues/3409 — a newer Ubuntu reproduction using `exec script ... -f >(while read; ...)` also hangs on termination.

Commit `ec10634e7ec41c05865f04aa8a62ec854dd66b9d` consolidated `script`, `scriptlive`, and `su --pty` onto `lib/pty-session`.

Commit `bdd43357062e7c84a4c9d60516c0f4cb28aedf1d` then moved the default child-wait implementation into `ul_pty_wait_for_child()`. Its commit message describes `child_die()` as the simple callback that informs the application about the tracked child's status. The singular child contract is also visible in the API and current `script.c`: `script` forks one command child, passes that PID to `ul_pty_set_child()`, and records status in `callback_child_die()`.

Commit `90ebcedb8701322685abaec76213dfba21757272` is useful precedent rather than the same defect: it fixed another signal-lifecycle regression introduced by the PTY consolidation commit. That history supports treating the consolidation boundary as a place where old `script` process semantics deserve direct comparison.

An upstream pull-request search found no existing PR for issue #2562 or this specific wait defect at the time of the expedition. PR #1141 mentions `ul_pty_wait_for_child` in an older PTY I/O/signal change and addresses a different problem.

## Question

When the generic PTY session tracks one command child, can `ul_pty_wait_for_child()` mistake `WNOHANG`'s zero result or an unrelated inherited child for completion of that tracked child?

## Source

- Project: `util-linux/util-linux`
- Requested revision: current `master`
- Resolved commit: `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Relevant current source blob: `lib/pty-session.c` blob `5b3d60dead322772eba323efcefb35139305924c`
- Relevant caller: `term-utils/script.c` blob `d84b61111773e8b84e9ea43ac9ec2a7f470a1b7e`
- Regression lineage: `ec10634e7ec41c05865f04aa8a62ec854dd66b9d`, `bdd43357062e7c84a4c9d60516c0f4cb28aedf1d`
- Local source path: unavailable during this round; the execution container could not resolve GitHub for a clone
- Import metadata: none; source inspection used the GitHub repository at the exact commit above

## Environment

Runtime probes used the available execution container:

- Distribution and release: Debian GNU/Linux 13 (trixie), 13.3
- Kernel and architecture: Linux 6.18.35, x86_64
- Shell: GNU Bash 5.2.37(1)-release
- Privileges: UID 0 inside the disposable execution container
- Context: disposable container
- Runtime `script`: util-linux 2.41
- Compiler used for preload probes: system C compiler

The runtime binary is older than the inspected upstream source. The relevant `ul_pty_wait_for_child()` logic remains present at exact upstream head `ce6a4ea...`; exact-head executable confirmation is still required.

## Baseline behavior

### Original report reduced to three commands

```sh
# Ordinary file logging: exits normally.
timeout 3s script -q -c 'echo test' /tmp/lf-util-linux-typescript
# observed: test
# exit: 0

# Bash may exec-optimize the last command. The process-substitution consumer
# then becomes a direct child of script. This hangs.
timeout 3s bash -c 'script -q -c "echo test" >(wc -c)'
# observed: test
# exit: 124 (timeout)

# A trailing no-op keeps the outer Bash process alive. wc remains Bash's child,
# and script exits normally.
timeout 3s bash -c 'script -q -c "echo test" >(wc -c); :'
# observed:
# test
# 165
# exit: 0
```

The trailing-`:` case is the negative control. It changes process ownership while preserving `script`, its PTY command, and the process-substitution logging mechanism.

### Process and descriptor ownership

During the hanging case, a live snapshot showed:

```text
PID 626  PPID 622  script  script -q -c sleep 0.2; echo test /dev/fd/63
PID 628  PPID 626  wc      wc -c

script fd 6  -> pipe:[5774]
script fd 63 -> pipe:[5774]
wc     fd 0  -> pipe:[5774]
```

The process-substitution `wc` is therefore an actual child of `script` in the failing execution. It waits for pipe EOF while `script` still owns the pipe's write end.

## Hypothesis or candidate

### Source defect

Current `ul_pty_wait_for_child()` does this while the PTY proxy is running:

```c
options = WNOHANG;
for (;;) {
        pid = waitpid(pty->child, &status, options);
        if (pid != (pid_t) -1) {
                if (pty->callbacks.child_die)
                        pty->callbacks.child_die(
                                        pty->callback_data,
                                        pty->child, status);
                ul_pty_set_child(pty, (pid_t) -1);
        } else
                break;
}
```

`waitpid()` has three distinct result classes here:

- `pid > 0`: that child was reaped;
- `pid == 0` with `WNOHANG`: the requested child is still running;
- `pid == -1`: error / no matching child.

The code groups `0` with a successful reap. It also mutates `pty->child` to `-1` inside a loop whose next iteration uses `pty->child` as the `waitpid()` selector. A successful first iteration therefore widens the next call to “any child.”

The final-wait branch independently uses `waitpid(-1, ...)`, so the same generic helper can reap children outside the single PID it claims to track.

### Candidate repair boundary

Keep the wait singular and make the return-value contract explicit. A source sketch is:

```c
void ul_pty_wait_for_child(struct ul_pty *pty)
{
        int status;
        pid_t pid;
        int options;

        if (pty->child == (pid_t) -1)
                return;

        options = ul_pty_is_running(pty) ? WNOHANG : 0;

        do
                pid = waitpid(pty->child, &status, options);
        while (pid < 0 && errno == EINTR);

        if (pid == pty->child) {
                if (pty->callbacks.child_die)
                        pty->callbacks.child_die(
                                        pty->callback_data,
                                        pty->child, status);
                ul_pty_set_child(pty, (pid_t) -1);
        }
}
```

This sketch deliberately changes only child selection and wait-result handling. It preserves the running `WNOHANG` behavior, the final blocking wait, the callback interface, and the existing status handoff.

The exact error policy for a blocking final wait that returns `ECHILD` remains a review point. The candidate above preserves the current running-path behavior of leaving the tracked PID unchanged on wait errors.

## Reproduction

The reusable commands and preload probes live in `fixtures/` beside this report.

Core reproduction:

```sh
./fixtures/reproduce.sh
```

Compile the wait tracer:

```sh
cc -shared -fPIC -O2 -Wall -Wextra \
  -o /tmp/lf-waitpid-trace.so fixtures/waitpid-trace.c -ldl

rm -f /tmp/lf-waitpid-trace.log
timeout 1s bash -c \
  'exec 9>/tmp/lf-waitpid-trace.log; \
   LF_WAITTRACE_FD=9 LD_PRELOAD=/tmp/lf-waitpid-trace.so \
   script -q -c "echo test" >(wc -c)'
head -25 /tmp/lf-waitpid-trace.log
```

Compile the experimental semantics shim:

```sh
cc -shared -fPIC -O2 -Wall -Wextra \
  -o /tmp/lf-waitpid-semantics.so fixtures/waitpid-semantics-shim.c -ldl

# Failing process-substitution case under simulated corrected semantics.
timeout 2s bash -c \
  'LD_PRELOAD=/tmp/lf-waitpid-semantics.so \
   script -q -c "echo test" >(wc -c)'

# Adjacent case: another inherited child exits before the PTY child.
/usr/bin/time -f 'rc=%x elapsed=%e user=%U sys=%S' \
  bash -c \
  'exec 8> >(sleep 0.05); \
   LD_PRELOAD=/tmp/lf-waitpid-semantics.so \
   exec script -q -e -c "sleep 0.50; exit 7" /dev/null'
```

## Results

### Wait trace on the hanging case

The first trace records exactly one PTY fork, then the decisive sequence:

```text
pid=695 fork() -> child=697
pid=695 waitpid(arg=697, options=0x1) -> 697 errno=0
pid=695 waitpid(arg=-1, options=0x1) -> 0 errno=0
pid=695 waitpid(arg=-1, options=0x1) -> 0 errno=0
pid=695 waitpid(arg=-1, options=0x1) -> 0 errno=0
...
```

`0x1` is `WNOHANG`. The first call correctly reaps the tracked PTY child. The loop then uses PID `-1`, repeatedly receives `0`, and remains runnable at full CPU while the process-substitution child waits for EOF from `script`.

### Candidate-semantics differential

```text
stock process-substitution:
  test
  rc=124

simulated break/target-only semantics:
  test
  165
  rc=0

simulated semantics, ordinary file control:
  test
  rc=0
```

The experimental interposer does not patch `script`; it changes only how the existing binary sees the two incorrect wait outcomes: `WNOHANG` zero is made to leave the loop without declaring the child dead, and the post-reap wildcard iteration is made to terminate. This is evidence for the semantic boundary, not a substitute for testing the real source patch.

### Adjacent context: unrelated child exits first

Fixture:

```sh
exec 8> >(sleep 0.05)
exec script -q -e -c 'sleep 0.50; exit 7' /dev/null
```

The inherited `sleep 0.05` child exits before the PTY child. The tracer observed:

```text
fork -> PTY child 800
waitpid(800, WNOHANG) -> 0
waitpid(-1, WNOHANG) -> 799    # unrelated inherited child reaped
waitpid(-1, WNOHANG) -> 0      # repeated spin
...
waitpid(-1, WNOHANG) -> 800    # PTY child eventually exits 7
```

The visible exit status still became `7` in five runs because the spin eventually reaped the PTY child and overwrote the earlier status. The ownership and CPU behavior still diverged sharply:

```text
stock:
  rc=7 elapsed=0.51 user=0.06 sys=0.38

simulated target-only semantics:
  rc=7 elapsed=0.51 user=0.00 sys=0.00
```

This adjacent case strengthens the repair boundary: the generic helper should neither announce completion on `0` nor reap a different child while waiting for its tracked PID.

## Falsified hypothesis

The first working theory blamed only the final blocking `waitpid(-1, ...)`: `script` would wait for the process-substitution consumer, while that consumer waited for EOF from `script`.

A candidate experiment that changed only final-wait behavior failed to release the hang. Tracing then located the earlier divergence inside the running `WNOHANG` loop. Retaining this failed hypothesis is useful because it distinguishes pipe lifetime from the actual spin owner.

## Interpretation

Demonstrated behavior:

1. Bash's last-command execution path can leave a process-substitution consumer as a direct child of `script`.
2. util-linux 2.41 reproduces the open #2562 hang on the compact `>(wc -c)` fixture.
3. Current upstream master still contains the wait logic that classifies `waitpid(..., WNOHANG) == 0` as a successful iteration and mutates the selector to `-1` before looping.
4. A wait interposer records the exact runtime sequence predicted by that source: target reap, wildcard zero, repeated wildcard zero.
5. A second inherited child exiting first causes the same loop to reap that unrelated child and spin until the PTY child exits.
6. Simulated target-only semantics make the original hang exit normally, preserve the ordinary-file control, preserve the adjacent command's exit `7`, and remove its near-one-core CPU burn.

Interpretation:

The bounded defect sits in `ul_pty_wait_for_child()`'s child-selection and return-value handling. The singular `pty->child` field and callback contract support a singular wait. A repair that waits only for that PID also closes the adjacent foreign-child reaping behavior instead of patching the process-substitution symptom in `script.c`.

## Evidence boundary

This round establishes source/runtime mechanism alignment with one important version boundary:

- exact current upstream source was inspected at `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`;
- runtime execution used Debian's util-linux 2.41 binary;
- the execution container could not clone/build GitHub source because DNS resolution for GitHub was unavailable;
- the source sketch itself has therefore not been compiled against exact current master;
- the upstream `script` test suite and other PTY consumers have not been run with the source candidate;
- `su --pty`, `scriptlive`, stopped/continued children, delivered termination signals, and `ECHILD` final-wait policy still need exact-candidate review;
- preload shims are experimental discriminators only;
- no claim is made yet that the patch sketch is upstream-ready.

The finding remains useful because the decisive faulty source is unchanged on current master and the runtime trace exercises the same wait semantics.

## Next step

1. Build exact `ce6a4ea...` in a writable carrier.
2. Reproduce both executable fixtures unchanged on that binary.
3. Apply the target-only `ul_pty_wait_for_child()` candidate.
4. Add a focused regression test that proves the process-substitution case terminates and a companion case where an unrelated inherited child exits first.
5. Run the focused `script` tests plus PTY consumers that share this helper.
6. Compare signal, stopped-child, child-exit-status, descriptor cleanup, and repeated-run behavior.
7. If those gates converge, prepare an upstream patch packet for explicit human authorization.

Human review will eventually choose between a minimal running-loop correction and the stronger target-only correction for both running and final waits. The adjacent foreign-child observation currently favors target-only semantics for both paths.

## Authority

Research and writes are confined to `teamleaderleo/linux-fieldwork` and the disposable local execution environment. No upstream interaction has been authorized or performed.
