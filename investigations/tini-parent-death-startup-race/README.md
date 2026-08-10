# Tini parent-death startup race

## TL;DR

At `krallin/tini` commit `369448a167e8b3da4ca5bca0b3307500c3371828`, `-p SIGNAL` installs `PR_SET_PDEATHSIG` only after argument parsing and signal setup. Linux does not deliver a parent-death signal retroactively. If Tini's direct parent exits before that `prctl()`, Tini can install the setting successfully and continue without ever receiving the requested signal.

A reduced fixture captured the original parent identity, forced the direct parent to exit before `prctl(PR_SET_PDEATHSIG, SIGUSR1)`, and checked Tini-style blocked-signal state. The current ordering produced no pending signal in five repeated runs. A discriminator that compares `getppid()` after `prctl()` and self-queues the requested signal when the parent identity changed produced the pending signal in all five runs.

Next action: test the same startup window in an exact Tini binary or owned-fork candidate. The narrow candidate is to retain the initial parent identity early, install `PDEATHSIG`, then compensate if the parent changed during setup.

## Explain like I'm five

`-p SIGTERM` means “tell Tini when its parent dies.” Linux starts watching only after Tini asks. Tini currently asks after some startup work. If the parent dies during that startup work, Linux has already missed the event.

Literal example: `Tini starts -> remembers option work / signal setup -> parent exits -> Tini calls PR_SET_PDEATHSIG -> call succeeds -> no SIGTERM was ever generated`.

## Why care

The option exists for lifecycle coupling in PID-namespace and privilege-changing launch paths. Missing the parent-death event can leave Tini and its supervised child alive after the launcher that was supposed to own them has gone away.

## Current state

- State: `REVIEW`
- Exact working head: `krallin/tini@369448a167e8b3da4ca5bca0b3307500c3371828`
- Latest authoritative gate or artifact: local reduced fixture `repro.c`, SHA-256 `679a1e123d0e66399d25592adf0e23ea49624768fdb701d864985e79380e3dba`
- First incomplete step: run the startup-parent-exit discriminator against an exact built Tini binary or narrow owned-fork candidate
- Cleanup state: direct-parent processes exited intentionally; fixture subjects exited; no surviving processes remained under the test runner
- Next safe action: add a Tini-native test where the launcher dies after Tini starts but before the current `prctl()` point
- External-contact state: no upstream contact authorized or made

## Intent and precedent

Tini documents `-p SIGNAL` as the signal Tini should receive when its parent exits:

- https://github.com/krallin/tini/blob/369448a167e8b3da4ca5bca0b3307500c3371828/README.md#parent-death-signal

The feature entered through PR 114:

- https://github.com/krallin/tini/pull/114

The original and current test establish the steady-state case by letting Tini fully start, spawn a child, and only then having that child kill Tini's parent. That proves Linux delivers the configured signal after `PR_SET_PDEATHSIG` is already installed. It does not exercise parent exit during Tini startup.

Current source calls `prctl(PR_SET_PDEATHSIG, parent_death_signal)` in `main()` only after:

1. `parse_args()`;
2. `parse_env()`;
3. `configure_signals()`.

Only after the `prctl()` does Tini register as a subreaper, run `reaper_check()`, and spawn the supervised child.

Primary source: https://github.com/krallin/tini/blob/369448a167e8b3da4ca5bca0b3307500c3371828/src/tini.c

Historical feature patch and test: https://github.com/krallin/tini/pull/114

## Question

If Tini's direct parent exits after Tini begins execution but before `PR_SET_PDEATHSIG` is installed, is the requested `-p` signal missed, and can an initial-parent identity check distinguish and repair that startup window?

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
- Privileges: uid `0` inside the disposable execution container; fixture uses ordinary fork, signal, pipe, and `prctl()` behavior
- Container, virtual machine, or host context: disposable container
- Relevant tool versions: GCC `14.2.0`

## Baseline behavior

The reduced fixture mirrors the decisive startup lifecycle:

