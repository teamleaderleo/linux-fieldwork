# Handoff — unit 01 tarfilter regex dialects

## Current state

State: `ACTIVE`  
Linux Fieldwork branch: `upstream/unit-01-tarfilter-regex-dialects`  
Branch base at claim: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`  
Commit immediately before this handoff: `3042536b4bb1b46920860072fbd4d61a6bed1b97`  
Exact branch head containing this handoff: recorded in the current `UNIT CHECKPOINT` comment on issue #397  
External contact authorized: `false`  
External contact made: `none`

## Latest result

The unit is rebased at the relevant-file level onto the clean unit-15 prerequisite and the exact `tarfilter` bytes in the user's mmdebstrap 1.5.7-3 repository. The regenerated two-patch series applies with zero fuzz and zero offsets, compiles, and passes the complete direct GNU tar matrix.

The historical regex patch is retired as an application carrier: after the clean prerequisite it used offsets `+25` and `+19`, then failed its final hunk. Its behavior was regenerated into one exact patch.

## Exact identities

### Source

- user-controlled repository: `teamleaderleo/mmdebstrap`
- branch/head: `master` at `574048f2a720057b75e56622003932f344dc700a`
- base `tarfilter` blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- public upstream observed by unit 15: `josch/mmdebstrap` `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`
- relevant public-upstream `tarfilter` blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- canonical Salsa exact head: `UNRESOLVED`

### Current series

1. prerequisite patch: `patches/0001-transform-metadata-prerequisite.patch`
   - blob `38510533dc015182f3e87e9d2f3777eea5b8c93b`
   - SHA-256 `4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c`
   - result blob `adb330efcc941bf5e646f195c245a3184e42f8e2`
2. regenerated regex patch: `patches/0002-tarfilter-regex-dialects.patch`
   - blob `7e7d37a77b0215af033b0c97770c83cce130911a`
   - SHA-256 `2c3312f732b2fa0f1a04c92d7633c8a1e7bc9c2c7a6b52a6d150096d6a8f1746`
   - result blob `ca8e656c036172230c796a8a12cb17f262108c39`
   - candidate SHA-256 `47e73119f2418fb1e7c47f3eb8f6e82e86a5903ff5c73c68fa5c5ac047ff6308`

### Execution

- Python `3.13.5`
- GNU tar `1.35`
- locale `LC_ALL=C`
- full matrix receipt SHA-256 `573cf47dcb947f62910fd3cdd77fe8103a0499b99b2d5d63dc0f081fb60ea8c0`
- representative rerun digest `731adb7f3cfd8f3aba6278ced4a630f4c588da0547952b4e9e02666c536fb65f`, identical twice

## Work completed in this continuation

- discovered the user's controlled `teamleaderleo/mmdebstrap` repository and pinned its exact 1.5.7-3 head;
- confirmed its `tarfilter` blob equals the Linux Fieldwork import and unit-15 current visible upstream observation;
- checked all issue #397 unit branches;
- reviewed tarfilter units 15, 16, and 18–22 for updates and overlap;
- selected unit 15's regenerated patch as the exact prerequisite;
- reproduced the historical regex patch offset/failure result;
- regenerated one regex patch against the clean prerequisite;
- proved dry-run and real application with zero fuzz and zero offsets;
- verified exact base, prerequisite, and candidate blobs;
- compiled the candidate;
- ran baseline and prerequisite negative controls;
- passed 41 candidate/GNU successful comparisons;
- passed two numeric-occurrence/link-scope comparisons;
- passed 11 shared rejection comparisons;
- passed three explicit POSIX-boundary comparisons;
- corrected one local harness ownership error and reran from isolated source files;
- passed a freshly materialized representative gate twice;
- committed a self-contained series, wrapper, runner, exact receipts, hashes, and parallel-unit map;
- updated README, source map, deep dive, tests, decisions, upstream draft, and this handoff.

## Parallel unit result

Every issue #397 unit branch exists. Relevant tarfilter branches contain substantive work.

- Unit 15 is the direct prerequisite and is vendored here.
- Unit 16 already vendors unit 15 and then changes type-hardlink identity.
- Units 18–22 own no-option, PAX-idshift, dotfile, parent-retention, and regular-type corrections.
- None replaces unit 1. A later combined branch must compose selected units and review line overlap.

See `artifacts/PARALLEL_UNITS.md`.

## Reproduction command

From a Linux Fieldwork checkout at this branch:

```sh
sh upstream-packets/units/01-tarfilter-regex-dialects/scripts/materialize_and_run.sh
```

The wrapper fails closed unless the base, prerequisite, and candidate blobs match the identities above. It applies both patches with `--fuzz=0`, compiles, runs the full matrix, and removes its temporary root.

## Cleanup state

The local test run used disposable materialization roots and Python `TemporaryDirectory` archives. No process, socket, mount, container, archive, patched source checkout, or Python cache is intentionally retained by the packet wrapper. Intentional durable state is limited to the Linux Fieldwork branch packet and internal issue checkpoint.

## First incomplete step

Use the user's full mmdebstrap checkout to identify the exact transform-related native tests and execute the candidate through project orchestration:

```sh
cd /path/to/teamleaderleo-mmdebstrap
# materialize the two packet patches onto a clean candidate copy or candidate branch
# keep the candidate at repository-root ./tarfilter
CMD=./mmdebstrap ./coverage.py --dist unstable TEST-NAME
```

Read current `coverage.txt`, `coverage.py`, and `tests/` before choosing `TEST-NAME`. Record exact commands, generated state, statuses, and cleanup.

## Next safe technical action

1. Create a local candidate branch in the user's controlled mmdebstrap repository if desired.
2. Apply the two packet patches with zero fuzz and offsets.
3. Port or select upstream-native transform tests, including PR #220's three positive controls.
4. Run focused native tests through `coverage.py`.
5. Run the appropriate broader native gate.
6. Compose selected independent tarfilter units, starting with the unit-15 prerequisite already present.
7. Review the complete combined diff and rerun focused tests after cleanup.
8. Resolve exact canonical Salsa head and live issue/MR overlap immediately before an authorization decision.

## Gates remaining

- upstream-native focused execution;
- appropriate broader native execution;
- selected parallel-unit composition and complete-diff review;
- controlled candidate branch and compare URL;
- exact canonical Salsa head and live overlap recheck;
- explicit authorization before external contact.

## Human decision state

No send decision yet. Product application and the direct GNU matrix are green. The next choice is technical: native-test port first, or combined tarfilter composition first.

Do not create a Salsa issue, merge request, comment, review, email, or mailing-list post without explicit authorization.
