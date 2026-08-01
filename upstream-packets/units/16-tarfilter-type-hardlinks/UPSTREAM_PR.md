# Upstream merge-request draft — validate type-excluded hard links in final-name space

Status: `WITHHELD — current-master rebase and external authorization pending`

## Summary

This change evaluates type-excluded hard-link dependencies in the same final projected name domain used by archive output.

It preserves target-before-link streaming, closes the output tar stream before returning status 1, keeps retained duplicate targets available, and reports original member and target spellings.

## Behavior

- Type-excluded member names are projected through component stripping and member-name transform scope.
- Retained member names are recorded after the same rewrite operation.
- Retained hard-link targets are projected through component stripping and hard-link transform scope.
- A retained hard link passes when an earlier retained occurrence supplies its final target identity.
- A retained hard link fails when the active type filter removed that final target identity and no retained occurrence supplies it.
- Rejection stops before writing the broken member, closes the tar stream, and returns status 1.
- Strip or transform reference failures already present without type exclusion remain unchanged.

## Why

The predecessor tracked normalized input names. Later stripping and transforms can make different inputs converge to the same emitted identity. Input-name state can therefore reject a valid link whose final target is present.

Tracking intermediate aliases creates the opposite attribution error: it can blame type exclusion for a link already broken by strip or transform behavior alone. One surviving final identity per occurrence gives the dependency check the same view as the extractor.

## Ordered implementation

1. apply the transform, hard-link target, occurrence, scope, and PAX metadata prerequisite;
2. add finalized type-dependency rejection and retained duplicate-target state;
3. replace input-name dependency state with final projected identities.

For a final upstream merge request, these layers may be squashed if current `master` already carries part of the prerequisite.

## Tests

The executed matrix covers:

- original regular-target exclusion and dangling hard-link prevention;
- valid final target created by component stripping;
- genuine removed final target;
- a target and dependent link both dropped by stripping;
- a strip-only broken reference that stays outside type-filter ownership;
- GNU-equivalent leading `/`, `./`, and `../` prefixes;
- distinct `.../` target spelling;
- independent `LNKTYPE` exclusion and immediate rerun;
- simultaneous regular and hard-link exclusion;
- first-peer stopping;
- retained duplicate targets;
- transformed retained-target collisions;
- transformed removed-target rejection;
- uppercase `H` transform scope as a direct pre-existing-break control;
- zero-fuzz patch application, Python compilation, GNU tar extraction, finalized output, and inode identity.

Internal selected-policy gate `30690541675` passed 442 tests. Inherited gate `30690583438` passed 450 tests before duplicate-discovery cleanup. The clean expanded rerun is `30691015678`.

## Review fence

The Linux Fieldwork branch adds exactly 14 files:

- 2 executable tests;
- 8 packet records and drafts;
- 3 active ordered patches;
- 1 rejected patch retained as evidence.

The imported tarfilter file is unchanged on the branch.

## Scope

This change handles target-before-link archives. Link-before-target buffering, arbitrary hard-link graphs, path-filter dependency policy, output rollback, intrinsic rewrite failures, other extractors, platforms, and privileged metadata remain separate.

## Upstream identity pending

- repository: `https://salsa.debian.org/debian/mmdebstrap.git`;
- intended base: `master`;
- exact base commit: pending current-master fetch;
- controlled fork: `NEEDS FORK`;
- candidate commit: pending rebase;
- delivery: Salsa merge request;
- external authorization: absent;
- external contact made: none.