1. subject blocks `SIGUSR1` as Tini blocks forwarded signals;
2. subject records its direct parent's PID;
3. direct parent exits;
4. subject waits briefly to make the parent-exit-before-`prctl()` ordering deterministic;
5. subject calls `prctl(PR_SET_PDEATHSIG, SIGUSR1)`;
6. subject checks whether `SIGUSR1` is pending.

Linux reports a successful `prctl()` while no parent-death signal becomes pending because the parent had already exited.

## Hypothesis or candidate

The invariant is: when `-p SIGNAL` is requested and Tini observed a live direct parent during its own startup, a parent death during the setup interval must result in the same requested signal becoming observable to Tini.

Candidate mechanism for review:

- capture the initial parent PID as early as practical in `main()`;
- install `PR_SET_PDEATHSIG` after parsing identifies the requested signal;
- immediately compare `getppid()` with the captured parent identity;
- if the identity changed during setup, queue the requested signal to Tini itself so the existing signal path observes it.

This preserves the configured signal value and current post-install parent-death behavior. The remaining tiny interval before the first parent-PID observation is an explicit boundary.

## Reproduction

Compile and run [`repro.c`](repro.c):

```sh
cc -O2 -Wall -Wextra -Werror repro.c -o repro
./repro
```

Five repeated authoritative runs produced:

```text
current-order: SIGUSR1-pending=0
ppid-check-order: SIGUSR1-pending=1
current-order: SIGUSR1-pending=0
ppid-check-order: SIGUSR1-pending=1
current-order: SIGUSR1-pending=0
ppid-check-order: SIGUSR1-pending=1
current-order: SIGUSR1-pending=0
ppid-check-order: SIGUSR1-pending=1
current-order: SIGUSR1-pending=0
ppid-check-order: SIGUSR1-pending=1
```

## Results

The baseline reduced model demonstrates Linux's non-retroactive `PDEATHSIG` behavior: the setting can be installed after the parent is already gone and no requested signal is generated.

The candidate discriminator demonstrates that retaining the original parent identity and checking it after `prctl()` detects the forced startup-parent-exit ordering. Self-queuing the requested signal produces the Tini-style pending signal state in every repeated run.

The upstream test acts as the adjacent negative control: when parent death happens only after setup is complete, kernel-delivered `PDEATHSIG` is the expected mechanism and already has coverage.

## Interpretation

Demonstrated behavior: `PR_SET_PDEATHSIG` does not repair a parent death that occurred before the call, and Tini currently performs no parent-identity check after installing it.

Source-supported consequence: a launcher that dies during Tini's parse/signal-configuration window can leave `-p` ineffective for that death event.

Design choice for review: an early parent-PID capture plus post-`prctl()` identity check closes the demonstrated interval from the capture point through installation. Exact placement and behavior for unusual reparenting contexts should be challenged with a Tini-native test before promotion.

## Evidence boundary

- The exact Tini source and feature history were read at commit `369448a167e8b3da4ca5bca0b3307500c3371828` through the GitHub connector.
- The local execution environment could not clone or build Tini because direct DNS access to GitHub was unavailable.
- Execution used a reduced C fixture for Linux `prctl()`, parent identity, blocked signals, and deterministic parent-exit ordering; the full Tini binary was not executed.
- The fixture establishes behavior on Linux 6.18.35 x86_64.
- PID-namespace teardown, SELinux/AppArmor credential transitions, and `unshare` integration were not executed.
- The candidate does not claim to detect a parent that dies before the first parent-PID observation in Tini's process.
- No upstream issue or patch was created.

Reopen triggers: an exact Tini startup test showing another mechanism already detects this interval, a reparenting case where the proposed identity check causes an incorrect signal, or current upstream work that already closes the gap.

## Next step

Human reviewer chooses whether to promote this into an owned-fork candidate. The supporting evidence is the exact `main()` call order, the steady-state scope of PR 114's test, and the deterministic baseline/candidate result in `repro.c`.

If promoted, build a native test that makes the launcher exit before the current `prctl()` point and asserts that the requested signal is still observed without changing steady-state behavior.

## Authority

No upstream Tini issue, email, pull request, patch submission, comment, review, or other interaction has been authorized or made. Repository-file links are retained as research evidence only.
