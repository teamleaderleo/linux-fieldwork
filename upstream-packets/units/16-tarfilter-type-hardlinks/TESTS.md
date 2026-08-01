# Tests and receipts — unit 16

## Exact identities

| Item | Identity |
| --- | --- |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported tarfilter | blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Unit-15 prerequisite | `patches/0000-unit15-transform-metadata-prerequisite.patch` |
| PR #310 predecessor | `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` |
| Selected final-identity candidate | `patches/0002-use-rewritten-identities-for-type-hardlinks.patch` |
| Rejected alias candidate | `patches/rejected/0002-alias-projection-overattributes-strip-breaks.patch` |
| Focused test | `tests/test_tarfilter_type_excluded_final_name_identity.py` |
| Inherited and transform matrix | `tests/test_tarfilter_type_excluded_inherited_matrix.py` |
| First selected-policy green head | `ec55994f0db12044f9c7ef9f843fe42aec7393e6` |
| Inherited matrix green head | `300b51056ded64a56ec3998bc639a57e9ea81125` |
| Expanded matrix head | `371802ab8728f149ddbac5a959e83ca8d0edef2d` |
| Duplicate-cleanup head | `7fe46662141fa39a3b18ae1baba29b2b39f6c330` |
| Internal PR | #399 |

## Exact composition commands

Each test obtains the imported source directly from Git's object database:

```sh
git cat-file blob ad776167a8473d5d15dbe22e850f4f6db35cf278
```

The disposable candidate tree receives the ordered series:

```sh
patch --batch --forward --fuzz=0 -p1 \
  -i upstream-packets/units/16-tarfilter-type-hardlinks/patches/0000-unit15-transform-metadata-prerequisite.patch
patch --batch --forward --fuzz=0 -p1 \
  -i upstream-packets/units/16-tarfilter-type-hardlinks/patches/0001-compose-pr310-predecessor-on-transform-carrier.patch
python3 -m py_compile upstream/mmdebstrap/tarfilter
patch --batch --forward --fuzz=0 -p1 \
  -i upstream-packets/units/16-tarfilter-type-hardlinks/patches/0002-use-rewritten-identities-for-type-hardlinks.patch
python3 -m py_compile upstream/mmdebstrap/tarfilter
```

Focused command:

```sh
python3 -m unittest tests.test_tarfilter_type_excluded_final_name_identity -v
```

Inherited and transform command:

```sh
python3 -m unittest tests.test_tarfilter_type_excluded_inherited_matrix -v
```

Complete repository gate:

```sh
python3 -m tools.run_fieldwork_unittests --verbosity 2
```

## Selected-policy matrix

### Focused cases

| Case | Predecessor | Selected candidate |
| --- | --- | --- |
| retained target and excluded duplicate converge to final `base` after strip | status 1; finalized partial archive containing regular `base` | status 0; emits `base` and `peer -> base`; GNU tar extracts one inode |
| strip alone already creates `base` plus broken `peer -> root/base` | status 0 and broken output | unchanged status 0 and broken output; unit 16 does not assign this failure to type exclusion |
| regular `root/base` is removed by type and retained `root/peer -> root/base` remains | status 1 and valid empty archive | status 1, original-name diagnostic, valid empty archive |
| target and dependent link are both dropped by strip | predecessor rejects using input identity | status 0 and valid empty archive |

### Inherited and transform cases

- GNU-equivalent leading `/`, `./`, and `../` target spellings reject when the target is removed by type.
- `.../root/base` remains distinct and follows the pre-existing invalid-archive control.
- `LNKTYPE` exclusion plus transform retains and extracts the regular target; the command is rerun immediately.
- simultaneous `REGTYPE` and `LNKTYPE` exclusion succeeds with an empty archive.
- multiple retained peers stop at the first removed dependency.
- an earlier retained duplicate target remains available after a later excluded duplicate occurrence.
- transform collisions that produce a retained final `base` override an excluded duplicate final `base`.
- a genuinely removed target transformed to final `base` is rejected.
- uppercase `H` leaves the hard-link target untransformed; the direct control is already broken, so type exclusion does not claim ownership.

## Exact CI history

### Run 1100 — malformed predecessor carrier

- head `ac21c095faae34fcd3cec3e4a7beae5a83979fe1`;
- run `30674423172`, job `91298597515`;
- failure before compilation:

```text
hunk count mismatch: declared old/new 12/31, observed 11/29
```

Commit `9ecda06a2ec7ba6dc7fade41d3ad13842220a741` corrected only the hunk header.

### Runs 1118, 1127, and 1131 — historical PR #68 carrier rejected

