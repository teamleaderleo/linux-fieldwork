# Duplicate names and retained hard-link targets

State: `repair prepared — exact candidate execution pending`

## TL;DR

PR #248 remembers every normalized member name skipped by `--type-exclude`. That is not sufficient archive state when the same name appears more than once.

A retained `root/base`, followed by a type-excluded duplicate also named `root/base`, still leaves a valid target in the output archive. The first candidate nevertheless marks the name excluded and rejects a later `root/peer -> root/base` hard link.

The repair separately remembers names already retained in the output. An excluded duplicate marks a name unavailable only when no prior retained member with that name exists. A later retained member also clears an older exclusion marker.

## Explain like I'm five

The output box already contains a real card named `root/base`. The input later shows another card with the same name, but the filter throws that second card away.

The first candidate writes “root/base was thrown away” and forgets that the first card is still in the box. It then rejects a label pointing to the card that is actually there.

## Why care

Tar archives may repeat names. Filters remove individual member occurrences; they do not erase an earlier occurrence already written to the output stream.

Rejecting a valid filtered archive is a product false positive, not merely a missing optimization. It can turn a successful type filter into status 1 and suppress a valid hard-link member.

## Exact fixture

Input order:

1. regular `root/base` with `retained-target\n`;
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

## Reference execution

A direct GNU tar control with the expected two-member output extracted successfully. `root/base` and `root/peer` had the same inode and the target contained `retained-target\n`.

This is local extractor evidence for the fixture shape. Actual imported-source, predecessor-candidate, and repaired-candidate execution is delegated to `tests/test_tarfilter_type_excluded_duplicate_target.py` and remains pending exact-head Linux Fieldwork CI.

## Predecessor source trace

The first candidate performs:

```python
if type_filter_should_skip(member):
    type_excluded_members.add(normalize(member.name))
    continue
```

For the fixture:

```text
retain regular root/base
skip symlink root/base -> add root/base to excluded set
read hard link root/peer -> root/base -> reject
```

The state records that one occurrence was excluded, not whether a target remains in the output.

## Repair

The second patch adds `retained_member_names`.

- A skipped occurrence adds an exclusion marker only when the output has not already retained that normalized name.
- A retained occurrence clears an older exclusion marker and records the name as retained.
- A hard-link dependency is checked before the current hard-link name becomes retained, so a self-link does not clear its own missing-target marker.

This preserves the original target-before-link streaming boundary. It does not buffer future members.

## Prepared regression

`tests/test_tarfilter_type_excluded_duplicate_target.py` requires:

1. imported source returns 0 for `--type-exclude=SYMTYPE`;
2. output contains regular `root/base` and hard link `root/peer`;
3. GNU tar extraction succeeds with one inode;
4. the PR #248 predecessor returns 1 and emits its focused diagnostic;
5. the predecessor partial archive contains only the retained regular target;
6. the second patch applies with zero fuzz and the composed source compiles;
7. the repair returns 0, preserves both output members, extracts successfully, and preserves one inode.

## Boundary

This repair handles exact normalized-name reuse before a retained hard link. Transform-induced name collisions, strip-component collisions, path-filter interactions, link-before-target order, arbitrary dependency graphs, output rollback, and archive-sized state remain separate design questions.

The retained/excluded sets still grow with distinct archive names. The earlier description of the state as “bounded” should be read as bounded per archive, not constant memory.

## Disposition

Stack this repair on PR #248, execute exact-head CI, then decide whether the duplicate-name semantics belong in the candidate policy or require a broader output-name state design.

Internal Linux Fieldwork work only. No Debian or external upstream contact is authorized or included.
