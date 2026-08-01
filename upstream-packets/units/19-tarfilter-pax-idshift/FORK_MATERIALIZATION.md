# Controlled fork materialization

Observed: `2026-08-01 16:09 +08:00`  
Unit: issue #397, unit 19  
External contact authorized: `false`

## Controlled repository

| Item | Exact value |
| --- | --- |
| Repository | `teamleaderleo/mmdebstrap` |
| Repository URL | `https://github.com/teamleaderleo/mmdebstrap` |
| Visibility | public |
| Access | owner/admin/push |
| Default branch | `master` |
| Default branch head | `574048f2a720057b75e56622003932f344dc700a` |
| Default branch head message | `feat: update mmdebstrap to 1.5.7-3` |
| Candidate branch | `linux-fieldwork/unit-19-tarfilter-pax-idshift` |
| Candidate head | `07e89c68dbed198b04bb60aeb1947433f6ead0b0` |
| Source commit | `1cd61501e18b5ffd861eceac9b70b1284fb0a0b6` |
| Native-test commit | `07e89c68dbed198b04bb60aeb1947433f6ead0b0` |
| Compare status | ahead by 2, behind by 0 |
| Changed-file fence | `tarfilter`; `tests/tarfilter-idshift` |
| Attached commit statuses | none observed |

## Base identity and lineage classification

The GitHub repository is a package-source mirror with its own commit lineage. It is not the canonical Forgejo repository and its `master` commit SHA is not the canonical upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`.

The two decisive base blobs nevertheless match the exact packet/import identities:

| Path | Fork `master` blob | Packet/import blob | Match |
| --- | --- | --- | --- |
| `tarfilter` | `ad776167a8473d5d15dbe22e850f4f6db35cf278` | `ad776167a8473d5d15dbe22e850f4f6db35cf278` | exact |
| `tests/tarfilter-idshift` | `6956e76aca153147d3a8a6668196d913ebc8a49e` | `6956e76aca153147d3a8a6668196d913ebc8a49e` | exact |

This repository therefore supplies a controlled writable branch and exact target-file materialization. It does not by itself establish a clean rebase onto the canonical repository lineage or prove that every non-target file equals canonical head.

## Materialized change

Commit `1cd61501e18b5ffd861eceac9b70b1284fb0a0b6` adds only:

```python
member.pax_headers.pop("uid", None)
member.pax_headers.pop("gid", None)
```

immediately after validated numeric uid/gid shifting.

Commit `07e89c68dbed198b04bb60aeb1947433f6ead0b0` extends `tests/tarfilter-idshift` with:

- one member whose uid/gid require PAX numeric records;
- one ordinary-header control;
- shifted numeric ownership assertions;
- regenerated PAX uid/gid assertions;
- unrelated PAX comment preservation;
- payload preservation;
- inverse-shift ownership round trip;
- trap cleanup for generated archives.

## Candidate blob identities

| Path | Candidate blob |
| --- | --- |
| `tarfilter` | `8c40acebba1734a26140790cfc59b72c62a98971` |
| `tests/tarfilter-idshift` | `cd749c063e754c4503771988fa1e5802076db0b0` |

## Diff fence

Comparison of `master...linux-fieldwork/unit-19-tarfilter-pax-idshift` reports:

- status: `ahead`;
- commits: `2`;
- behind: `0`;
- `tarfilter`: `+2/-0`;
- `tests/tarfilter-idshift`: `+85/-2`;
- no other changed paths.

The two test deletions are the replacement of the original trap line and the prior end-of-file boundary as represented by GitHub's diff accounting; no original test behavior was intentionally removed.

## Tests and statuses

No GitHub commit statuses or workflow checks were attached to candidate head `07e89c68dbed198b04bb60aeb1947433f6ead0b0` when inspected.

The project-native focused gate remains:

```sh
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
```

That gate must execute with QEMU enabled. It also exercises Black on `tarfilter` and ShellCheck/shfmt on the rendered native test.

## Remaining lineage requirement

Before upstream authorization, either:

1. import/fetch canonical head `77ec9be5417ee44c96343d2347145585da1b1f94` into a controlled repository and rebuild the candidate on that exact commit; or
2. obtain a newer canonical head, record it, and rebase/reapply the same two-file change there.

The current mirror branch is useful for review and test execution, but it is not a substitute for the canonical-lineage receipt.

## Authority boundary

Creating and updating the user's controlled fork branch is internal preparation authorized by the user's request. No issue, pull request, comment, review, reaction, email, or other communication was sent to the canonical upstream project.