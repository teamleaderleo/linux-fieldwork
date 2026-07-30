# LF-11 — Merged-`/usr` Path Assumptions

## In simple words

Debian systems use a merged layout where historical top-level paths resolve into `/usr`. This lane tests scripts and tools that still treat paths such as `/bin` and `/usr/bin` as different authorities or resolve target-root symlinks unsafely.

## Programme

[`Debian packages, transactions, and builds`](../../STATUS.md)

## State

`mapped` — ready for synthetic-root probes, with boot-sensitive branches reserved for a VM.

## Question

Which scripts and tools still distinguish `/bin` from `/usr/bin`, resolve symlinks too early, or mishandle package transitions on merged-`/usr` systems?

## Why this could matter

Path assumptions can break package upgrades, initramfs generation, archive contents, target-root containment, and recovery tooling.

## Likely targets

Maintainer scripts, bootstrap hooks, initramfs tools, shell scripts, package build rules, and path canonicalization utilities.

## First probe

Run selected operations in equivalent merged and synthetic split root layouts. Compare path discovery, package installation, archive output, generated configuration, and any resolution outside the target root.

## Environment

Current CI for synthetic roots. Use a VM for boot-path claims.

## Promotion signal

Promote when equivalent paths produce different functional results, symlink handling escapes a target root, or upgrades fail across the layout transition.

## Stop signal

Close when observed differences are cosmetic or explicitly required by Debian policy.

## Expected outputs

- path and symlink model;
- paired root fixtures;
- selected script or tool matrix;
- candidate investigation or retained negative result.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.