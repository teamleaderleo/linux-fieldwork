# Upstream issue draft — type-excluded hard-link checks use pre-rewrite identity

Status: `WITHHELD — internal draft; external contact unauthorized`

## Summary

`tarfilter` applies `--type-exclude` before component stripping and transforms. A composed hard-link dependency check that records skipped input names can reject a valid retained link even though another retained member supplies the final rewritten target.

## Reproducer

Input order:

```text
regular   prefix/base
symlink   root/base -> missing
hardlink  root/peer -> root/base
```

Command:

```sh
mmtarfilter --type-exclude=SYMTYPE --strip-components=1
```

The valid filtered result is:

```text
regular   base
hardlink  peer -> base
```

GNU tar extracts that archive and preserves one inode. Input-name dependency state instead remembers excluded `root/base` and rejects `root/peer -> root/base` before stripping.

## Existing type-filter failure

A simpler target-before-link archive containing regular `root/base` and hard link `root/peer -> root/base` demonstrates the original defect: excluding `REGTYPE` retains the payload-free hard link, returns status 0, and emits an archive GNU tar cannot extract.

A focused rejection policy fixes that result, but its dependency identity must follow the names actually emitted.

## Expected behavior

- project a type-excluded member through member-name component stripping and transform scope;
- project a retained hard-link target through hard-link component stripping and transform scope;
- accept the link when a retained occurrence supplies the final target identity;
- reject before output when the active type filter removed the final target identity and no retained occurrence supplies it;
- close the tar stream before returning status 1;
- retain original input strings in the diagnostic.

## Attribution boundary

Some strip or transform options already create broken references without type exclusion. For example, stripping `root/base` and `prefix/peer -> prefix/root/base` produces `base` plus `peer -> root/base`. This report does not assign that existing rewrite behavior to `--type-exclude`.

## Scope

Included:

- target-before-link archives;
- type-excluded targets;
- component stripping and member/hard-link transform scopes;
- duplicate target occurrences;
- finalized partial or empty output on rejection.

Excluded:

- link-before-target buffering;
- arbitrary hard-link graphs;
- path-filter dependency policy;
- intrinsic strip or transform reference failures;
- output rollback, other extractors, platforms, and privileged metadata.

## Evidence prepared

Internal exact-head gates cover:

- original dangling-target baseline;
- valid final-target acceptance and one-inode extraction;
- genuine removed-target rejection and finalized empty output;
- retained duplicate targets;
- leading-prefix equivalence and distinct dot prefixes;
- independent filters and immediate rerun;
- transform collisions and uppercase hard-link scope boundaries;
- zero-fuzz ordered patch composition and Python compilation.

The exact current upstream base and public references will be added only after technical rebase and explicit authorization.
