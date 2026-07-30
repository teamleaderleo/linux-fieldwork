# Services, Processes, and Resources

## In simple words

This programme studies Linux process ownership across service managers, cgroups, subprocess trees, runtime files, cancellation, restart, shutdown, and resource cleanup.

## Current direction

- **Mapped:** [LF-20 — systemd stop, timeout, and descendant cleanup](lanes/LF-20-systemd-stop-timeout-descendant-cleanup/brief.md)
- **Mapped:** [LF-22 — cgroup v2 delegation and resource cleanup](lanes/LF-22-cgroup-v2-delegation-cleanup/brief.md)
- **Mapped:** [LF-23 — cancellation, subprocess, and file-descriptor cleanup](lanes/LF-23-cancellation-subprocess-fd-cleanup/brief.md)
- **Inbox:** LF-21 — tmpfiles and sysusers package lifecycle
- **Inbox:** LF-24 — shutdown and soft-reboot persistence

## First sequence

Run LF-23 on the current runner. Use that fixture design to inform LF-20 in a systemd VM. Check runner cgroup delegation before opening LF-22 execution work.

## Candidate targets

`mmdebstrap`, systemd service management, cgroup v2, package builders, test runners, image tools, shell and Python orchestration code.

## Authority

Programme mapping grants no upstream-contact authority.