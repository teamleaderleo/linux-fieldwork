# procps pkill --mrelease signal-state boundary

## TL;DR

`procps-ng/procps` at commit `9196b59143f6a4d7d54c8a128d753269e496f458` sends the requested signal through a pidfd and, when `--mrelease` is selected, immediately calls `process_mrelease(pidfd, 0)`. Linux only accepts `process_mrelease()` once the target is already dying/exiting (or its address space was already reaped).

A disposable local probe on Linux `6.18.35` x86_64 confirmed the boundary: immediate mrelease succeeded 5/5 after default-action `SIGTERM` and 5/5 after `SIGKILL`, but failed with `EINVAL` 5/5 when `SIGTERM` was caught by a handler that exited 300 ms later and 5/5 when `SIGTERM` was ignored.

This does **not** establish a kernel defect. It establishes a user-visible semantic boundary in `pkill --mrelease`: a signal can be delivered successfully while the immediate memory-release step fails because the process has not entered the kernel's dying state yet. Current `pkill` source treats such a non-`ESRCH` mrelease failure as command failure even though the signal was delivered.

The next useful action is to run the exact current procps binary built from the reviewed head against the same fixture and decide whether the intended CLI contract should (a) document that `--mrelease` is reliable only once the chosen signal has made the target dying, (b) restrict/recommend fatal signals such as `SIGKILL`, or (c) wait/retry only for a narrowly defined transition without turning graceful termination into an unbounded wait.

## Explain like I'm five

`pkill --mrelease` does two things: first it sends a signal, then it asks Linux to tear down the process's memory immediately.

Linux says yes to the second request only when the process is already on its way out. A normal `SIGTERM` with the default action puts the process into that state quickly enough that the request works. But if the program catches `SIGTERM` to do cleanup first, the signal was delivered successfully while the process is still alive, so Linux rejects the immediate memory-release request with `EINVAL`.

`pkill` currently turns that second-step failure into exit status 1.

## Why care

`SIGTERM` is `pkill`'s default signal and is commonly caught for graceful shutdown. A caller using `--mrelease` can therefore see a failing `pkill` result after a successfully delivered termination request solely because the target has not crossed the kernel's mrelease eligibility boundary yet.

That distinction matters to scripts: "signal delivery failed" and "signal delivered, but immediate memory reclamation was not yet legal" are different outcomes.

## Source boundary

### procps

- Project: `procps-ng/procps`
- Reviewed revision: `9196b59143f6a4d7d54c8a128d753269e496f458`
- Reviewed file: `src/pgrep.c`
- Reviewed manual: `man/pgrep.1`
- Feature-introduction commit: `0da7bd30a229d56f69e44ab5477cdf0b3f4bd56a`
- Current reviewed head date from repository history: 2026-07-07

### Linux kernel

- Project: `torvalds/linux`
- Reviewed revision: `d58772d8520c7ef247c4b95c9bd76d3a25da9ff5`
- Reviewed file: `mm/oom_kill.c`
- Reviewed selftest: `tools/testing/selftests/mm/mrelease_test.c`

### Local execution environment

- Kernel: `Linux 6.18.35` x86_64
- Compiler: `gcc (Debian 14.2.0-19) 14.2.0`
- libc: `glibc 2.41`
- Privileges: ordinary disposable process execution; no external targets, services, credentials, or persistent system changes
- Fixture: [`mrelease_probe.c`](mrelease_probe.c)

## Bounded question

What does `pkill --mrelease` mean when the selected signal is successfully delivered but the target has not yet entered a state that Linux accepts for `process_mrelease()`?

## Invariant under review

A command result should distinguish failure to signal the target from failure to reclaim memory after successful signal delivery, and its documentation should make the lifecycle requirement for mrelease understandable to callers.

## Operation owners

- `pkill` owns target selection, pidfd opening, signal delivery, invocation of `process_mrelease()`, warnings, and final exit status.
- Linux `process_mrelease()` owns the eligibility decision for whether the target address space may be reaped.
- The target process owns userspace signal-handler behavior before it enters exit.

## Source observations

### 1. pkill performs mrelease immediately after successful signal delivery

At the reviewed procps head, the `PKILL` loop:

1. opens a pidfd for each selected process;
2. sends the requested signal using `execute_kill()`;
3. increments `kill_count` when signal delivery succeeds;
4. if `--mrelease` is enabled, immediately calls `process_mrelease(pidfd, 0)`;
5. treats every mrelease failure other than `ESRCH` as `mrelease_failed = true`;
6. returns exit status 1 if any such failure occurred.

There is no wait for the signal handler or for a transition into exit state between signal delivery and mrelease.

### 2. SIGTERM is still the default signal

`opt_signal` is initialized to `SIGTERM`. The `--mrelease` option does not change the signal and does not reject signals that may be caught, ignored, or otherwise non-fatal at the moment of delivery.

### 3. Linux explicitly rejects a live/non-exiting process

At the reviewed Linux head, `process_mrelease()` obtains the target task and its `mm`, then calls `task_will_free_mem(p)`.

If that predicate is false and `MMF_OOM_SKIP` is not already set, the syscall returns `-EINVAL`.

`task_will_free_mem()` requires the task and all relevant sharers of its address space to already be dying/exiting. Its core predicate returns true for a group exit or a final thread carrying `PF_EXITING`; it does not treat mere successful signal queueing as sufficient.

### 4. The kernel selftest supplies a strong negative control

The Linux `mrelease_test.c` selftest explicitly calls `process_mrelease()` on a live child before sending `SIGKILL` and requires `EINVAL`.

It then sends `SIGKILL` and calls `process_mrelease()` immediately, treating success as the normal result and `ESRCH` as the race where the child exited too soon to reap.

