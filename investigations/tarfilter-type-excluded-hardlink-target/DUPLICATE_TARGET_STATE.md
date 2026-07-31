# Duplicate names and retained hard-link targets

State: `review repaired — exact-head execution pending`

## TL;DR

PR #248 has two remaining state/lifecycle defects in its current candidate:

1. it calls `exit(1)` inside the streaming tar context, although its tests require a finalized valid output archive;
2. it remembers every normalized member name skipped by `--type-exclude`, even when an earlier retained occurrence with the same name remains a valid hard-link target.

The clean stacked repair first lets the tar context close before returning status 1. A separate second patch tracks names actually retained in the output and rejects a hard link only when no retained occurrence of its normalized target remains.

Complete review found that “actually retained” must be literal: the first version updated retained state before `--strip-components` could still drop the member. The repaired patch now updates retained/excluded state only after every later skip decision and immediately before `out_tar.addfile()`.

## Explain like I'm five

The output box already contains a real card named `root/base`. The filter later throws away a different card with the same name.

The first candidate forgets the real card and rejects a label pointing to it. When it does reject something, it also jumps out before closing the output box properly.

The repair remembers only cards that really reach the box and always closes the box before reporting an error. A card that was considered and then dropped by another filter is not counted as packed.

## Why care

Tar archives may repeat member names. A filter removes one occurrence; it does not retroactively erase an earlier member already written to the output stream.

Conversely, reaching the type-filter stage does not prove a member was emitted. Later strip logic can still skip it. Recording that member as retained can authorize a hard link to a target absent from the output.

Rejecting a valid hard link is a product false positive. Allowing a hard link to a non-emitted target is a broken-output false negative. Exiting before archive finalization is a separate lifecycle defect: downstream readers can receive zero bytes or an unfinished stream instead of the documented valid partial or empty archive.

## Lifecycle repair

`0001-reject-hardlinks-to-type-excluded-members.patch` sets a failure flag and breaks the member loop. The `with tarfile.open(..., mode="w|")` context closes normally, writing the archive trailer, before the function exits with status 1.

This preserves the existing policy of stopping at the first known excluded dependency while satisfying the candidate tests' valid-archive contract.

## Retained duplicate-name fixture

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

## Strip-skipped target fixture

Input order:

1. regular `base` containing `strip-skipped-target\n`;
2. symbolic link also named `base`, pointing to `missing`;
3. hard link `root/peer -> base`.

Filters:

```text
--type-exclude=SYMTYPE
--strip-components=1
```

The one-component regular member is skipped by strip logic and never reaches output. The symbolic-link duplicate is excluded. The hard-link member itself survives stripping as `peer` but its target `base` is absent.

Observed imported behavior is status 0 with a broken `peer -> base` output member. The lifecycle-repaired predecessor rejects status 1 and emits a finalized valid empty archive. The repaired duplicate-state candidate must retain that rejection; the skipped regular member must not clear the exclusion marker.

## Duplicate-state repair

`0002-honor-retained-duplicate-targets.patch` adds `retained_member_names` beside the excluded-name set.

- A type-skipped occurrence adds an exclusion marker only when the output has not already retained that normalized input name.
- A hard-link dependency is checked before the current hard-link name becomes retained, so a self-link does not clear its own missing-target marker.
- The current normalized input name is carried through later filtering.
- A retained occurrence clears an older exclusion marker and records the name only after strip, PAX, idshift, and transform processing have completed and immediately before output.

This preserves target-before-link streaming. It does not buffer future members.

The retained name deliberately refers to the normalized input identity used by the type-exclusion dependency check. Transform- and strip-induced output-name collisions remain outside this patch rather than being silently conflated with type-filter state.

## Focused regression

`tests/test_tarfilter_type_excluded_duplicate_target.py` requires:

### Retained duplicate

1. imported source returns 0 and emits the retained regular target plus hard link;
2. GNU tar extracts that archive and both paths share an inode;
3. the lifecycle-repaired PR #248 predecessor returns 1 with its focused diagnostic;
4. predecessor output is a finalized, extractable partial archive containing only the retained regular target;
5. patch 0002 applies with zero fuzz and the composed source compiles;
6. repaired candidate returns 0, preserves both output members, extracts successfully, and preserves one inode.

### Strip-skipped target

1. imported source returns 0 with broken `peer -> base` output and GNU tar extraction fails;
2. lifecycle-repaired predecessor returns 1 with the focused diagnostic and a finalized empty archive;
3. repaired source places retained-state mutation after the strip skip and directly before output;
4. repaired candidate also returns 1 with the focused diagnostic and a finalized extractable empty archive.

The existing PR #248 matrix separately requires genuine removed-target rejection, leading-prefix equivalence, non-equivalent dot prefixes, independent type filters, first-peer stopping, zero-fuzz first-patch composition, and complete Python syntax.

## Evidence history

The earlier stacked PR #281 mixed this mechanism with stale transform/PAX carrier repair after PR #248 was force-restacked. Its exact heads and failed packaging runs remain useful history, but it is not the current carrier.

The first clean PR #310 head `373293cc9e7e174bf9679bea2c55404700cf81f2` had exact CI queued when complete review found the premature retained-state mutation. That head is provenance only and does not establish the repaired strip boundary.

Moving exact identity and gate status should be read from PR #310 rather than embedded here as a self-expiring current claim.

## Boundary

This repair handles exact normalized input-name reuse before a retained hard link and distinguishes a member actually emitted from one skipped later by strip logic.

Transform-induced name collisions, strip-induced target rewriting, path-filter interactions, link-before-target order, arbitrary dependency graphs, output rollback, and archive-sized state remain separate questions.

The retained and excluded sets grow with distinct archive names. They are per-archive state, not constant-space state.

## Disposition

Execute the repaired clean current-base stack, inspect the complete four-file delta, and compose it into PR #248 only if lifecycle, retained-duplicate, and strip-skipped-target controls pass on the unchanged exact head.

Internal Linux Fieldwork work only. No Debian or external upstream contact is authorized or included.
