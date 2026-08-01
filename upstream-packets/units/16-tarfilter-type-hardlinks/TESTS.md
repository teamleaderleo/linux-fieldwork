# Tests and receipts — unit 16

## Exact identities

| Item | Identity |
| --- | --- |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported tarfilter | blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Transform/strip patch | blob `1703984aa0c030e5131618a3541ee85bfd68ec65` |
| PR #310 predecessor | head `32dfa36a6feb533bc1126a11ef33979e45b410ec` |
| Packet predecessor patch | `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` |
| Focused test | `tests/test_tarfilter_type_excluded_final_name_identity.py` |
| Internal PR | #399 |

## Focused command

```sh
python3 -m unittest tests.test_tarfilter_type_excluded_final_name_identity -v
```

The test performs these setup gates for each case:

```sh
patch --batch --forward --fuzz=0 -p1 \
  -i investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch
patch --batch --forward --fuzz=0 -p1 \
  -i upstream-packets/units/16-tarfilter-type-hardlinks/patches/0001-compose-pr310-predecessor-on-transform-carrier.patch
python3 -m py_compile upstream/mmdebstrap/tarfilter
```

All patch application and source execution occurs in `TemporaryDirectory` copies.

## Matrix

| Case | Input and options | Required predecessor result | Extractor control |
| --- | --- | --- | --- |
| false rejection | regular `prefix/base`; excluded symlink `root/base`; hard link `root/peer -> root/base`; `--type-exclude=SYMTYPE --strip-components=1` | status 1; focused input-name diagnostic; finalized partial archive containing regular `base` | direct expected `base` plus `peer -> base` archive extracts and shares one inode |
| false acceptance | excluded regular `root/base`; hard link `prefix/peer -> prefix/root/base`; `--type-exclude=REGTYPE --strip-components=1` | status 0; emitted `peer -> root/base` with no target member | GNU tar extraction returns nonzero and creates neither target nor peer |

## Prepared assertions

### False rejection

- exact two-patch zero-fuzz composition;
- Python compilation succeeds;
- predecessor status equals 1;
- stderr contains `hard-link target excluded by type filter: root/peer -> root/base`;
- output map equals `{base: REGTYPE}`;
- partial output extracts successfully and contains `final-name-target\n`;
- direct expected output extracts successfully;
- direct expected `base` and `peer` share one inode.

### False acceptance

- exact two-patch zero-fuzz composition;
- Python compilation succeeds;
- predecessor status equals 0;
- output map equals `{peer: LNKTYPE -> root/base}`;
- GNU tar extraction returns nonzero;
- output tree contains neither `root/base` nor `peer`.

## CI receipt

Initial characterization head: `ac21c095faae34fcd3cec3e4a7beae5a83979fe1`.

Linux Fieldwork CI run `30674423172` / run number 1100 was queued after draft PR #399 opened. The packet documentation commits advanced the PR head afterward, so the final exact-head run must be recorded in this file before disposition changes.

## Baseline evidence inherited from carriers

- PR #244 run `30590931312` passed at characterization head `c853da482a04a5ad49b53478b49e540fd4208b27`.
- PR #244 current-head integrity run `30594719522` passed at `d58deabce19ee98d506970674b537cb091381c5b`.
- PR #310 records current repair head `32dfa36a6feb533bc1126a11ef33979e45b410ec`; its latest run state must be treated as carrier evidence only, not unit-16 final-name evidence.

## Cleanup and rerun

The focused test creates archives, patched source copies, extraction directories, and bytecode below Python temporary directories. It opens no network connections, modifies no packages, creates no devices, and retains no process or filesystem state after the test process exits.

An immediate exact-command rerun remains required after the first successful exact-head execution.

## Tests pending

- focused test on the final packet head;
- immediate focused rerun after cleanup;
- transform-scope projection controls;
- output-name collision and duplicate-occurrence controls;
- inherited PR #248 candidate matrix;
- inherited PR #310 lifecycle and duplicate matrix;
- complete current Linux Fieldwork gate on the selected correction;
- package pipeline, other extractor, platform, and privileged metadata gates.

## Interpretation rule

A green characterization proves the predecessor has both final-name failure directions under the declared fixtures. It does not accept a correction. Candidate acceptance requires a new patch, red-to-green comparison, inherited matrix execution, cleanup, rerun, and complete-gate evidence on one exact head.
