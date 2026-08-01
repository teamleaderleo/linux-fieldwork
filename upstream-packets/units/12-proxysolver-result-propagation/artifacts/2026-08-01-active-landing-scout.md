# Active landing scout — 2026-08-01

## Scope

Find projects with stronger current activity and broader maintainer coverage that could absorb the useful parts of unit 12. This is a placement assessment only. No issue, pull request, discussion, email, fork mutation, or other external contact was made.

The exact unit-12 source patch remains specific to `mmdebstrap/proxysolver`. Other projects can realistically absorb one of three separable assets:

1. the EDSP/external-solver result contract;
2. the focused exit/signal regression matrix;
3. an integration assertion that an `mmdebstrap` failure cannot become consumer success.

## Existing controlled fork

The connected GitHub installation contains the public fork:

- `teamleaderleo/mmdebstrap`
- default branch: `master`
- existing Linux Fieldwork branches for several other units
- no unit-12 candidate branch observed during this scout

This closes `NEEDS FORK`. It does not itself authorize a new branch, pull request, or upstream contact.

## Ranked landing zones

### 1. APT Developers / apt plus apt-tests — strongest contract owner

**Why it fits**

APT owns EDSP, external solver execution, and `apt-dump-solver`. The companion `apt-tests` project explicitly stores real-world EDSP and EIPP inputs for solver/planner testing. That is the cleanest home for the general contract: a wrapper or protocol participant must preserve a completed solver's nonzero or signaled result.

**Activity and ownership signals**

- team-owned Salsa namespace: `APT Developers`;
- apt tags `3.3.1`, `3.3.0`, and `3.2.0` were published within the previous three months;
- the repository has a substantial public fork network and ongoing merge-request activity;
- `apt-tests` is explicitly scoped to EDSP/EIPP solver and planner cases.

**What can be absorbed**

- a protocol-level regression fixture derived from the unit-12 0/7/SIGTERM/SIGINT matrix;
- documentation or a test asserting exact child-result semantics;
- potentially a native `apt-dump-solver` behavior fix if current APT code has an analogous gap.

**What cannot be transplanted unchanged**

The Python `proxysolver` patch is mmdebstrap-specific. APT would need a C++-native test or implementation change, not the existing patch verbatim.

**Sources consulted**

- https://salsa.debian.org/apt-team/apt
- https://salsa.debian.org/apt-team/apt/-/tags
- https://salsa.debian.org/apt-team/apt-tests

### 2. Freexian / Debusine — strongest active direct consumer

**Why it fits**

Debusine has a first-class `MmDebstrap` worker task implementing its system-bootstrap interface. It schedules mmdebstrap on workers and turns the result into Debian environment artifacts. A false-success result at this boundary can create a misleading completed work request or invalid environment artifact, so the unit-12 regression has direct operational relevance.

**Activity and ownership signals**

- organization/team-owned Salsa project;
- release history was updated in the week of this scout;
- recent releases include multiple `MmDebstrap` task fixes and features;
- the project has many active work streams, forks, tasks, workflows, and worker maintainers.

**What can be absorbed**

- a worker-task integration test injecting an mmdebstrap child failure and asserting task failure;
- signal/exit-status normalization tests at the external-task boundary;
- a minimum-mmdebstrap version or capability gate after the underlying fix is released;
- the compact fake-solver matrix as a fixture for the task test.

**Best pitch shape**

A small regression titled around “MmDebstrap task must fail when the external solver fails” is more relevant than asking Debusine to carry the proxysolver implementation patch.

**Sources consulted**

- https://freexian-team.pages.debian.net/debusine/reference/tasks/worker/mmdebstrap.html
- https://freexian-team.pages.debian.net/debusine/reference/release-history.html
- https://salsa.debian.org/freexian-team/debusine

### 3. go-debos/debos — strongest GitHub consumer and likely practical target

**Why it fits**

Debos contains a dedicated `MmdebstrapAction` and recommends the Debian `mmdebstrap` package. Its action is used to construct target root filesystems. Recent debos work specifically fixed silent-success and swallowed-error behavior in tests and actions, matching the failure class of unit 12.

**Activity and ownership signals**

- latest observed main commit: `c32dc9c9fc111322097218535daecd4c80f7b50f` on 2026-07-31;
- 818 repository commits;
- 37 open and 418 closed pull requests in the observed public view;
- July 2026 pull requests include member-authored changes;
- recent merged commits include “avoid silent failure”, “do not swallow errors”, and other result-contract repairs from several contributors;
- Debian packaging is maintained by the Debian Go Packaging Team and version 1.1.7-1 recommends mmdebstrap.

**What can be absorbed**

- an end-to-end `MmdebstrapAction` failure-propagation test;
- a test fixture that substitutes a controlled mmdebstrap/proxysolver and checks positive exit plus signal results;
- clearer action diagnostics preserving the underlying mmdebstrap result;
- a dependency-version guard after an upstream mmdebstrap release contains the source fix.

**Best pitch shape**

Lead with consumer impact and a regression test. Avoid proposing that debos vendor the mmdebstrap Python patch.

**Sources consulted**

- https://github.com/go-debos/debos
- https://github.com/go-debos/debos/pulls
- https://pkg.go.dev/github.com/go-debos/debos/actions
- https://packages.debian.org/testing/debos

### 4. Debian CI / autopkgtest — useful secondary integration owner

**Why it fits**

Autopkgtest and mmdebstrap overlap in testbed/image creation. The mmdebstrap project ships an autopkgtest QEMU builder, and Debian documentation/bug history describes mmdebstrap as an unprivileged route for creating autopkgtest QEMU images.

**Activity and ownership signals**

- Debian CI team ownership;
- releases 5.54 and 5.55 in January 2026;
- active forks and maintainer changes in 2026.

**What can be absorbed**

A smoke test that image/testbed creation fails visibly when bootstrap or solver execution fails. The exact proxysolver source patch remains outside autopkgtest's ownership.

**Sources consulted**

- https://salsa.debian.org/ci-team/autopkgtest
- https://salsa.debian.org/ci-team/autopkgtest/-/tags

## High-activity project with weak direct fit

### systemd/mkosi

Mkosi is highly active, multi-contributor, and supports APT-based Debian/Ubuntu image creation. The public view showed more than 6,500 commits and thousands of closed pull requests. However, no direct mmdebstrap dependency was established in this scout. Unit 12 should only be carried there if an analogous subprocess-result defect is found in mkosi itself. Activity alone is not enough to justify transplanting unrelated code.

Source: https://github.com/systemd/mkosi

## Recommended absorption plan

Use a three-layer route rather than searching for a single replacement maintainer:

1. **APT/apt-tests:** land or validate the general EDSP solver-result contract.
2. **mmdebstrap fork:** retain the exact proxysolver source fix and native test on a controlled unit-12 branch.
3. **Debusine and debos:** prepare consumer-level regressions proving their task/action fails when mmdebstrap's solver fails.

This creates independent pressure at the protocol, implementation, and consumer layers. It also lets the reusable test evidence survive even if the original mmdebstrap upstream remains slow.

## Suggested next safe technical work

Without contacting anyone:

1. create a unit-12 branch in `teamleaderleo/mmdebstrap` from the controlled upstream snapshot;
2. apply the composed source patch and native test there;
3. inspect Debusine's `MmDebstrap` task tests and debos's `MmdebstrapAction` tests;
4. draft one consumer regression for each project in the Linux Fieldwork workspace;
5. compare whether either consumer already preserves and exposes exact signal identity or only requires a nonzero task result.

Branch creation and external submissions require explicit authorization beyond this scout.

## External-contact state

`false; none occurred`.