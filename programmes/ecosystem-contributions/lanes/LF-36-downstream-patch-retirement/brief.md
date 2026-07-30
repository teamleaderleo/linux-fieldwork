# LF-36 — Downstream Patch Retirement and Upstream Transfer

## In simple words

Distributions carry patches when released upstream code does not fit their needs. This lane checks whether those patches remain necessary, whether newer upstream code supersedes them, and whether a general fix should move upstream.

## Programme

[`Ecosystem contributions and upstream fixes`](../../STATUS.md)

## State

`mapped` — ready for source and package-history reconnaissance.

## Question

Which downstream patches can be removed, refreshed, narrowed, converted into tests, or promoted into a general upstream correction?

## Why this could matter

Long-lived downstream patches create upgrade cost, hide compatibility assumptions, diverge behavior across distributions, and leave upstream without the tests or context needed to prevent recurrence.

## Likely targets

Debian patch series, Nixpkgs patches, Fedora downstream patches, Arch package patches, Linuxbrew/Homebrew formula patches, and their corresponding upstream repositories.

## First probe

Select ten actively carried patches across at least two package collections. Record the original reason, current upstream revision, surrounding history, existing upstream issue or pull request, package build command, and whether the patch still changes behavior. Fully test the two strongest retirement or upstream-transfer candidates.

## Environment

Current CI and rootless containers where the package build is tractable. Use source-only review for expensive candidates until a smaller fixture is identified.

## Promotion signal

Promote when a patch is demonstrably obsolete, applies too broadly, lacks regression coverage, fixes a general upstream defect, or can be replaced by a smaller compatibility change with clear validation.

## Stop signal

Close when the patch is intentionally distribution-specific, tied to local policy, still required with no general upstream contract, already being retired, or impossible to validate within available environments.

## Expected outputs

- patch provenance table;
- upstream overlap and history review;
- before/after build or test evidence;
- candidate package cleanup, upstream test, upstream fix, or retained rationale;
- explicit ownership and contact recommendation.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.