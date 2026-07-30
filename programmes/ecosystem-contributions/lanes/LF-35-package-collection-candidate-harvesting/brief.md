# LF-35 — Package Collection Candidate Harvesting

## In simple words

Package collections compile thousands of unrelated projects under repeatable rules. This lane searches those build and test surfaces for defects that can become small, independent downstream or upstream contributions.

## Programme

[`Ecosystem contributions and upstream fixes`](../../STATUS.md)

## State

`mapped` — ready for current-CI reconnaissance and small container builds.

## Question

Which package updates, failed builds, architecture gaps, reproducibility differences, dependency errors, service definitions, obsolete patches, or test failures can be reduced into reviewable contribution packets?

## Why this could matter

One package collection exposes many languages, build systems, libraries, and applications. A disciplined intake lane can produce continuing useful work while also revealing recurring upstream failure classes.

## Likely targets

Nixpkgs, Debian package and QA surfaces, Fedora package repositories, Arch packages, Linuxbrew/Homebrew formulae, and selected upstream projects reached through package evidence.

## First probe

Choose one package collection available in the current environment. Record its contribution checks and candidate queries. Rank twenty candidates, inspect the top five against current upstream state, and reduce the best two to exact build or test reproductions.

## Environment

Current CI and rootless containers. Record when a candidate requires another architecture, macOS, privileged execution, a VM, hardware, credentials, or a network service.

## Promotion signal

Promote when a candidate has a pinned package and upstream revision, repeatable failure or deterministic difference, bounded ownership, overlap check, and a credible test or validation command.

## Stop signal

Park candidates already fixed, actively owned upstream, unsupported by the package collection, dependent on unavailable proprietary inputs, or reducible only to cosmetic metadata changes.

## Expected outputs

- contribution-surface map;
- candidate ranking with downstream/upstream ownership;
- two reproduction-ready packets per round;
- promoted investigations or retained stop records;
- recurring failure-class notes.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.