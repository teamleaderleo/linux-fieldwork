# Handoff — unit 16

## Current state

State: `ACTIVE`  
Linux Fieldwork branch: `upstream/unit-16-tarfilter-type-hardlinks`  
Internal draft PR: #399  
External-contact state: unauthorized; none made

The selected final-projected-identity candidate now has a clean expanded technical-head result and a successful complete rerun at the current internal PR head. The CI step recorded by the previous handoff is complete. The first incomplete technical work is the exact current-upstream fetch, comparison, zero-fuzz rebase, and current-source matrix.

## Exact branch and candidate identities

| Item | Identity |
| --- | --- |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Current packet head before this update | `c0926e099b98252e3d8f0c8463d53e9709e2a470` |
| Imported tarfilter blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Unit-15 prerequisite | `patches/0000-unit15-transform-metadata-prerequisite.patch` |
| Lifecycle/duplicate predecessor | `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` |
| Selected final-only correction | `patches/0002-use-rewritten-identities-for-type-hardlinks.patch` |
| Rejected alias policy | `patches/rejected/0002-alias-projection-overattributes-strip-breaks.patch` |
| First focused green head | `ec55994f0db12044f9c7ef9f843fe42aec7393e6` |
| Inherited green head | `300b51056ded64a56ec3998bc639a57e9ea81125` |
| Expanded matrix head | `371802ab8728f149ddbac5a959e83ca8d0edef2d` |
| Duplicate-clean technical head | `7fe46662141fa39a3b18ae1baba29b2b39f6c330` |
| Canonical upstream repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended upstream branch | `master` |
| Controlled fork | `NEEDS FORK` |

Use the branch ref for the latest packet head. Documentation commits after the technical heads do not change candidate or test bytes.

## Selected behavior

A retained hard link is accepted when its final projected target identity is already available among retained final member identities.

A type-excluded occurrence marks its surviving final projected member identity unavailable only while no retained occurrence supplies that identity.

A known type-owned dependency failure stops before the hard-link member is written. The tar output context closes before status 1. Original input names appear in the diagnostic.

Intermediate aliases are deliberately excluded. A broken reference already produced by strip or transform behavior without type exclusion remains outside unit 16.

## Completed work

1. Preserved the executed baseline and PR #310 lifecycle/duplicate predecessor.
2. Replaced the non-applicable historical PR #68 carrier with unit 15's clean prerequisite.
3. Restacked the predecessor against unit 15's transform representation.
4. Implemented final projected identity for excluded members and retained hard-link targets.
5. Preserved original input names for diagnostics and finalized failure output.
6. Added focused strip/final-name tests plus inherited prefix, duplicate, lifecycle, filter, transform, collision, and scope controls.
7. Rejected the mechanically green alias policy because direct controls show that it assigns a pre-existing strip failure to type exclusion.
8. Removed accidental duplicate focused-test discovery from the inherited module.
9. Reviewed the complete branch fence: 14 added files before the new receipt, with imported source unchanged.
10. Completed the clean expanded run at technical head `7fe4666...`.
11. Completed a full rerun at packet head `c0926e0...` with unchanged candidate and test bytes.
12. Retained the two new exact receipts in `artifacts/ci-clean-expanded-and-rerun.md`.

## Exact executed evidence

### Selected focused gate

Run `30690541675`, job `91344358024`, head `ec55994f0db12044f9c7ef9f843fe42aec7393e6`:

- 4 patch files and 11 hunks validated;
- compilation passed;
- 442 tests passed in 164.133 seconds;
- all four focused unit-16 cases passed;
- shell syntax and command-help gates passed.

### Inherited gate

Run `30690583438`, job `91344466738`, head `300b51056ded64a56ec3998bc639a57e9ea81125`:

- 4 patch files and 11 hunks validated;
- compilation passed;
- 450 tests passed in 162.772 seconds;
- inherited prefix, independent-filter rerun, first-peer, and retained-duplicate controls passed;
- shell syntax and command-help gates passed.

Four focused tests were discovered twice in this run. Commit `7fe46662141fa39a3b18ae1baba29b2b39f6c330` replaced the class alias with a module import.

