# Tests and receipts — unit 16

## Exact identities

| Item | Identity |
| --- | --- |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported tarfilter | blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Transform/strip patch | blob `1703984aa0c030e5131618a3541ee85bfd68ec65` |
| PR #310 predecessor | head `32dfa36a6feb533bc1126a11ef33979e45b410ec` |
| Packet predecessor patch | `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` |
| Final-identity candidate patch | `patches/0002-use-rewritten-identities-for-type-hardlinks.patch` |
| Focused test | `tests/test_tarfilter_type_excluded_final_name_identity.py` |
| Candidate matrix head | `655cd649df333d93082f98136e15740e3630950a` |
| Internal PR | #399 |

## Focused command

```sh
python3 -m unittest tests.test_tarfilter_type_excluded_final_name_identity -v
```

The test performs these setup gates:

```sh
patch --batch --forward --fuzz=0 -p1 \
  -i investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch
patch --batch --forward --fuzz=0 -p1 \
  -i upstream-packets/units/16-tarfilter-type-hardlinks/patches/0001-compose-pr310-predecessor-on-transform-carrier.patch
python3 -m py_compile upstream/mmdebstrap/tarfilter
patch --batch --forward --fuzz=0 -p1 \
  -i upstream-packets/units/16-tarfilter-type-hardlinks/patches/0002-use-rewritten-identities-for-type-hardlinks.patch
python3 -m py_compile upstream/mmdebstrap/tarfilter
```

The imported source bytes are captured when the test module is imported. Each case writes those frozen bytes into its own `TemporaryDirectory`, so earlier tests cannot mutate the source selected for composition.

## Red-to-green matrix

| Case | Input and options | Required predecessor result | Required candidate result |
| --- | --- | --- | --- |
| false rejection | regular `prefix/base`; excluded symlink `root/base`; hard link `root/peer -> root/base`; `--type-exclude=SYMTYPE --strip-components=1` | status 1; finalized partial archive containing regular `base` | status 0; `base` plus `peer -> base`; GNU tar extraction succeeds and preserves one inode |
| false acceptance | excluded regular `root/base`; hard link `prefix/peer -> prefix/root/base`; `--type-exclude=REGTYPE --strip-components=1` | status 0; broken `peer -> root/base` | status 1; original-name diagnostic; finalized valid empty archive |
| genuine removed target | excluded regular `root/base`; hard link `root/peer -> root/base`; `--type-exclude=REGTYPE` | status 1; empty archive | status 1; same focused diagnostic and empty archive |
| strip-dropped target and link | regular `base`; excluded symlink `base`; hard link `root/peer -> base`; `--type-exclude=SYMTYPE --strip-components=1` | status 1 under input-name checking | status 0; finalized valid empty archive because both the target identity and dependent link are dropped by strip semantics |

## Exact CI history

### Run 1100 — malformed predecessor carrier

- technical head: `ac21c095faae34fcd3cec3e4a7beae5a83979fe1`;
- run: `30674423172`;
- job: `91298597515`;
- result: failure in `Validate changed patch carriers`;
- exact evidence:

```text
patches/0001-compose-pr310-predecessor-on-transform-carrier.patch:4:
hunk count mismatch: declared old/new 12/31, observed 11/29
```

Compilation and tests did not run. Commit `9ecda06a2ec7ba6dc7fade41d3ad13842220a741` corrected only the hunk header to `11/29`.

### Run 1118 — carrier valid, test source contaminated by suite order

- head: `9ecda06a2ec7ba6dc7fade41d3ad13842220a741`;
- run: `30689716762`;
- job: `91342161441`;
- patch validation: passed, `1 patch file` and `3 hunks`;
- Python compilation: passed;
- full discovery: retained 440 tests;
- result: 438 passed, the two unit-16 tests failed before source execution.

Exact setup failure in each test:

```text
patching file upstream/mmdebstrap/tarfilter
Hunk #1 FAILED at 68.
Hunk #2 succeeded at 275 (offset 2 lines).
Hunk #3 succeeded at 299 (offset -2 lines).
1 out of 3 hunks FAILED
```

The focused test copied the live repository source at execution time. Earlier transform tests can modify that file in their own negative-control workflow, so the selected bytes depended on discovery order. Commit `f71f7b0462cca85a94417665214b5a91918c1f42` freezes `SOURCE_BYTES` at module import and writes those exact bytes into each disposable candidate tree.

### Run 1127 — final-identity candidate matrix

- exact technical head: `655cd649df333d93082f98136e15740e3630950a`;
- run: `30690001217`;
- patch validation: passed;
- Python compilation: passed;
- full unit suite: in progress at this record update.

Record the final job ID, result, focused assertions, cleanup, and immediate rerun after completion.

## Baseline evidence inherited from carriers

- PR #244 run `30590931312` passed at characterization head `c853da482a04a5ad49b53478b49e540fd4208b27`.
- PR #244 current-head integrity run `30594719522` passed at `d58deabce19ee98d506970674b537cb091381c5b`.
- PR #310 records current repair head `32dfa36a6feb533bc1126a11ef33979e45b410ec`; its result is predecessor evidence, not final-name candidate acceptance.

## Cleanup and rerun

The focused test creates archives, patched source copies, extraction directories, rejects, and bytecode below Python temporary directories. It opens no network connections, modifies no packages, creates no devices, and retains no process or filesystem state after the test process exits.

An immediate exact-command rerun remains required after the first successful exact-head execution.

## Tests pending

- completed receipt for run `30690001217`;
- immediate focused rerun after cleanup;
- transform-scope projection controls;
- output-name collision and duplicate-occurrence controls;
- inherited PR #248 candidate matrix;
- inherited PR #310 lifecycle and duplicate matrix;
- complete current Linux Fieldwork gate on the selected correction;
- package pipeline, other extractor, platform, and privileged metadata gates.

## Interpretation rule

A green four-case matrix proves the selected final-identity correction for the declared fixtures. Candidate acceptance still requires inherited matrices, collision and transform-scope controls, cleanup, immediate rerun, complete-diff review, and a complete current gate on one exact head.
