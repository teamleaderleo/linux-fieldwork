# mkosi repeated-interrupt escape can stall on a signal-resistant child

## TL;DR

At upstream `systemd/mkosi` commit `f7401bdc8d23486bb346790dc92508381a062f3b`, the top-level signal handler records the first `SIGINT`, `SIGTERM`, or `SIGHUP` in a process-global `INTERRUPTED` latch and returns immediately for later handled signals. Both `spawn()` and `fork_and_wait()` can enter a second blocking child wait after that first interrupt. A reduced fixture reproduces the result: when the child ignores the forwarded signal, later `SIGINT` and `SIGTERM` deliveries leave both parent and child alive.

This conflicts with mkosi's documented 2020 interrupt intent: the first Ctrl-C should allow graceful child exit, while a second Ctrl-C should let the user escape a hanging subprocess. The next useful action is a full mkosi integration reproduction on the pinned revision, followed by a focused design review of repeat-interrupt escalation semantics.

## Explain like I'm five

mkosi starts another program and waits for it. The first Ctrl-C tells that program to stop and lets mkosi wait for cleanup. If the program refuses to stop, the user presses Ctrl-C again. Current mkosi records that it has already seen an interrupt and discards the later request, while the parent stays in `wait()`.

Literal example: `child ignores SIGINT -> parent receives Ctrl-C -> parent forwards SIGINT -> child keeps running -> user sends Ctrl-C again -> parent handler returns -> parent keeps waiting`.

## Why care

A package build, image build, helper, or forked worker that blocks or masks termination signals can leave the mkosi parent unresponsive to the normal repeated-interrupt escape path. The practical consequence can be a forced `SIGKILL`, which removes mkosi's opportunity to finish ordinary cleanup and can leave transient state for a later invocation.

## Current state

- State: `REVIEW`
- Exact working branch: `research/mkosi-repeat-interrupt-hang`
- Evidence-producing fixture commit: `6ad887b33162a5f164786192574a7631d298a63d`
- Owning Fieldwork issue: `#552`
- Latest authoritative gate or artifact: reduced `spawn()` + `fork_and_wait()` positive/negative-control run recorded below
- First incomplete step: full mkosi invocation on the exact upstream revision
- Cleanup state: fixture forcibly removed signal-resistant parent/child processes after observation; no retained processes
- Next safe action: reproduce through real mkosi, then test an escalation candidate against both duplicate-delivery and later-user-interrupt cases
- External-contact state: no upstream contact authorized or made

## Intent and precedent

The historical behavior is unusually explicit.

- `systemd/mkosi@74c08c979c9c60cbda0ec70e52ba3ebb28519589` introduced delayed first-interrupt handling so a subprocess could exit cleanly and stated that a second Ctrl-C should still let the user exit a hanging subprocess.
- `systemd/mkosi@b1a34444c3f83279d8c5c3e9f9b7d769bbf035da` added graceful `SIGTERM` handling.
- `systemd/mkosi@ca2f63f9fe97bbf5aef1ef2811fcc936c9e2de4c` added the same graceful handling for `SIGHUP`.
- `systemd/mkosi@b3be819fe77ac8a07ad0609ab258a9b830abd04e` moved away from foreground process-group manipulation. It added the global `INTERRUPTED` latch because a forked parent and child could both receive the same terminal SIGINT and the parent could then forward another SIGINT, producing duplicate `KeyboardInterrupt` delivery.
- `systemd/mkosi@b07bf6ddef931f58d117161e266a020c689708c2` added the pre-finally `proc.wait()` in `spawn()` so an interrupt during a wait would not leave a child alive.

The current combination solves duplicate delivery of the first interrupt by making the process handler one-shot. It also removes the old distinction between duplicate delivery from one interrupt event and a genuinely later request to escalate out of a hung wait.

A nearby closed upstream issue, `systemd/mkosi#3726`, involved stale VM state after Meson interrupted mkosi and escalated to `SIGKILL` after roughly 0.5 seconds. Maintainer discussion attributed that case to the external runner preventing mkosi from finishing cleanup. The present finding is a different mechanism: mkosi itself remains alive while later handled signals are discarded.

## Question

After mkosi forwards the first interrupt to a child that remains alive, can a later `SIGINT`, `SIGTERM`, or `SIGHUP` make the mkosi parent leave its blocking wait?

## Source

- Project: `systemd/mkosi`
- Requested revision: `main`, inspected 2026-08-11
- Resolved commit: `f7401bdc8d23486bb346790dc92508381a062f3b`
- Candidate source commit: none; this record establishes the defect mechanism before choosing an escalation policy
- Source files inspected: `mkosi/__main__.py`, `mkosi/run.py`, `mkosi/sandbox.py`
- Local source path: none; source was read through the GitHub connector
- Import metadata: none; the execution runtime could not resolve `github.com`, so a source-tree clone was unavailable

## Environment

- Distribution and release: Debian GNU/Linux 13
- Kernel and architecture: Linux `6.18.35`, x86_64
- Shell: Bash `5.2.37`
- Privileges: uid 0 / gid 0; the fixture itself needs no privileged operation
- Container, virtual machine, or host context: disposable tool runtime
- Relevant tool versions: Python `3.13.5`

## Baseline behavior

Current `mkosi/__main__.py` has a process-global `INTERRUPTED` flag. `onsignal()` raises `KeyboardInterrupt` only for the first handled signal and returns for every later `SIGINT`, `SIGTERM`, or `SIGHUP`.

Current `mkosi/run.py` contains two adjacent wait paths with the same decision boundary:

