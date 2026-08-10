# util-linux `script(1)` PTY child wait spin

## TL;DR

`script(1)` can consume a CPU indefinitely when Bash process substitution leaves an extra child under the `script` process. Current `util-linux` master still carries the mechanism in `ul_pty_wait_for_child()`: the running path calls `waitpid(..., WNOHANG)` and treats every return other than `-1` as a reap. A return of `0` means the requested child is still running. After a real reap, the loop also changes the tracked PID to `-1`, so the next iteration widens into `waitpid(-1, ...)` and can include unrelated children.

A local util-linux 2.41 binary reproduces upstream issue #2562. The stored passive `waitpid` tracer records `tracked child -> reaped`, followed by repeated `waitpid(-1, WNOHANG) -> 0`. A local semantic discriminator that changed only those wait outcomes made the original reproduction exit normally and removed the CPU burn from an adjacent case where an unrelated inherited child exits first.

The source candidate is small: wait only for `pty->child`, interpret `0` as “still running,” call `child_die` only when the returned PID equals the tracked PID, and make the final blocking wait target that same PID. Exact-current build and test execution are the next gate.

## Explain like I'm five

`script` starts one helper process: the shell or command running inside its pseudo-terminal. It remembers that helper's PID.

Bash can also leave another child behind for `>(wc -c)`. The current loop finishes waiting for the real `script` child, changes its remembered PID to `-1`, then asks Linux about “any child.” Linux answers `0`, meaning “a matching child exists and is still running.” The loop reads that `0` like a completed wait and asks again immediately.

Literal example:

`script child exits -> waitpid returns its PID -> remembered PID becomes -1 -> waitpid(-1, WNOHANG) returns 0 -> loop repeats at full CPU`.

## Why care

This is a user-visible `script(1)` hang with a compact shell fixture and an open upstream report. The same code can also wildcard-reap a child outside the single PID tracked by the PTY helper.

`util-linux` is already an inbox Fieldwork target, so this gives the lab a bounded repair candidate and a clear regression-test direction.

## Current state

- State: `REPAIR`
- Exact working head: upstream `util-linux/util-linux` master `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Fieldwork carrier: issue `#579`, branch `expedition/util-linux-script-pty-wait`
- Latest gate: local wait-semantics differential on util-linux 2.41; stock process substitution times out, simulated target-only semantics exits `0`; an adjacent inherited-child case keeps exit `7` while CPU time falls from about `0.44s` to `0.00s` over a `0.51s` run
- First incomplete step: build exact upstream head, apply the source candidate, add an upstream-style regression test, and run focused `script`/PTY tests
- Cleanup state: complete; local test processes and compiled preload objects removed
- Next safe action: validate the real source patch against exact-current source
- External-contact state: no upstream comment, issue edit, pull request, review, or patch submission authorized or made

## Intent and precedent

Two open reports describe this family:

- https://github.com/util-linux/util-linux/issues/2562 — `script` hangs in `ul_pty_wait_for_child` with `>(wc)` and reports the regression beginning at `ec10634e7ec41c05865f04aa8a62ec854dd66b9d`.
- https://github.com/util-linux/util-linux/issues/3409 — a newer Ubuntu reproduction using `exec script ... -f >(while read; ...)` also hangs on termination.

Commit `ec10634e7ec41c05865f04aa8a62ec854dd66b9d` consolidated `script`, `scriptlive`, and `su --pty` onto `lib/pty-session`.

Commit `bdd43357062e7c84a4c9d60516c0f4cb28aedf1d` moved the default child-wait implementation into `ul_pty_wait_for_child()`. Its commit message describes `child_die()` as the callback used to report the tracked child's status. Current `script.c` follows that singular-child model: it forks one command child, passes that PID to `ul_pty_set_child()`, and stores status in `callback_child_die()`.

Commit `90ebcedb8701322685abaec76213dfba21757272` is useful precedent: it repaired a separate signal-lifecycle regression introduced by the PTY consolidation commit.

An upstream PR search found no current repair tied to issue #2562 or this exact wait defect. PR #1141 mentions `ul_pty_wait_for_child` in an older PTY I/O/signal change and addresses a different problem.

## Question

When the generic PTY session tracks one command child, can `ul_pty_wait_for_child()` confuse `WNOHANG`'s zero result or an unrelated inherited child with completion of that tracked child?

## Source