- runs `30689716762`, `30690001217`, and `30690165287`;
- exact imported source was ultimately loaded through `git cat-file blob`;
- the historical transform patch still failed its parser hunk with `--fuzz=0` while later hunks applied with offsets.

The result selected unit 15's clean regenerated prerequisite instead of repairing a second transform carrier inside unit 16.

### Run 1138 — clean-series candidate hunk count

- head `942a3e4cae0f91461165cb6befefd3910717bcd2`;
- run `30690359366`, job `91343855979`;
- candidate hunk declared 70 new lines and contained 72;
- commit `87af719648d5fc43e616030e61dc6182d9273d3e` corrected only that header.

### Run 1140 — rejected alias candidate is mechanically green

- head `87af719648d5fc43e616030e61dc6182d9273d3e`;
- run `30690434953`, job `91344069265`;
- patch validation: 3 files, 9 hunks;
- 442 tests passed;
- shell syntax and command-help gates passed.

The direct strip control later rejected this policy: alias projection assigned a pre-existing strip-reference failure to type exclusion. The exact candidate is retained under `patches/rejected/`.

### Run 1143 — selected final-only policy red transition

- head `85c00c3d42be14b5774fb5c5222bb57484af7f0d`;
- run `30690507583`, job `91344268061`;
- patch validation and compilation passed;
- 441 of 442 tests passed;
- the sole failure was the superseded assertion expecting alias-based rejection:

```text
AssertionError: 0 != 1
```

The other three focused unit-16 cases passed. This run proves the selected patch changed the disputed attribution boundary while retaining the genuine dependency checks.

### Run 1144 — selected focused policy green

- exact head `ec55994f0db12044f9c7ef9f843fe42aec7393e6`;
- run `30690541675`, job `91344358024`;
- patch validation: 4 files, 11 hunks;
- compilation passed;
- discovery retained 442 of 465 tests and removed 23 exact inherited duplicates;
- all 442 tests passed in 164.133 seconds;
- all four focused unit-16 cases passed;
- shell syntax and command-help gates passed.

### Run 1147 — inherited matrix green with duplicate discovery

- exact head `300b51056ded64a56ec3998bc639a57e9ea81125`;
- run `30690583438`, job `91344466738`;
- patch validation: 4 files, 11 hunks;
- compilation passed;
- discovery retained 450 of 473 tests and removed 23 exact inherited duplicates;
- all 450 tests passed in 162.772 seconds;
- inherited prefix, independent-filter rerun, first-peer, and duplicate-target cases passed;
- shell syntax and command-help gates passed.

A module-level alias to the focused `TestCase` caused four focused tests to run twice. Commit `7fe46662141fa39a3b18ae1baba29b2b39f6c330` imports the helper module instead. The behavior result remains valid; the test count is superseded by the clean rerun.

### Run 1150 — transform-scope expansion before duplicate cleanup

- head `371802ab8728f149ddbac5a959e83ca8d0edef2d`;
- run `30690790494`;
- queued at the last status check.

### Run 1157 — clean expanded rerun

- head `7fe46662141fa39a3b18ae1baba29b2b39f6c330`;
- run `30691015678`;
- queued at the last status check;
- expected clean discovery count: 449 selected tests.

## Baseline evidence inherited from carriers

- PR #244 run `30590931312` passed at characterization head `c853da482a04a5ad49b53478b49e540fd4208b27`.
- PR #244 integrity run `30594719522` passed at `d58deabce19ee98d506970674b537cb091381c5b`.
- PR #310 head `32dfa36a6feb533bc1126a11ef33979e45b410ec` supplies predecessor lifecycle and duplicate-state behavior.
- Unit 15 supplies the clean transform, hard-link-target, occurrence, scope, and PAX metadata prerequisite.

## Cleanup and rerun

Every source copy, patch application, archive, extraction directory, bytecode file, and rerun target lives below `TemporaryDirectory`. The tests create no persistent process, socket, mount, package mutation, device node, or external contact.

The independent `LNKTYPE` transform control runs twice immediately in one disposable tree. One unchanged-head complete workflow remains after run 1157 succeeds.

## Tests pending

- final receipts for runs `30690790494` and `30691015678`;
- one unchanged-head complete rerun after the clean expanded result;
- current Salsa `master` zero-fuzz rebase and current upstream gate;
- package pipeline, other extractor, platform, and privileged metadata gates, when useful and authorized.

## Interpretation rule

A green clean expanded matrix demonstrates final projected identity for target-before-link streaming, including strip, transform, duplicate, prefix, scope, lifecycle, and immediate-rerun controls. Upstream readiness still requires current-master rebase, final diff review, current packet drafts, and explicit authorization.
