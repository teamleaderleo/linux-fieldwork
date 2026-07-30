# Research Rounds

This directory holds broad Linux and Debian landscape maps that identify possible investigation lanes before any one lane becomes active work.

## In simple words

A research round surveys a region, records promising questions, and proposes the smallest useful probes. It helps choose work without treating every interesting mechanism as a defect.

## Current round

- [`2026-07-30-linux-landscape.md`](2026-07-30-linux-landscape.md) — 34 candidate lanes across rootless execution, Debian packages, filesystems, disk images, services, resources, security, networking, boot, and kernel-facing work.

The active short index lives in [`../RESEARCH_LANES.md`](../RESEARCH_LANES.md).

## Lane states

- **Mapped** — the question and first probe are recorded.
- **Ready** — source target and execution environment are clear enough to begin a bounded scout.
- **Investigating** — an exact revision and owned investigation path exist.
- **Retained** — useful finding or note exists without a candidate change.
- **Deferred** — valuable question needs a VM, hardware, custom kernel, unavailable source, or another dependency.
- **Closed** — evidence supports existing behavior or the consequence is too weak to justify more work.

## Promotion

Before opening an investigation:

1. select one bounded question;
2. name the source tree and exact revision to import or inspect;
3. state the environment and privilege requirements;
4. design one probe with distinguishing outcomes;
5. identify the consequence that would justify continued work;
6. define a stop condition.

Then create an investigation from [`../templates/investigation.md`](../templates/investigation.md) and link it from the relevant landscape round.

## Research-round discipline

A landscape file may contain broad possibilities. Strong technical claims belong in `investigations/` with commands, results, revisions, and evidence limits. General lessons discovered along the way belong in `notes/`.
