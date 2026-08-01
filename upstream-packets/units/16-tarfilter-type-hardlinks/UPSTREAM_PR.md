# Upstream pull-request draft — validate type-excluded hard links in final-name space

Status: `WITHHELD — candidate implementation and authorization pending`

## Summary

This change makes `tarfilter` evaluate type-excluded hard-link dependencies in the same final-name domain used by archive output.

It preserves the existing focused rejection policy for target-before-link archives, finalizes the output tar stream before returning status 1, and keeps earlier retained duplicate targets available.

## Behavior

- Type-excluded member names are projected through the applicable component-strip and member-name transform operations.
- Retained hard-link targets are projected through the applicable component-strip and hard-link transform operations before dependency checking.
- A retained hard link passes when its final target identity is already available in output.
- A retained hard link fails when its final target identity was removed by the active type filter and no retained occurrence supplies that target.
- Rejection stops before writing the broken member, closes the tar stream, and returns status 1 with the existing member-to-target diagnostic.

## Why

The previous dependency state used normalized input names. Component stripping and transforms can change both member names and hard-link targets afterward. That mismatch can reject a valid final target or accept a missing final target.

## Tests

The focused matrix covers:

- a valid `base` target created from `prefix/base` while an excluded `root/base` input occurrence exists;
- a missing `root/base` target created from `prefix/root/base` after the actual `root/base` member is excluded;
- zero-fuzz composition with the canonical transform/strip patch;
- Python compilation;
- emitted member maps;
- finalized partial output on rejection;
- GNU tar extraction failure for accepted dangling output;
- GNU tar extraction and one-inode identity for the valid expected archive.

Before submission, this draft also requires:

- transform-scope projection controls;
- duplicate and output-name collision controls;
- inherited removed-target, prefix-equivalence, lifecycle, and duplicate matrices;
- cleanup and immediate rerun;
- complete current upstream test gate on the exact candidate head.

## Scope

This change handles target-before-link archives. Link-before-target buffering, arbitrary hard-link graphs, path-filter dependency policy, output rollback, other extractors, platforms, and privileged metadata remain outside this change.

## Submission state

External contact remains unauthorized. Replace this section with exact upstream base, candidate commit, test commands, and public references only after technical completion and explicit authorization.
