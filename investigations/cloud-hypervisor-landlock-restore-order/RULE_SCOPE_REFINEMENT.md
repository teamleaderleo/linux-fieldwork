# Restore source rule scope — file-specific vs directory read authority

Updated: 2026-08-11

Exact upstream head: `915d359f97475b1a39d8561f8db514da9e692d19`

## Decision refinement

The initial candidate treated the caller-selected restore directory as temporary read authority.

A tighter current-source observation improves that design:

- `config.json` is completely opened/read/deserialized before the candidate restriction point;
- `state.json` is completely opened/read/deserialized before the candidate restriction point;
- `memory-ranges` is the only standard snapshot file opened later, inside `MemoryManager::new_from_snapshot()` / `Vm::new()`;
- on-demand restore keeps the already-open `memory-ranges` fd in the UFFD source.

Therefore the leading temporary rule can be **one file**:

```text
<current source_url>/memory-ranges -> r
```

instead of the whole restore directory.

## Variant A1 — file-specific `memory-ranges` rule

Sequence:

1. read saved config;
2. read saved state;
3. derive `<source_url>/memory-ranges`;
4. add that exact file as temporary read authority;
5. apply normal saved config Landlock rules + temporary file rule;
6. construct VM/devices/memory under Landlock.

Advantages:

- minimum post-restriction authority;
- moved snapshots work because the current source file is allowed;
- unrelated files beside the snapshot remain unavailable;
- on-demand restore works through the opened fd;
- disk/backing paths remain governed exclusively by normal VM policy.

Cost:

- future snapshot formats that add another post-restriction file must update this inventory and tests.

**Current leading variant.**

## Variant A2 — restore directory read rule

Grant the whole `source_url` directory read access.

Advantages:

- naturally covers future snapshot files under the root;
- simple operation-level model.

Costs:

- grants unrelated sibling files inside the snapshot directory;
- wider than current restore actually requires after config/state are consumed.

Keep as a compatibility alternative if maintainers prefer the snapshot directory to be the explicit authority unit.

## Why pre-Landlock config/state reads are acceptable within this candidate

The process cannot reconstruct its saved VM path policy until it reads the snapshot configuration.

The restore API explicitly names the snapshot source, so reading the minimum metadata needed to recover that policy is the bootstrap step. Once config/state are parsed, ordinary VM/device construction can run under the recovered sandbox.

This is analogous to receive-migration receiving configuration before it applies Landlock.

The candidate claim is therefore:

> recovered configuration should constrain the resource-opening phase that follows it.

It does not attempt to use recovered configuration to retroactively constrain the metadata read needed to recover that configuration.

## Strong extra negative control

Place an unrelated readable file beside `memory-ranges` in a moved snapshot directory:

```text
copied-snapshot/
  config.json
  state.json
  memory-ranges
  unrelated-secret-control
```

After candidate restore has applied Landlock, a VMM-side path-open probe should still be unable to open `unrelated-secret-control` unless another saved rule grants it.

This distinguishes file-specific authority from the broader directory variant.

Do not turn this control into a guest exploit test. A simple controlled VMM-side test/helper is sufficient if the candidate needs policy proof.

## On-demand lifetime

Landlock regulates future path operations, while `FileUffdMemorySource` retains an already-open fd. The temporary path rule only needs to permit the initial `File::open(memory-ranges)` performed after restriction.

The UFFD thread then inherits the Landlock domain because it is spawned after the earlier restriction point.

## Updated candidate preference

1. **A1: exact `memory-ranges` read rule** — preferred.
2. A2: restore-directory read rule — compatibility alternative.
3. permanent mutation of `VmConfig.landlock_rules` — avoid; it accumulates operation-specific paths in future snapshots.
4. late Landlock after `Vm::new()` — baseline behavior under investigation.
