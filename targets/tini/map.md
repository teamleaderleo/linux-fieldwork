# Tini Target Map

## In simple words

Tini is a small container init that sits directly on Linux process, signal, process-group, subreaper, and parent-lifecycle behavior. Its code is compact enough for exact source reasoning, while its job crosses several timing and ownership boundaries that fit Linux Fieldwork's lifecycle lenses.

This map was created after one scout produced two separate startup-lifecycle investigations at the same exact upstream revision.

## Source identity

- Canonical repository: `https://github.com/krallin/tini.git`
- Requested revision: current repository head observed on 2026-08-11
- Resolved commit: `369448a167e8b3da4ca5bca0b3307500c3371828`
- Local source: no imported tree yet; exact files were read through the connected GitHub repository
- Import metadata: none

## Why it recurs

Tini deliberately owns several Linux lifecycle translations:

- blocked-signal collection and forwarding;
- direct-child versus process-group delivery;
- child process-group creation and tty foreground ownership;
- zombie reaping and optional subreaper registration;
- child exit/signal translation into Tini exit status;
- parent-death coupling through `PR_SET_PDEATHSIG`;
- startup ordering between configuration, fork, exec, signal delivery, and cleanup.

Those are compact examples of the same ownership, ordering, and cleanup questions that recur in larger supervisors and container runtimes.

## Relevant programmes

- [`Services, processes, and resources`](../../programmes/services-resources/STATUS.md)
- [`Rootless execution, namespaces, and mounts`](../../programmes/rootless-execution/STATUS.md)

## Mapped lanes

- [LF-23 — cancellation, subprocess, and file-descriptor cleanup](../../programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/brief.md)

## Existing investigations

- [Process-group startup signal race](../../investigations/tini-process-group-startup-signal-race/README.md)
- [Parent-death startup race](../../investigations/tini-parent-death-startup-race/README.md)

## Source and test surfaces

Begin with:

- `src/tini.c`: `configure_signals()`, `spawn()`, `isolate_child()`, `wait_and_forward_signal()`, `reap_zombies()`, and `main()` startup order;
- `test/run_inner_tests.py`: steady-state signal, process-group, reaping, and parent-death orchestration;
- `test/pgroup/`: process-group propagation fixture;
- `test/pdeathsignal/`: parent-death fixture;
- historical PR 16 for process-group killing and PR 114 for parent-death signaling.

High-value adjacent discriminators include signal arrival before child readiness, child exit during forwarding, tty/non-tty process-group setup, parent exit during argument and signal setup, subreaper versus PID-1 mode, and immediate clean rerun.

## Current evidence boundary

The first two investigations use exact upstream source/history plus local reduced syscall fixtures on Debian 13, Linux 6.18.35 x86_64. The local shell could not clone GitHub, so a full exact Tini binary has not yet executed for these startup windows. Treat both findings as source-supported, syscall-reproduced candidates awaiting Tini-native confirmation.

## Policy boundary

This target map authorizes research inside Linux Fieldwork only. No Tini issue, email, pull request, patch submission, comment, review, or other upstream interaction is authorized by this map.
