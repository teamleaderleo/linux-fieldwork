# Source map — unit 16

## Imported and prerequisite source

| Role | Path or carrier | Exact identity | Notes |
| --- | --- | --- | --- |
| imported tarfilter | `upstream/mmdebstrap/tarfilter` | blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Type exclusion occurs before strip and transform processing. |
| unit-15 rewrite prerequisite | `patches/0000-unit15-transform-metadata-prerequisite.patch` | copied from unit 15 patch blob `38510533dc015182f3e87e9d2f3777eea5b8c93b` | Adds clean strip/link rewriting, five-field transforms, `_sed_substitute`, scope handling, and PAX cleanup. |
| current upstream repository | `https://salsa.debian.org/debian/mmdebstrap.git` | branch `master`; exact head pending | Current-master fetch and rebase remain. |

## Canonical carriers

| Carrier | Exact identity | Ownership |
| --- | --- | --- |
| Issue #243 | current issue record | Original type-excluded hard-link defect and bounded rejection policy. |
| PR #244 | merge `29ac38765bbbe99ed62313da54e7e0022b8cb9c3`; executed head `c853da482a04a5ad49b53478b49e540fd4208b27` | Executed dangling-output baseline and neighboring LNKTYPE control. |
| PR #248 | head `f1b013832b5f3b073a9131de83ce89077771a7ea` | First focused rejection, archive-root prefix normalization, independent filters, first-peer behavior. |
| PR #310 | head `32dfa36a6feb533bc1126a11ef33979e45b410ec` | Archive finalization, retained duplicate target, and post-skip retention timing. |
| Issue #335 | current issue record | Pre-rewrite versus final projected identity question. |
| unit 15 | `upstream/unit-15-tarfilter-transform-metadata` | Clean rewrite prerequisite replacing the historical PR #68 patch carrier. |
| PR #399 | current unit branch | Internal CI and packet carrier. |

## Active ordered patch series

| Order | Path | Purpose |
| ---: | --- | --- |
| 0 | `patches/0000-unit15-transform-metadata-prerequisite.patch` | Establish the member, hard-link target, transform scope, occurrence, and PAX rewrite contract. |
| 1 | `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` | Add finalized type-dependency rejection and retained duplicate target state. |
| 2 | `patches/0002-use-rewritten-identities-for-type-hardlinks.patch` | Project excluded members and retained hard-link targets into final identity space before dependency comparison. |

## Rejected patch evidence

| Path | Rejection reason |
| --- | --- |
| `patches/rejected/0002-alias-projection-overattributes-strip-breaks.patch` | Intermediate aliases turn a strip-only broken reference into a misleading type-filter diagnostic. Run `30690434953` proves the patch is mechanically green; the direct control rejects its policy. |

## Packet-owned tests

| Test | Claims |
| --- | --- |
| `tests/test_tarfilter_type_excluded_final_name_identity.py` | Exact blob loading, zero-fuzz series, compilation, valid final target acceptance, genuine removed-target rejection, strip-dropped link behavior, and pre-existing strip-break boundary. |
| `tests/test_tarfilter_type_excluded_inherited_matrix.py` | Prefix equivalence, distinct dot prefix, independent filters and immediate rerun, first-peer stopping, retained duplicate targets, transformed collisions, transformed removed targets, and uppercase `H` boundary. |

## Source ownership map

### Type exclusion

`type_filter_should_skip(member)` owns removal by `--type-exclude`. Unit 16 projects the skipped member's name through member-name strip and transform scope only when that projection survives.

### Name rewriting

Unit 15 owns:

- component stripping for `member.name`;
- component stripping for hard-link `member.linkname`;
- transform occurrence semantics;
- member (`r`), hard-link (`h`), and symlink (`s`) scopes;
- stale PAX `path` and `linkpath` removal.

### Dependency state

Patch 0001 supplies finalized rejection and retained occurrence state. Patch 0002 replaces input-name comparison with normalized final projected identities. Original input names remain for stderr.

### Attribution boundary

A reference already broken without type exclusion stays outside unit 16. The direct strip and uppercase-`H` controls enforce this boundary.

## Inherited tests and evidence

| Carrier or test | Reused claim |
| --- | --- |
| `tests/test_tarfilter_type_excluded_hardlink_target.py` | Original baseline and neighboring LNKTYPE control. |
| `tests/test_tarfilter_type_excluded_hardlink_candidate.py` | Genuine removed target, leading prefixes, distinct `.../`, independent filters, and first-peer stopping. |
| `tests/test_tarfilter_type_excluded_hardlink_patch_contract.py` | Exact patch composition and syntax. |
| `tests/test_tarfilter_type_excluded_duplicate_target.py` | Finalized output, retained duplicate target, and post-skip retention timing. |
| unit-15 tests | Transform occurrence, scope, hard-link target rewriting, and PAX regeneration compatibility. |

## Superseded or historical carriers

- PR #281 remains useful stale-stack history; PR #310 is the selected lifecycle/duplicate predecessor.
- PR #68 records the reviewed transform-scope history, while unit 15 supplies the exact clean prerequisite used here.
- The alias-projection candidate is retained solely as rejected evidence.
- Issue #240 and PR #241 define path-filter compatibility and remain outside this type-filter correction.

## Branch map

| Role | Branch |
| --- | --- |
| Linux Fieldwork unit | `upstream/unit-16-tarfilter-type-hardlinks` |
| Initial rejection | `fix/tarfilter-type-excluded-hardlink-target` |
| Duplicate/lifecycle repair | `repair/tarfilter-retained-duplicate-target-v2` |
| Unit-15 prerequisite | `upstream/unit-15-tarfilter-transform-metadata` |
| Controlled Salsa fork | `NEEDS FORK` |

## External destination

- project: `https://salsa.debian.org/debian/mmdebstrap`;
- repository: `https://salsa.debian.org/debian/mmdebstrap.git`;
- intended base: `master`;
- delivery: GitLab/Salsa fork and merge request;
- current-master exact commit: pending;
- external authorization: absent;
- external contact made: none.
