# Upstream issue draft — type exclusion can break hard-link dependencies after name rewriting

Status: `WITHHELD — internal draft; external contact unauthorized`

## Summary

`tarfilter` applies `--type-exclude` before `--strip-components` and transforms. A retained hard link can therefore be validated against pre-rewrite target text while the emitted archive resolves the link using rewritten names.

This creates both failure directions:

1. a valid final target is rejected because an excluded input occurrence used the same pre-strip spelling;
2. a missing final target is accepted because its pre-strip spelling differed from the excluded input name.

## Reproducer 1 — valid target rejected

Input member order:

```text
regular   prefix/base
symlink   root/base -> missing
hardlink  root/peer -> root/base
```

Command:

```sh
tarfilter --type-exclude=SYMTYPE --strip-components=1
```

Expected emitted archive:

```text
regular   base
hardlink  peer -> base
```

The final target `base` exists. Current composed dependency checking rejects `root/peer -> root/base` before component stripping and returns status 1.

## Reproducer 2 — missing target accepted

Input member order:

```text
regular   root/base
hardlink  prefix/peer -> prefix/root/base
```

Command:

```sh
tarfilter --type-exclude=REGTYPE --strip-components=1
```

Current composed behavior returns status 0 and emits:

```text
hardlink  peer -> root/base
```

The emitted target `root/base` is absent. GNU tar extraction fails.

## Expected behavior

Hard-link dependency decisions should use the same final-name operation used for emitted member names and emitted hard-link targets. A retained hard link with an emitted target should pass. A retained hard link whose final target was removed by the type filter should fail with a focused diagnostic before the broken member is written.

Failure output should remain a finalized tar stream.

## Compatibility boundary

This report concerns target-before-link archives, `--type-exclude`, component stripping, and the existing transform target scopes. Link-before-target buffering, arbitrary hard-link graphs, path-filter policy, output rollback, and broad transform-language compatibility are separate.

## Evidence available internally

- executed original dangling-target baseline;
- finalized rejection and duplicate-target predecessor;
- two-case strip-rewrite characterization;
- GNU tar extraction and inode controls;
- exact zero-fuzz patch composition.

Exact candidate and full-gate evidence will be added before any authorized submission.
