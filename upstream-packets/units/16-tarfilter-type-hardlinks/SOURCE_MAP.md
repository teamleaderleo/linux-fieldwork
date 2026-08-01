# Source map — unit 16

## Imported source

| Role | Path or carrier | Exact identity | Notes |
| --- | --- | --- | --- |
| tarfilter implementation | `upstream/mmdebstrap/tarfilter` | blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Type exclusion precedes strip and transform processing. |
| canonical transform/strip patch | `investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch` | blob `1703984aa0c030e5131618a3541ee85bfd68ec65` | Rewrites member names and hard-link targets; clears stale PAX `path` and `linkpath`. |

## Canonical carriers

| Carrier | Exact identity | Ownership |
| --- | --- | --- |
| Issue #243 | current issue record | Original type-excluded hard-link defect and bounded rejection policy. |
| PR #244 | merge `29ac38765bbbe99ed62313da54e7e0022b8cb9c3`; executed code/test head `c853da482a04a5ad49b53478b49e540fd4208b27` | Executed baseline: dangling retained hard link after REGTYPE exclusion. |
| PR #248 | head `f1b013832b5f3b073a9131de83ce89077771a7ea` | First rejection candidate and normalized leading-prefix matrix. |
| PR #310 | head `32dfa36a6feb533bc1126a11ef33979e45b410ec` | Archive-finalization and retained-duplicate repairs. |
| Issue #335 | current issue record | Final-name identity defect after strip rewriting. |
| PR #68 | merge `e7388243f3436ceda16f9d5be70d5423cc379b9d` | Canonical member/link rewrite and PAX regeneration carrier. |
| PR #399 | branch head tracked in `HANDOFF.md` | Current internal unit workspace and CI carrier. |

## Packet-owned files

| Path | Purpose |
| --- | --- |
| `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` | Packet-local zero-fuzz composition of PR #310 behavior after the PR #68 transform/strip patch. |
| `tests/test_tarfilter_type_excluded_final_name_identity.py` | Two strip-induced identity discriminators from issue #335. |
| `README.md` | Current state, exact identities, scope, and disposition. |
| `DEEP_DIVE.md` | Mechanism, approach history, and correction constraints. |
| `TESTS.md` | Commands, expected results, CI receipts, cleanup, and unexecuted gates. |
| `DECISIONS.md` | Canonical-carrier and work-order decisions. |
| `HANDOFF.md` | Exact stopping point and first incomplete step. |

## Source ownership map

### Type exclusion

`type_filter_should_skip(member)` and the early `continue` in the archive loop own the original target-removal event.

### Name rewriting

The PR #68 patch owns:

- component stripping for `member.name`;
- component stripping for hard-link `member.linkname`;
- transform scopes for member names, hard-link targets, and symlink targets;
- stale PAX `path` and `linkpath` removal.

### Dependency state

PR #248 introduces the excluded-name set and focused error. PR #310 adds finalized exit and retained duplicate state. Unit 16 owns moving this state and comparison into a coherent final emitted-name domain.

## Test ownership

| Test | Claim |
| --- | --- |
| `tests/test_tarfilter_type_excluded_hardlink_target.py` | Original baseline and neighboring LNKTYPE control, merged through PR #244. |
| `tests/test_tarfilter_type_excluded_hardlink_candidate.py` | PR #248 genuine removed-target rejection, prefix equivalence, independent filters, and first-peer behavior. |
| `tests/test_tarfilter_type_excluded_hardlink_patch_contract.py` | PR #248 exact composition and syntax contract. |
| `tests/test_tarfilter_type_excluded_duplicate_target.py` | PR #310 finalized output, retained duplicate target, and strip-skipped non-retention. |
| `tests/test_tarfilter_type_excluded_final_name_identity.py` | Unit 16 false rejection and false acceptance after strip rewrites. |

## Superseded or historical carriers

- PR #281 preserves useful failed and stale-stack history; PR #310 replaces it as the duplicate/lifecycle carrier.
- PR #48 supplies part of the rewrite/PAX history; PR #68 is the canonical integrated transform-scope carrier.
- Issue #240 and PR #241 define path-filter compatibility and remain outside this type-filter correction.

## Branch map

| Role | Branch |
| --- | --- |
| Linux Fieldwork unit branch | `upstream/unit-16-tarfilter-type-hardlinks` |
| Initial rejection carrier | `fix/tarfilter-type-excluded-hardlink-target` |
| Duplicate/lifecycle repair carrier | `repair/tarfilter-retained-duplicate-target-v2` |
| Controlled upstream fork branch | `NEEDS FORK` |

## External destination

`NEEDS DESTINATION DECISION`. No upstream contact is authorized or made.
