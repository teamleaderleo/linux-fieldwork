# Tini process-group startup signal race

## TL;DR

At `krallin/tini` commit `369448a167e8b3da4ca5bca0b3307500c3371828`, `-g` process-group forwarding has a startup race. Tini blocks signals before `fork()`, the child creates its own process group after `fork()`, and the parent can consume a pending signal and call `kill(-child_pid, signal)` before that process group exists. In that ordering Linux returns `ESRCH`; Tini warns that the child was dead even though the child can still be alive, and the signal is lost.

A faithful reduced fixture reproduced the ordering on Linux 6.18.35. Across 10,000 iterations, the current ordering forwarded 41 signals and hit `ESRCH` 9,959 times. A discriminator where the parent establishes `setpgid(child_pid, child_pid)` before forwarding delivered all 10,000 signals and produced zero `ESRCH` results.

Next action: execute an exact Tini binary or owned-fork candidate with a startup-signal regression that sends the signal before child-tree readiness. Keep the existing child-side `setpgid()` / tty ownership path while evaluating a parent-side group-establishment handshake.

## Explain like I'm five

Tini promises that `-g` sends a signal to the whole child group. The group is created by the child a moment after the child is born. Tini's parent half can try to send the signal during that tiny moment. Linux then says “that group does not exist,” and Tini drops the signal.

Literal example: `SIGUSR1 arrives while blocked -> Tini forks -> parent tries kill(-child_pid, SIGUSR1) before child setpgid() -> ESRCH -> child keeps running`.

## Why care

`-g` exists so container shutdown and terminal-style signals reach the whole foreground child group. A signal arriving during process startup can disappear before the group exists. For termination signals this can delay or defeat shutdown; for reload or user signals it can lose the requested event entirely.

## Current state

- State: `REVIEW`
- Exact working head: `krallin/tini@369448a167e8b3da4ca5bca0b3307500c3371828`
- Latest authoritative gate or artifact: local reduced fixture `repro.c`, SHA-256 `8cff6b8cd9ec90ed35b9d80ecfa1f4e4ae42c035d5b83bd8c1043b2fbe1e66a8`
- First incomplete step: run the startup discriminator against an exact built Tini binary or a narrow owned-fork candidate
- Cleanup state: every fixture child was reaped; no surviving processes or files beyond `/tmp` fixture binaries during execution
- Next safe action: add a Tini-native regression that queues a signal before spawn completion and compare baseline with parent-established PGID
- External-contact state: no upstream contact authorized or made

## Intent and precedent

Tini documents `-g` and `TINI_KILL_PROCESS_GROUP` as sending signals to the child's process group so every process in the group receives the signal:

- https://github.com/krallin/tini/blob/369448a167e8b3da4ca5bca0b3307500c3371828/README.md#process-group-killing

The feature entered through PR 16 in 2015:

- https://github.com/krallin/tini/pull/16

That change added child-side `setpgid(0, 0)` and parent-side `kill(-child_pid, signal)`. Its process-group test waits until two descendants are visible before signaling. The current test retains that readiness wait, so it validates steady-state group forwarding while leaving startup forwarding outside the fixture.

Current relevant source:

- `configure_signals()` blocks forwarded signals before spawn.
- `spawn()` forks; only the child calls `isolate_child()`, which starts with `setpgid(0, 0)`.
- the parent branch returns immediately after recording `child_pid`.
- `wait_and_forward_signal()` later calls `kill(kill_process_group ? -child_pid : child_pid, sig.si_signo)`.
- `ESRCH` is converted into the warning `Child was dead when forwarding signal` and execution continues.

Primary source: https://github.com/krallin/tini/blob/369448a167e8b3da4ca5bca0b3307500c3371828/src/tini.c

Current test: https://github.com/krallin/tini/blob/369448a167e8b3da4ca5bca0b3307500c3371828/test/run_inner_tests.py

## Question

Can Tini lose a signal in `-g` mode when the signal is pending before the child has completed `setpgid()`, and does establishing the same PGID from the parent before forwarding remove that failure window?

## Source

- Project: `krallin/tini`
- Requested revision: current repository head observed on 2026-08-11
- Resolved commit: `369448a167e8b3da4ca5bca0b3307500c3371828`
- Candidate source commit: none; candidate mechanism only
- Local source path: exact source read through the connected GitHub repository; the local shell could not clone because DNS access to `github.com` was unavailable
- Import metadata: none; no source tree was imported into `upstream/`

## Environment

- Distribution and release: Debian GNU/Linux 13
- Kernel and architecture: Linux `6.18.35`, `x86_64`
- Shell: GNU bash `5.2.37(1)-release`
- Privileges: uid `0` inside the disposable execution container; fixture itself requires no privileged syscall
- Container, virtual machine, or host context: disposable container
- Relevant tool versions: GCC `14.2.0`

