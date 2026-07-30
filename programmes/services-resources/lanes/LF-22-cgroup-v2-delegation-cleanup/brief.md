# LF-22 — Cgroup v2 Delegation and Resource Cleanup

## In simple words

Cgroup v2 gives nested workload managers a delegated subtree with strict controller and ownership rules. This lane tests setup, limit hits, process movement, partial failure, and complete teardown.

## Programme

[`Services, processes, and resources`](../../STATUS.md)

## State

`mapped` — ready after a cgroup capability survey.

## Question

Can delegated workloads create subgroups, apply controllers, hit limits, move processes, and disappear without leaving unusable controller state?

## Why this could matter

A failed or incomplete delegation can block nested managers, misattribute resource failures, let processes escape accounting, or leave undeletable groups.

## Likely targets

Systemd resource control, container managers, CI executors, user services, and direct cgroup v2 consumers.

## First probe

Create a delegated subtree, enable available CPU, memory, pids, and I/O controls, induce limit hits and process exit, then verify controller state, process placement, ownership, and directory cleanup.

## Environment

Privileged CI or a VM with a writable delegated cgroup hierarchy.

## Promotion signal

Promote when a manager cannot recover after partial setup, diagnostics identify the wrong layer, processes escape accounting, or empty groups remain undeletable.

## Stop signal

Close when delegation and teardown follow the kernel and manager contracts under every tested path.

## Expected outputs

- runner capability survey;
- delegated subtree fixture;
- limit and cleanup matrix;
- candidate investigation or retained environment boundary.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.