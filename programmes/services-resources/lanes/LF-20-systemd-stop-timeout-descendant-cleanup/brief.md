# LF-20 — Systemd Stop, Timeout, and Descendant Cleanup

## In simple words

A systemd unit owns processes through its cgroup and stop policy. This lane creates difficult descendant patterns and checks whether stop, restart, failure, and timeout leave the machine in the state the unit reports.

## Programme

[`Services, processes, and resources`](../../STATUS.md)

## State

`mapped` — ready when a reusable systemd VM or PID-1 testbed exists.

## Question

Under restart, stop timeout, process forking, reparenting, and signal resistance, which descendants survive and which cleanup guarantees hold?

## Why this could matter

Surviving workers, retained mounts, open files, and overlapping generations can corrupt service state or make a successful restart misleading.

## Likely targets

Systemd service management, package-provided units, daemon wrappers, and services with multi-process lifecycles.

## First probe

Create a test service that forks several descendant patterns, ignores selected signals, opens files, and mounts a temporary filesystem. Exercise start, restart, stop, failure, and timeout while recording cgroup and resource state.

## Environment

A VM or container booted with systemd as PID 1. Selected user-unit mechanics may be scouted on current CI.

## Promotion signal

Promote when descendants survive outside the intended cgroup, resources remain attached, restart overlaps old and new workers, or the unit state misrepresents the live process tree.

## Stop signal

Close when process and resource cleanup match explicit unit settings and diagnostics.

## Expected outputs

- reusable service fixture;
- process and cgroup timeline;
- resource cleanup report;
- candidate investigation or retained unit-policy map.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.