That selftest supports the interpretation that mrelease eligibility is a lifecycle state, not simply proof that some signal was delivered.

## Executed distinguishing probe

The checked-in fixture creates only disposable child processes and exercises the same syscall sequence relevant to current `pkill`:

```text
pidfd_open(child)
pidfd_send_signal(pidfd, signal)
process_mrelease(pidfd, 0)
```

The target allocates 64 MiB so there is real anonymous memory to reap. Four cases run five times each:

1. default-action `SIGTERM`;
2. `SIGTERM` caught by a handler that waits 300 ms then exits;
3. ignored `SIGTERM`;
4. `SIGKILL`.

Command used:

```sh
gcc -O2 -Wall -Wextra mrelease_probe.c -o mrelease_probe
./mrelease_probe
```

## Observed results

```text
default SIGTERM          send=0/ok mrelease=0/ok   x5
handler-delayed SIGTERM  send=0/ok mrelease=-1/EINVAL x5
ignored SIGTERM          send=0/ok mrelease=-1/EINVAL x5
SIGKILL                  send=0/ok mrelease=0/ok   x5
```

The handler-delayed case is the important discriminator: signal delivery succeeded, the process did eventually exit because of its SIGTERM handler, but the immediate mrelease request was too early under the kernel contract.

## Interpretation

### Demonstrated behavior

On this Linux environment, successful signal delivery does not imply immediate eligibility for `process_mrelease()` when userspace handles or ignores the signal.

### Source-supported procps consequence

The reviewed procps control flow would classify the handler-delayed/ignored `EINVAL` case as `mrelease_failed` and return exit status 1 even though `execute_kill()` succeeded and `kill_count` was incremented.

This consequence is source-derived rather than executed against a binary built from the exact reviewed procps head; the local system's installed procps is older and does not expose `--mrelease`.

### Not established as a defect yet

A failure exit may be intentional when the user explicitly requested both signal delivery and immediate release. The open design question is whether current documentation and result semantics make the lifecycle prerequisite clear enough, especially because `SIGTERM` is the default and commonly handled.

## Cross-context pass

### Default-action SIGTERM

**Discriminator:** kernel default disposition is terminating.

Observed: mrelease succeeds immediately 5/5. This is the positive control showing the fixture does not simply force every mrelease call to fail.

### Handler-delayed SIGTERM

**Discriminator:** signal delivery succeeds, but userspace runs before exit.

Observed: mrelease fails `EINVAL` 5/5 even though the handler exits 300 ms later.

This is the strongest semantic boundary because it separates "delivered termination request" from "already dying enough for mrelease."

### Ignored SIGTERM

**Discriminator:** target never enters exit because of the requested signal.

Observed: mrelease fails `EINVAL` 5/5. This is expected and prevents overclaiming that any delivered signal should permit memory reclamation.

### SIGKILL

**Discriminator:** uncatchable fatal group-exit signal.

Observed: mrelease succeeds immediately 5/5. This matches the kernel selftest pattern and is the strongest negative control against a generic ordering bug.

## Next exact probe

Build `procps-ng/procps` at `9196b59143f6a4d7d54c8a128d753269e496f458` and run its `pkill --mrelease` against two tiny named fixtures:

1. a default-action target;
2. a SIGTERM handler that records receipt, waits briefly, and exits.

Record:

- pkill exit status;
- stderr warning;
- handler receipt marker;
- target exit status;
- pidfd/mrelease syscall results under `strace` if available;
- whether the target is still alive when pkill exits;
- an immediate clean rerun.

Expected distinguishing result from current source: default-action SIGTERM exits 0; handler-delayed SIGTERM warns about `process_mrelease` and exits 1 even though the signal was delivered.

## Candidate dispositions

If exact-binary execution matches the source prediction, choose among these narrow designs rather than broadening the patch prematurely:

- **Documentation boundary:** explain that mrelease only succeeds once the signal has put the target into a dying/exiting state and recommend `SIGKILL` when deterministic immediate reclamation is required.
- **Result boundary:** preserve successful signal delivery distinctly from reclamation failure, if the CLI contract values the kill result more than the optional reclamation result.
- **Bounded transition handling:** consider a narrowly bounded retry only for `EINVAL` where the target is expected to become dying, with strict timeout/exit semantics. This needs care because waiting can defeat the option's immediate-reclamation purpose and a caught signal may intentionally keep the process alive.

No source candidate is recommended before exact-current-binary execution clarifies the intended CLI contract.

## Evidence boundary

Established:

- exact current procps source ordering and exit-status decision at the reviewed head;
- exact Linux kernel eligibility predicate at the reviewed kernel head;
- kernel selftest expectations for live child vs post-`SIGKILL` child;
- local syscall behavior across default SIGTERM, handler-delayed SIGTERM, ignored SIGTERM, and SIGKILL on Linux 6.18.35;
- positive and negative controls;
- no upstream contact occurred.

Not established:

- execution of a procps binary built from `9196b59143f6a4d7d54c8a128d753269e496f458`;
- maintainer intent for handler-delayed SIGTERM beyond the feature commit and current manual wording;
- behavior on older kernels that support `process_mrelease()`;
- whether libc wrappers versus direct syscalls alter any error presentation;
- whether a retry/wait policy would be desirable upstream.

## Stop / reopen rule

Do not call this a generic `process_mrelease()` race: default terminating signals and SIGKILL passed the immediate path.

Reopen as a concrete procps defect if exact-current-binary execution confirms a misleading or incompatible command result for handler-delayed termination and source/history gives no intentional contract for that result. Otherwise retain it as a documented lifecycle boundary.

## External-contact state

No upstream greenlight was given. No upstream issue, pull request, comment, review, email, or other external contact was created.
