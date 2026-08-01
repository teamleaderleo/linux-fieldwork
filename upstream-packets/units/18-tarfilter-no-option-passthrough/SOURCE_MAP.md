# Source map

## Upstream source

| Role | Identity | Relevance |
| --- | --- | --- |
| Canonical repository | `josch/mmdebstrap` on Muffin Gitea | Intended destination |
| Base branch/head | `main` at `77ec9be5417ee44c96343d2347145585da1b1f94` | Current repository base observed 2026-08-01 |
| File | `tarfilter` | Entire unit source boundary |
| Last file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` | Current file content identity |
| Local imported file | `upstream/mmdebstrap/tarfilter` | Exact test baseline |
| Local imported Git blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Matches current displayed upstream file content |

## Candidate and tests

| Path | Ownership |
| --- | --- |
| `investigations/tarfilter-no-option-passthrough/tarfilter-no-option-passthrough.patch` | Canonical source patch for unit 18 |
| `tests/test_tarfilter_no_option_passthrough.py` | Negative control, byte-identity matrix, zero-value controls, and all active-operation controls |
| `investigations/tarfilter-no-option-passthrough/README.md` | Earlier technical record |
| `notes/filesystems/no-op-archive-filters-must-preserve-bytes.md` | Reusable principle and evidence boundary |

## Linux Fieldwork carriers read

| Carrier | Role | Disposition for unit 18 |
| --- | --- | --- |
| #397 | Priority-zero unit definition and workflow authority | Authoritative initiative |
| #29 | Root cause, consequences, current-upstream check | Canonical issue |
| #27 | Earlier duplicate | Closed; retain only as provenance |
| PR #46 | Focused accepted implementation and regression | Canonical merged internal carrier |
| PR #33 | Earlier combined sparse/path/no-op stack | Superseded for unit 18 by PR #46 |
| PR #23 | Active sparse rewrite candidate | Adjacent work; excluded from this unit |
| LF-14 sparse artifacts | Sparse corruption consequence | Evidence only; implementation excluded |

## Linked evidence details

- PR #46 exact accepted head: `8c8f45872e6eb2b4ea770e5753c6dc66347c8f56`.
- PR #46 successful Linux Fieldwork CI: run `30534506273`.
- PR #33 review explicitly selected PR #46 as the stronger independent no-option proof.
- PR #33's GitGuardian alert was classified as a false positive caused by a synthetic `.secret` pathname; no credential was present.

## Current branch changes

| Commit | Change |
| --- | --- |
| `bcd9a7c54e4f4a1c7523a32e94923d0f63fa1ae3` | Regenerated patch hunk for clean zero-fuzz application |
| `748f95cf0470d2c9ba96b8432c3cac7d2267aaeb` | Added `--fuzz=0` enforcement and path/PAX/type/strip active-operation controls |
| later packet commits | Durable unit records |

## External destination

- Proposed method: Gitea fork and pull request.
- Controlled fork: `NEEDS FORK`.
- External authorization: `false`.
- External contact made: none.
