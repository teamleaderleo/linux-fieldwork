# Upstream merge request draft

Status: `DRAFT — HOLD`  
Proposed destination: mmdebstrap GitLab project  
Proposed base branch: `NEEDS CURRENT UPSTREAM PIN`  
Candidate branch or patch series: `UNSELECTED`  
External contact authorized: `false`

## Proposed title

Preserve reproducible root and chrootless tar output by normalizing directory mtimes

## Draft

### Summary

This change converged root and chrootless direct-tar output under an explicit `SOURCE_DATE_EPOCH` by assigning the selected epoch to real archive-tree directory mtimes while preserving directory access time and non-directory metadata.

### Before

Root and chrootless output could contain identical paths, types, modes, ownership, sizes, links, and regular-file bytes while differing on older package-owned directory mtimes. The existing byte-comparison regression then failed.

### After

Root and chrootless tarballs were byte-identical for the focused case. Older regular-file mtimes, directory access time, links, xattrs, ACLs, file capabilities, sparse source allocation, foreign-device descendants, and cleanup behavior remained unchanged.

### Implementation

The exact implementation remains intentionally blank until the archive-boundary authority discriminator selects one of:

1. descriptor-retained directory mutation under an explicit quiescent-tree ownership premise; or
2. archive-header-only directory mtime normalization with complete PAX, xattr, link, and sparse compatibility controls.

PR #395's path-based helper is excluded from this draft because it overwrites directory access time and retains check-to-mutation identity risk.

### Tests required before authorization

- minimal current-clamp negative control;
- full-normalization losing control for old regular-file mtime;
- directory-atime losing control;
- symlink and hard-link preservation;
- foreign-device exclusion;
- xattr, ACL, file-capability, and sparse-source preservation;
- archive-boundary process receipts in repeated root and chrootless runs;
- focused real sid `chrootless` case with all include variants;
- immediate clean rerun;
- current upstream syntax, formatting, and focused native tests;
- complete selected diff review.

### Compatibility

The intended surface is Linux root/chrootless mode, direct tar output, explicit `SOURCE_DATE_EPOCH`, and ordinary non-dry-run execution. Other modes and output formats retain current behavior unless separately evidenced.

## Proposed commits or patch order

`UNSELECTED — authority and access-time repair first.`

## Reviewer notes

The central review point is mutation authority after setup completes. Descriptor identity prevents pathname redirection but can remain bound to an inode moved outside the temporary root. The selected patch must state the operation-ownership premise explicitly or avoid live-tree mutation entirely.

## Submission checklist

- [ ] Candidate rebased onto current upstream.
- [ ] Complete upstream diff reviewed.
- [ ] Baseline regression fails and candidate passes.
- [ ] Directory atime remains unchanged.
- [ ] Authority discriminator resolved.
- [ ] Upstream-native focused tests pass.
- [ ] Cleanup and immediate rerun pass.
- [ ] Active equivalent work rechecked.
- [ ] Fork/branch delivery path exists.
- [ ] Draft contains no Linux Fieldwork-only routing.
- [ ] Explicit authorization recorded.
- [ ] Public merge request and exact submitted head recorded after submission.
