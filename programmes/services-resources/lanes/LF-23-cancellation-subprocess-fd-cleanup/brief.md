# LF-23 — Cancellation, Subprocess, and File-Descriptor Cleanup

## In simple words

Linux administration tools often control many child processes, pipes, locks, sockets, and temporary paths. This lane interrupts them at defined stages and checks whether every owned resource reaches a declared final state.

## Programme

[`Services, processes, and resources`](../../STATUS.md)

## State

`mapped` — ready for a current-CI probe against the existing `mmdebstrap` workflow.

## Question

When a Linux tool is interrupted, do all child processes, pipes, temporary files, locks, sockets, and inherited descriptors reach a clean final state?

## Why this could matter

A surviving child, retained lock, blocked pipe, or misleading complete result can hang automation, corrupt reruns, or delete unrelated state during cleanup.

## Likely targets

`mmdebstrap`, package builders, test runners, image tools, and shell or Python orchestration code.

## First probe

Wrap each spawned command with observable PID and descriptor logging. Interrupt at selected stages, then inspect process trees, locks, open files, sockets, output status, and retained paths before rerunning.

## Environment

Current CI.

## Promotion signal

Promote when a child survives, a pipe prevents exit, a lock blocks rerun, output is reported as complete after cancellation, or cleanup removes state outside the owned path.

## Stop signal

Close when cancellation converges promptly on a declared partial or rolled-back result and reruns begin cleanly.

## Expected outputs

- spawn and signal map;
- interruption harness;
- process, descriptor, and path report;
- candidate investigation or retained negative result.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.