# LF-12 — Reproducible Package Variance

## In simple words

A reproducible package should produce equivalent output from the same declared inputs. This lane varies one environmental factor at a time and traces the first meaningful difference back to source or tooling.

## Programme

[`Debian packages, transactions, and builds`](../../STATUS.md)

## State

`mapped` — ready for a short current-CI build.

## Question

Which outputs change when build time, path, locale, timezone, hostname, user name, file order, and parallelism vary?

## Why this could matter

Uncontrolled variance weakens verification, cache reuse, release comparison, and supply-chain review. Small packages offer a tractable route from binary difference to source cause.

## Likely targets

Small Debian source packages, upstream build systems, `reprotest`, `diffoscope`, `strip-nondeterminism`, and language-specific generators.

## First probe

Select a short build and run paired builds while varying one factor at a time. Classify timestamps, embedded paths, ordering, randomness, locale, and environment data with diffoscope-style analysis.

## Environment

Current CI with pinned source and build dependencies where practical.

## Promotion signal

Promote when a small source-level or tool-level change removes a deterministic difference with clear value beyond one fixture.

## Stop signal

Close when variance comes solely from declared inputs or is already normalized by the supported packaging path.

## Expected outputs

- package selection rationale;
- variance matrix;
- first-difference analysis;
- candidate source fix, tooling fix, or retained negative result.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.