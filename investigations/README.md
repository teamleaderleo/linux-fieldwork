# Investigations

This directory holds bounded Linux and Debian questions supported by repeatable evidence.

Each investigation should identify the exact source or system boundary, environment, baseline behavior, distinguishing hypothesis or candidate change, commands, observed results, interpretation, evidence limits, next step, and upstream-contact authority.

Start with [`../templates/investigation.md`](../templates/investigation.md).

## Naming

Use a short project-and-question directory name, such as:

- `mmdebstrap-unwritable-tmpdir/`
- `systemd-service-restart-order/`
- `ext4-rename-crash-window/`

Keep scripts, fixtures, logs, and retained result notes inside the investigation directory. Large generated artifacts should be omitted or linked through a durable external artifact store.

## Completion

An investigation can finish with a candidate change, a retained finding, a follow-up question, or a negative result. Record the evidence boundary and cleanup state before calling it complete.