## Baseline behavior

The reduced fixture mirrors the decisive ordering:

1. block `SIGUSR1` as Tini does before spawn;
2. queue `SIGUSR1` on the parent before `fork()`;
3. fork;
4. child calls `setpgid(0, 0)` and restores its signal mask;
5. parent consumes the pending signal and calls `kill(-child_pid, SIGUSR1)`;
6. record whether the group existed and whether the child actually died from `SIGUSR1`.

With the current ordering, the parent usually runs before the child has created its group. `kill(-child_pid, SIGUSR1)` then returns `ESRCH`. The signal has already been consumed from Tini's pending set, so no later retry occurs.

## Hypothesis or candidate

The invariant is: once Tini accepts a signal for process-group forwarding, startup ordering must not make that signal disappear solely because the child has not yet executed its own `setpgid()`.

Candidate mechanism for review: have the parent establish the child's PGID before `spawn()` returns, while retaining child-side `setpgid()` because the child also owns tty foreground-group setup. Parent and child setting the same PGID is the intended discriminator; exact error handling around a child that has already exec'd or exited still needs source-level design review.

The candidate should preserve:

- existing child process-group identity;
- tty ownership work in the child;
- direct-child mode when `-g` is absent;
- existing signal mask restoration;
- current exit-code and reaping behavior.

## Reproduction

Compile and run [`repro.c`](repro.c):

```sh
cc -O2 -Wall -Wextra -Werror repro.c -o repro
./repro 10000
```

Observed authoritative run:

```text
current-order: iters=10000 forwarded=41 ESRCH=9959 other=0 child-died-SIGUSR1=41
parent-setpgid-order: iters=10000 forwarded=10000 ESRCH=0 other=0 child-died-SIGUSR1=10000
```

Earlier raw group-existence stress also showed the same discriminator across 20,000 iterations:

```text
current-model: iters=20000 group-present=201 ESRCH=19799 other=0
parent-setpgid-model: iters=20000 group-present=20000 ESRCH=0 other=0 parent-setpgid-other-errors=0
```

## Results

The current source ordering admits an observable interval where the child's PID exists but the process group named by `-child_pid` does not. Linux reports `ESRCH` for the group send in that interval.

The signal-forwarding fixture proves the practical consequence inside the reduced model: every `ESRCH` iteration lost the forwarded `SIGUSR1`; only successful group sends produced `SIGUSR1` child termination. Establishing the same PGID from the parent before consuming/forwarding the queued signal removed the failure in all 10,000 iterations.

The existing upstream process-group test is a useful negative control for steady-state behavior: it waits for the full child tree before signaling, which is exactly the context where the process group already exists.

## Interpretation

Demonstrated behavior: the syscall ordering used by Tini can produce `ESRCH` while the child is alive, and a signal already consumed by the parent's wait loop is then lost.

Source-supported consequence: current Tini treats `ESRCH` as if the child were dead and performs no retry or PGID synchronization.

Design choice for review: parent-side `setpgid(child_pid, child_pid)` before returning from `spawn()` closes the demonstrated group-creation window in the reduced fixture. A Tini-native candidate should verify exact Linux error cases and tty behavior before promotion.

## Evidence boundary

- The exact Tini source and tests were read at commit `369448a167e8b3da4ca5bca0b3307500c3371828` through the GitHub connector.
- The local execution environment could not clone or build Tini because direct DNS access to GitHub was unavailable.
- Execution used a reduced C fixture reproducing the exact decisive Linux syscalls and signal-mask ordering, not the full Tini binary.
- Results establish the startup race mechanism on Linux 6.18.35 x86_64. Other kernels and non-Linux platforms were not executed.
- Tty foreground-group behavior was not exercised.
- No container runtime integration test was executed.
- No upstream issue or patch was created.

Reopen triggers: an exact Tini run that proves startup forwarding is serialized elsewhere, Linux behavior that makes parent-side PGID establishment unsafe for Tini's tty contract, or current upstream work already closing this window.

## Next step

Human reviewer chooses whether this is worth promoting into an owned-fork Tini candidate. The supporting evidence is the exact source ordering, the upstream test's steady-state readiness wait, and the 10,000-iteration baseline/candidate discriminator in `repro.c`.

If promoted, first build a Tini-native regression that queues `SIGUSR1` before child group readiness. Then implement the narrowest PGID synchronization that makes that regression pass without changing non-`-g` behavior.

## Authority

No upstream Tini issue, email, pull request, patch submission, comment, review, or other interaction has been authorized or made. Repository-file links are retained as research evidence only.