- Project: `util-linux/util-linux`
- Requested revision: current `master`
- Resolved commit: `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Relevant source: `lib/pty-session.c`, blob `5b3d60dead322772eba323efcefb35139305924c`
- Relevant caller: `term-utils/script.c`, blob `d84b61111773e8b84e9ea43ac9ec2a7f470a1b7e`
- Regression lineage: `ec10634e7ec41c05865f04aa8a62ec854dd66b9d`, `bdd43357062e7c84a4c9d60516c0f4cb28aedf1d`
- Local source path: unavailable during this round because the execution container could not resolve GitHub for a clone
- Import metadata: none; exact source inspection used GitHub directly

## Environment

Runtime probes used the available disposable container:

- Debian GNU/Linux 13 (trixie), 13.3
- Linux 6.18.35, x86_64
- GNU Bash 5.2.37(1)-release
- UID 0 inside the container
- `script` from util-linux 2.41
- system C compiler for the passive preload tracer

The runtime binary is older than the inspected upstream source. The relevant `ul_pty_wait_for_child()` code remains present at exact upstream head `ce6a4ea...`; executable confirmation of that exact head remains open.

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

# A trailing no-op keeps the outer Bash process alive. wc remains Bash's child.
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

The process-substitution `wc` is an actual child of `script` in the failing execution. It waits for pipe EOF while `script` still owns the pipe's write end.

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

`waitpid()` has three distinct outcomes here:

- `pid > 0`: a matching child was reaped;
- `pid == 0` with `WNOHANG`: the requested child is still running;
- `pid == -1`: error / no matching child.

The code groups `0` with a reap. It also changes `pty->child` to `-1` inside a loop whose next iteration uses `pty->child` as the selector. A successful first iteration therefore widens the next call to “any child.”

The final-wait branch independently uses `waitpid(-1, ...)`, so the helper can reap children outside the single PID it tracks.

### Candidate repair boundary

Keep the wait singular and make the return-value contract explicit:

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

This sketch changes child selection and wait-result handling while preserving the running `WNOHANG` mode, final blocking wait, callback interface, and status handoff.

The exact policy for a blocking final wait that returns `ECHILD` remains a review point.

## Reproduction

The durable executable fixtures stored with this report are:

```text
fixtures/reproduce.sh
fixtures/waitpid-trace.c
```

Core reproduction:

```sh
./fixtures/reproduce.sh
```

Passive wait trace:

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

A second local preload experiment simulated the target-only candidate semantics against the same installed binary. The interaction safety layer blocked storing that experimental interposer source in this repository. Its executed results are retained below, and the product candidate itself is expressed as the source sketch above.

## Results

### Wait trace on the hanging case

The passive tracer records one PTY fork, then the decisive sequence:

```text
pid=695 fork() -> child=697
pid=695 waitpid(arg=697, options=0x1) -> 697 errno=0
pid=695 waitpid(arg=-1, options=0x1) -> 0 errno=0
pid=695 waitpid(arg=-1, options=0x1) -> 0 errno=0
pid=695 waitpid(arg=-1, options=0x1) -> 0 errno=0
...
```

`0x1` is `WNOHANG`. The first call correctly reaps the tracked PTY child. The loop then uses PID `-1`, repeatedly receives `0`, and remains runnable while the process-substitution child waits for EOF from `script`.

### Candidate-semantics differential

Local executed results:

```text
stock process-substitution:
  test
  rc=124

simulated target-only semantics:
  test
  165
  rc=0

simulated semantics, ordinary-file control:
  test
  rc=0
```

The experimental interposer changed only the two outcomes needed to test the candidate boundary: a `WNOHANG` zero left the current loop without declaring the child dead, and the post-reap wildcard iteration terminated. This is a discriminator for the repair idea, followed by exact-source patch testing as the authoritative gate.

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

Five stock runs still returned the command's exit `7`, because the spin eventually reaped the PTY child and overwrote the earlier status. CPU behavior separated the implementations clearly:

```text
stock:
  rc=7 elapsed=0.51 user=0.06 sys=0.38

simulated target-only semantics:
  rc=7 elapsed=0.51 user=0.00 sys=0.00
```

This context strengthens the candidate: the helper should leave a `0` result alone and should wait only for the child PID it owns.

## Falsified hypothesis

The first theory blamed only the final blocking `waitpid(-1, ...)`: `script` would wait for the process-substitution consumer while that consumer waited for EOF from `script`.

Changing only final-wait behavior failed to release the hang. The passive trace then located the earlier divergence inside the running `WNOHANG` loop. Keeping this failed theory in the record separates pipe lifetime from the actual spin owner.

## Interpretation

Demonstrated behavior:

1. Bash's last-command path can leave a process-substitution consumer as a direct child of `script`.
2. util-linux 2.41 reproduces open issue #2562 with the compact `>(wc -c)` fixture.
3. Current upstream master still contains the wait code that classifies `waitpid(..., WNOHANG) == 0` as a completed iteration and mutates the selector to `-1` before looping.
4. The passive tracer records the exact runtime sequence predicted by that source: target reap, wildcard zero, repeated wildcard zero.
5. An inherited child exiting first causes the same loop to reap that different child and spin until the PTY child exits.
6. Simulated target-only semantics release the original hang, preserve the ordinary-file control and exit `7` companion case, and remove the near-one-core CPU burn.

The bounded defect sits in `ul_pty_wait_for_child()`'s child selection and return-value handling. The singular `pty->child` field and callback contract support a singular wait. Fixing the generic helper also covers the foreign-child case without adding process-substitution-specific behavior to `script.c`.

## Evidence boundary

- Exact current upstream source was inspected at `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`.
- Runtime execution used Debian's util-linux 2.41 binary.
- The execution container could not clone/build GitHub source because GitHub DNS resolution was unavailable.
- The source sketch has therefore yet to be compiled against exact current master.
- The upstream `script` tests and other PTY consumers have yet to run with the source candidate.
- `su --pty`, `scriptlive`, stopped/continued children, delivered termination signals, and `ECHILD` final-wait policy remain candidate-review areas.
- The stored tracer is passive. The local semantics interposer was an experimental discriminator; its repository write was blocked and its source is intentionally absent from this carrier.
- Upstream readiness is still open.

The central finding remains strong because the decisive source code is unchanged on current master and the passive runtime trace exercises the same wait contract.

## Next step

1. Build exact `ce6a4ea...` in a writable carrier.
2. Reproduce both executable contexts on that binary.
3. Apply the target-only `ul_pty_wait_for_child()` candidate.
4. Add a focused regression test for process-substitution termination plus a companion inherited-child case.
5. Run focused `script` tests and PTY consumers sharing the helper.
6. Compare signal behavior, stopped children, command exit status, descriptor cleanup, CPU use, and repeated runs.
7. If those gates converge, prepare an upstream patch packet for explicit human authorization.

The current evidence favors target-only semantics in both running and final wait paths over a narrower one-line `pid > 0` fix, because the final wildcard wait carries the same foreign-child ownership issue.

## Authority

Research and writes are confined to `teamleaderleo/linux-fieldwork` and the disposable local execution environment. No upstream interaction has been authorized or performed.
