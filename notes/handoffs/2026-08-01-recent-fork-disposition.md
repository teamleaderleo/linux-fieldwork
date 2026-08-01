# Recent fork disposition — 2026-08-01

## TL;DR

The recent Linux-oriented forks do not justify another broad candidate scan. Two forks map to exact retained work:

- `teamleaderleo/util-linux` removes the controlled-source blocker for issue #397 unit 23 and now carries an observable fork-only native test carrier;
- `teamleaderleo/libarchive` already contains completed evidence for an overlap review whose public implementation carrier remains open.

`systemd`, BuildKit, and nixpkgs currently map only to formal or broad lanes. Starting source changes there now would expand the backlog before the priority-zero closeout work is cleared.

## Why care

A fork is an execution surface, not a bounded question. Treating every new fork as a request for fresh exploration would recreate the exact backlog issue #397 is trying to close.

## Exact inventory and disposition

### mmdebstrap

```text
repository: teamleaderleo/mmdebstrap
candidate branch: linux-fieldwork/unit-05-run-qemu-result-precedence
candidate head: 6efe6945f9f89cff57fe84086ede7bda747c3879
Linux Fieldwork packet head: 4dc764d20e9651b9f7b18d036582fb54d541e12e
state: HOLD
```

The source and reduced lifecycle evidence are saturated. Remaining work is canonical Salsa reconciliation and upstream-native QEMU execution. No additional mmdebstrap source exploration is justified until those gates move.

### util-linux

```text
repository: teamleaderleo/util-linux
stable fix: 3cd5f1dd69495864f3046cdbcefa104786fe5a27
fork-only CI base: linux-fieldwork/unit-23-lscpu-cpuset-native-base
base head: 7669d148543822d56ffffa31d2f399f078f8e117
fork-only CI head: linux-fieldwork/unit-23-lscpu-cpuset-native-gate
head: 95ebc67e521195741040ffebb58756b259fb69b2
internal draft PR: teamleaderleo/util-linux#1
focused run: 30691835019 — queued
repository build run: 30691835043 — queued
```

The internal PR is an execution carrier only. It builds through util-linux's own CI scripts, runs the project-native `lscpu` suite, and runs the deterministic malformed-cpuset matrix twice. It changes no product source beyond the already-landed stable fix.

Disposition: continue exact run classification when hosted execution starts. This is the only new fork that immediately advances a retained priority-zero unit.

### libarchive

```text
repository: teamleaderleo/libarchive
controlled evidence PR: #1 — merged and closed
exact evidence head: 0ff0fe951b3bfe264875d0b4bf1e0dcc23088edd
public overlap: libarchive/libarchive#3070 — open
public overlap head: c79a8b8a221022ebc5b23accdb06bc14923c4082
```

The public PR remains active. Its discussion now explicitly recognizes that 7-Zip streamability depends on central-directory placement: some archives can be read forward while others require backward access. That matches the retained Fieldwork list-versus-extract result.

Disposition: retain as overlap review. Do not create a competing product implementation while the public carrier remains active.

### systemd

Existing Fieldwork state:

- target state: `inbox`;
- formal lane: `LF-20-systemd-stop-timeout-descendant-cleanup`;
- adjacent cgroup cleanup lane: `LF-22-cgroup-v2-delegation-cleanup`;
- no exact investigation or selected source correction found in the current repository map.

Disposition: keep at lane level. A fork alone does not satisfy the bounded-question and distinguishing-probe gate.

### BuildKit

Existing Fieldwork state:

- mentioned only in broad ecosystem contribution mapping;
- no exact investigation, selected defect, or retained candidate found.

Disposition: no source work during the priority-zero closeout initiative.

### nixpkgs

Existing Fieldwork state:

- package-collection candidate-harvesting lane `LF-35`;
- downstream-patch-retirement lane `LF-36`;
- no exact current source correction selected for this fork.

Disposition: keep as programme input. Do not turn the fork into an unbounded package scan.

## Decision

The sense of exhaustion is technically accurate: the mmdebstrap and libarchive work has reached evidence or overlap boundaries, rather than lacking more ideas.

The next useful sequence is narrow:

1. classify the util-linux fork-only native runs;
2. complete or retain the exact issue #397 units already in progress;
3. resist opening systemd, BuildKit, or nixpkgs source work until a bounded carrier is promoted through the existing lane rules.

## Evidence boundary

This record inventories accessible controlled forks against existing Linux Fieldwork records. It does not claim a complete review of every file or upstream issue in each fork. It selects whether a current durable carrier exists and whether the fork removes a named blocker.

## Authority

External contact authorized: `false`.

The util-linux PR and branches are inside the controlled fork. No canonical util-linux, libarchive, systemd, BuildKit, nixpkgs, or mmdebstrap issue, pull request, comment, review, email, or patch submission was created by this pass.
