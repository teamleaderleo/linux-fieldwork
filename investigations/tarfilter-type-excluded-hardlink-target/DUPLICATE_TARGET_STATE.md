# Duplicate names and retained hard-link targets

State: `current-base repair prepared — exact-head execution pending`

## TL;DR

PR #248 has two remaining state/lifecycle defects in its current four-file candidate:

1. it calls `exit(1)` inside the streaming tar context, although its tests require a finalized valid output archive;
2. it remembers every normalized member name skipped by `--type-exclude`, even when an earlier retained occurrence with the same name remains a valid hard-link target.

The clean stacked repair first lets the tar context close before returning status 1. A separate second patch tracks names already retained in the output and rejects a hard link only when no retained occurrence of its normalized target remains.

## Explain like I'm five

The output box already contains a real card named `root/base`. The filter later throws away a different card with the same name.

The first candidate forgets the real card and rejects a label pointing to it. When it does reject something, it also jumps out before closing the output box properly.

The repair remembers what is still in the box and always closes the box before reporting an error.

## Why care

Tar archives may repeat member names. A filter removes one occurrence; it does not retroactively erase an earlier member already written to the output stream.

Rejecting a valid hard link is a product false positive. Exiting before archive finalization is a separate lifecycle defect: downstream readers can receive zero bytes or an unfinished stream instead of the documented valid partial or empty archive.

## Lifecycle repair

`0001-reject-hardlinks-to-type-excluded-members.patch` now sets a failure flag and breaks the member loop. The `with tarfile.open(..., mode="w|")` context closes normally, writing the archive trailer, before the function exits with status 1.

This preserves the existing policy of stopping at the first known excluded dependency while satisfying the candidate tests' valid-archive contract.

## Duplicate-name fixture

Input order:

1. regular `root/base` containing `retained-target\n`;
2. symbolic link also named `root/base`, pointing to `missing`;
3. hard link `root/peer -> root/base`.

Filter:

```text
--type-exclude=SYMTYPE
```

Expected output:

```text
regular root/base
hard link root/peer -> root/base
```

The excluded symbolic-link occurrence is never emitted. The earlier regular target remains.

## Duplicate-state repair

`0002-honor-retained-duplicate-targets.patch` adds `retained_member_names` beside the excluded-name set.

- A skipped occurrence adds an exclusion marker only when the output has not already retained that normalized name.
- A retained occurrence clears an older exclusion marker and records the name as retained.
- A hard-link dependency is checked before the current hard-link name becomes retained, so a self-link does not clear its own missing-target marker.

This preserves target-before-link streaming. It does not buffer future members.

## Prepared regression

`tests/test_tarfilter_type_excluded_duplicate_target.py` requires:

1. imported source returns 0 and emits the retained regular target plus hard link;
2. GNU tar extracts that archive and both paths share an inode;
3. the lifecycle-repaired PR #248 predecessor returns 1 with its focused diagnostic;
4. the predecessor output is a finalized, extractable partial archive containing only the retained regular target;
5. the second patch applies with zero fuzz and the composed source compiles;
6. the repaired candidate returns 0, preserves both output members, extracts successfully, and preserves one inode.

The existing PR #248 matrix separately requires a finalized valid empty archive for a genuine removed-target rejection, prefix equivalence, independent type filters, first-peer stopping, zero-fuzz first-patch composition, and complete Python syntax.

## Evidence history

The earlier stacked PR #281 mixed this mechanism with stale transform/PAX carrier repair after PR #248 was force-restacked. Its exact heads and failed packaging runs remain useful history, but it is not the current carrier.

This record belongs to the clean branch rebuilt directly from current PR #248 head `f1b013832b5f3b073a9131de83ce89077771a7ea`. Moving exact identity and gate status should be read from the stacked pull request rather than embedded here as a self-expiring claim.

## Boundary

This repair handles exact normalized-name reuse before a retained hard link. Transform-induced name collisions, strip-component collisions, path-filter interactions, link-before-target order, arbitrary dependency graphs, output rollback, and archive-sized state remain separate questions.

The retained and excluded sets grow with distinct archive names. They are per-archive state, not constant-space state.

## Disposition

Execute the clean current-base stack, review its four-file delta, and compose it into PR #248 only if both the lifecycle and duplicate-name controls pass on the unchanged exact head.

Internal Linux Fieldwork work only. No Debian or external upstream contact is authorized or included.