### Clean expanded technical-head gate

Run `30691015678`, job `91345628785`, technical head `7fe46662141fa39a3b18ae1baba29b2b39f6c330`, merge checkout `2ebc22e9699521b41e943c492c6bdde4185d4ebc`:

- 4 patch files and 11 hunks validated;
- compilation passed;
- discovery retained 449 of 472 tests and removed 23 exact inherited duplicates;
- 449 tests passed in 166.207 seconds;
- all focused, inherited, and transform-scope unit-16 controls passed;
- shell syntax and command-help gates passed.

### Current packet-head rerun

Run `30691660479`, job `91347358106`, PR head `c0926e099b98252e3d8f0c8463d53e9709e2a470`, merge checkout `20acc0c079a34776df2e81a447833df6e8673cbe`:

- 4 patch files and 11 hunks validated;
- compilation passed;
- discovery retained 449 of 472 tests and removed 23 exact inherited duplicates;
- 449 tests passed in 151.721 seconds;
- all focused, inherited, and transform-scope unit-16 controls passed;
- shell syntax and command-help gates passed.

### Rejected and red-transition evidence

- Alias candidate run `30690434953`, job `91344069265`, head `87af719648d5fc43e616030e61dc6182d9273d3e` passed 442 tests but remains rejected on policy evidence.
- Selected-policy red transition run `30690507583`, job `91344268061`, head `85c00c3d42be14b5774fb5c5222bb57484af7f0d` passed 441 of 442 tests; the sole failure was the superseded alias expectation.

## First incomplete step

Fetch the exact current `master` commit from the Debian mmdebstrap Salsa repository and write it into the packet before editing source or patches.

Then:

1. obtain current upstream `tarfilter` bytes and record their blob/digest;
2. compare them with imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
3. classify unit-15 and PR #310 overlap in current source;
4. regenerate or rebase patches 0000 through 0002 with zero fuzz;
5. run the focused and inherited matrices against the exact current upstream source;
6. perform a fresh complete source-diff review;
7. decide whether the prerequisite remains a full ordered series or can be reduced;
8. keep `NEEDS FORK` until explicit authorization permits a controlled Salsa fork.

If current public source cannot be fetched reliably, record the exact failed endpoint/tool result and stop rather than substituting an inferred commit.

## Complete-review checklist

- [x] original baseline carrier read;
- [x] PR #248 candidate read;
- [x] PR #310 lifecycle/duplicate repair read;
- [x] issue #335 final-name question read;
- [x] unit-15 clean prerequisite copied exactly;
- [x] active patch series reviewed in order;
- [x] rejected alias policy preserved with discriminator;
- [x] focused and inherited selected-policy gates green;
- [x] clean expanded run complete;
- [x] current packet-head complete rerun green;
- [x] destination and intended base branch identified;
- [x] complete pre-receipt branch fence reviewed;
- [ ] exact current upstream base commit fetched;
- [ ] current upstream tarfilter identity recorded;
- [ ] current-master zero-fuzz rebase complete;
- [ ] current-upstream matrix complete;
- [ ] current-upstream complete diff reviewed;
- [ ] controlled fork selected or created after authorization.

## Cleanup state

All candidate source copies, patch applications, archives, extraction directories, and bytecode live below `TemporaryDirectory`. CI leaves no persistent process, socket, mount, lock, package mutation, device node, or caller-selected deletion root.

No upstream fork was created. Durable work lives on the Linux Fieldwork branch and internal PR #399.

## Open questions

- exact current Salsa `master` commit and overlap with units 15 and 16;
- whether submission should be one integrated commit or an ordered series;
- whether final availability needs occurrence counts under a future link-before-target or rollback design;
- package-level diagnostic effects in current mmdebstrap pipelines;
- whether an upstream issue adds value once a merge request is ready.

## External-contact guard

Do not create or use a Salsa fork, open an issue or merge request, post a comment, send email, submit a patch, upload a package, or contact any external maintainer without explicit authorization. Public-source reads and internal Linux Fieldwork work remain authorized.
