# LF-07 — Maintainer-Script Interruption and Idempotency

## In simple words

Debian package scripts change users, services, caches, alternatives, and configuration. This lane interrupts those scripts between meaningful side effects and checks whether rerunning the package action converges on the same state as a clean installation.

## Programme

[`Debian packages, transactions, and builds`](../../STATUS.md)

## State

`mapped` — ready for a disposable-root current-CI probe.

## Question

Can selected package `preinst`, `postinst`, `prerm`, and `postrm` scripts recover when interrupted between meaningful side effects?

## Why this could matter

Package operations may be interrupted by process termination, maintainer-script failure, system shutdown, or resource exhaustion. Re-execution should avoid duplicated state, damaged configuration, and undocumented manual repair.

## Likely targets

- a small package with two or more visible side effects;
- debhelper-generated service, account, cache, or configuration snippets;
- `dpkg` maintainer-script execution paths.

## First probe

Choose a compact package script, inject termination after each meaningful step, rerun the package action, and compare the final filesystem, package state, users, services, and generated data with a clean installation.

## Environment

Current CI inside an expendable root filesystem or container.

## Promotion signal

Promote when re-execution fails, duplicates state, overwrites local configuration, leaves services inconsistent, or requires an undocumented repair sequence.

## Stop signal

Close when every interruption point converges on the clean final state.

## Expected outputs

- script and generated-snippet map;
- interruption fixture;
- clean-state comparison;
- ranked next package candidates or retained negative result.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.