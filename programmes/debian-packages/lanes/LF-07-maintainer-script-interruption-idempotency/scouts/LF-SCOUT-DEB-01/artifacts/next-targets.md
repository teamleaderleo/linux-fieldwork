# LF-07 follow-on targets

This shortlist records the next probes after the purpose-built `postinst` fixture. These are candidates only; no package-specific result is claimed here.

## 1. Alternatives-only rerun

Use a tiny package whose `postinst` registers one primary alternative and one slave link. Interrupt immediately after the alternatives database update and rerun configuration.

Why first:

- compact observable state under `/var/lib/dpkg/alternatives/`;
- clean comparison of link targets and administrative state;
- low dependency surface;
- useful control case because repeated `update-alternatives --install` should converge.

Candidate pattern: the historical `tar` package `postinst`, which installs the `rmt` alternative and slave manual-page link.

Distinguishing outcomes:

- converged alternative database and links;
- duplicate or reordered entries;
- link/database disagreement;
- recovery requiring `update-alternatives --remove` or `--auto`.

## 2. System group plus state directory

Use a package script that creates a system group and then creates a group-owned state directory. Interrupt between group creation and directory creation, then after directory creation.

Why second:

- covers identity state plus filesystem ownership;
- exposes numeric-ID drift, missing groups, wrong modes, and partial directory setup;
- recovery can be checked with `getent`, `stat`, and package status.

Candidate pattern: the Samba `postinst` sequence that creates the `sambashare` group and `/var/lib/samba/usershares` with group ownership and mode `1770`.

Distinguishing outcomes:

- same group identity and directory metadata as clean install;
- duplicate or differently numbered group;
- directory created with fallback ownership;
- manual `chgrp` or `chmod` required.

## 3. Debhelper-generated service and cache snippets

Build a small package with a service unit plus one cache-triggering asset, then inspect the generated maintainer-script snippets before inserting interruption points between them.

Why third:

- tests generated code rather than only handwritten script bodies;
- combines service enable/start state with cache refresh state;
- closer to common real package behavior.

Suggested components:

- `dh_installsystemd` generated `postinst` snippets;
- one cache action such as icon, MIME, desktop, or manual-page database refresh;
- a disposable container with service start suppressed or a stubbed service manager, recorded explicitly.

Distinguishing outcomes:

- unit enablement, service state, and cache contents converge;
- duplicate enablement links or stale cache state;
- rerun starts a service that clean install leaves stopped;
- repair requires a package-specific command.

## Signal variants for every target

Run each meaningful point with:

1. maintainer-script `exit 1`;
2. `SIGTERM`;
3. `SIGKILL`;
4. one recovery run;
5. a second recovery run to test stability after apparent success.

Capture package status immediately after interruption and after each recovery. Compare the second recovered snapshot with both the first recovered snapshot and the clean baseline.

## Recommended order

Start with the alternatives-only probe. It is the smallest real-package-style extension and gives a strong idempotent control before moving to account creation and service/cache behavior.