1. `spawn()` catches `KeyboardInterrupt`, forwards `SIGINT` to the child, re-raises, and then waits again in `finally` after sending `SIGCONT`.
2. `fork_and_wait()` catches `KeyboardInterrupt`, forwards `SIGINT` to the forked child, and immediately performs another blocking `waitpid()`.

If the child terminates on the first forwarded `SIGINT`, both paths converge normally. If the child keeps running, the parent enters the secondary wait after its one-shot signal latch has already been set.

## Hypothesis or candidate

Hypothesis: the global one-shot signal latch suppresses all later user or service escalation requests while either secondary wait remains blocked.

The distinguishing controls are:

- negative control: child uses the default SIGINT disposition and exits after the first forwarded interrupt;
- positive case: child ignores `SIGINT` and `SIGTERM`, keeping the secondary wait live while the harness sends a second SIGINT and then SIGTERM to the parent;
- adjacent context: execute the same discriminator through both `spawn()`-style `Popen.wait()` control flow and `fork_and_wait()`-style `waitpid()` control flow.

A candidate fix remains intentionally open. The desired policy has to preserve graceful handling and suppress duplicate delivery from one interrupt wave while restoring a meaningful later escape request.

## Reproduction

The retained fixture copies the relevant current control-flow policy into a standard-library-only process test. It performs no mounts, package operations, namespace changes, network access, or external-system interaction.

```sh
python3 investigations/mkosi-repeat-interrupt-hang/reproduce.py
```

For each parent path it runs a default-signal child and a signal-resistant child. The harness records parent/child liveness after each signal and then forcibly kills any survivors so the test leaves no process behind.

## Results

Observed output on the environment above:

```text
spawn / default
SIGINT#1: parent_alive=False child_alive=False
spawn / ignore
SIGINT#1: parent_alive=True child_alive=True
SIGINT#2: parent_alive=True child_alive=True
SIGTERM#3: parent_alive=True child_alive=True
fork / default
SIGINT#1: parent_alive=False child_alive=False
fork / ignore
SIGINT#1: parent_alive=True child_alive=True
SIGINT#2: parent_alive=True child_alive=True
SIGTERM#3: parent_alive=True child_alive=True
```

Observed result:

- The negative controls exit after the first interrupt and leave no child alive.
- The signal-resistant cases keep both parent and child alive after the first SIGINT, second SIGINT, and later SIGTERM.
- The harness then uses SIGKILL strictly for fixture cleanup.
- The same distinction appears through both current wait patterns.

## Interpretation

### Demonstrated behavior

The reduced fixture demonstrates that the current one-shot handler policy plus the current secondary-wait patterns can make later handled signals ineffective once the first `KeyboardInterrupt` has been consumed. The result reproduces in both adjacent wait contexts and disappears when the child accepts the first forwarded interrupt.

### Intent evidence

Historical mkosi source history explicitly preserved a second Ctrl-C as the escape path for a hanging subprocess. The 2025 signal-routing rewrite explains why duplicate first-signal delivery needed suppression, but its global one-shot latch also suppresses distinct later interrupts.

### Plausible consequence

A real mkosi invocation that reaches one of these waits with a signal-resistant child can require an unhandled signal such as SIGKILL to terminate the parent. Forced termination can bypass ordinary mkosi cleanup. This consequence is source-supported and fixture-supported, while the complete real-mkosi process tree still needs an integration reproduction.

### Open design choice

The fix should distinguish duplicate delivery associated with the same interrupt handling sequence from a later escalation request. Exact escalation behavior—raise immediately, terminate the child more strongly, restore default handling, or another bounded policy—needs testing against real mkosi child ownership and cleanup behavior before choosing a patch.

## Evidence boundary

This investigation currently establishes the signal/wait control-flow defect with a reduced executable fixture and exact current source/history inspection.

Limits:

- A full checkout of `systemd/mkosi` was unavailable because the runtime could not resolve `github.com` for clone operations.
- No real `mkosi build`, `mkosi sandbox`, package-manager transaction, VM, namespace, mount, or sandbox integration run was executed.
- The fixture sends signals directly to the parent and models the forwarding logic; it does not recreate terminal foreground process-group delivery.
- The positive child deliberately ignores SIGINT/SIGTERM. Real helpers can reach equivalent resistance through explicit handlers, blocked signals, or stalled cleanup, but those concrete upstream children have not been catalogued here.
- No candidate patch or project test suite has been run.
- No claim is made that closed upstream issue `#3726` is caused by this defect.

## Next step

Run the pinned mkosi revision in an environment with the source tree available and invoke a deliberately signal-resistant synthetic child through a real mkosi path. Record parent/child/process-group state after first SIGINT, second SIGINT, and SIGTERM, then rerun cleanly.

If the full invocation matches the reduced result, prototype the smallest escalation policy that satisfies all of these checks:

1. a normal child gets the first graceful interrupt and exits cleanly;
2. duplicate delivery from one terminal interrupt does not produce a second accidental `KeyboardInterrupt`;
3. a genuinely later Ctrl-C or termination request can escape a signal-resistant child wait;
4. both `spawn()` and `fork_and_wait()` follow the same policy;
5. cleanup and rerun state remain clean.

The human review decision is whether the reduced two-path reproduction plus explicit historical intent is sufficient to promote this into a mkosi candidate-fix investigation before full integration execution.

## Authority

No upstream issue, email, pull request, patch submission, comment, review, or other interaction has been authorized or created. All work remains inside Linux Fieldwork.
