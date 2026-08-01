# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `tarfilter`, `main()` id-shift block | file commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0`; repository head `77ec9be5417ee44c96343d2347145585da1b1f94` | Current public source still shifts `member.uid`/`member.gid` and retains stale numeric PAX keys. |
| Upstream tests | `tests/tarfilter-idshift` | present in mmdebstrap 1.5.7 sources, 3,961 bytes | Existing native test covers ordinary ID shifting; a forced PAX-large case remains to be added. |
| Package source | Debian source `mmdebstrap` | `1.5.7-3` in sid/forky; `1.5.7-1+deb13u1` in trixie | Both visible source lines retain the same id-shift implementation. |
| Contribution instructions | canonical repository issue/PR interface | observed 2026-08-01 | Proposed delivery is a controlled Forgejo/Gitea fork and PR after authorization. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Status |
| --- | --- | --- | --- |
| Issue #37 | closed 2026-07-30 | defect record, source analysis, reproducer, expected correction | canonical investigation |
| PR #78 | head `8d6443626e4338b180ec0533969bfe4d32b20d52`; merge `4df9ff80f01a0aef255e2c9011034d23e340cebe` | retained patch, exact-source regression, accepted review, CI receipt | canonical prior candidate |
| CI run `30538012863` | PR #78 exact head | exact-source focused and repository evidence | accepted receipt |
| `investigations/tarfilter-pax-idshift/` | merged through PR #78 | prior narrative and Linux Fieldwork-path patch | historical evidence |
| `tests/test_tarfilter_pax_idshift.py` | merged through PR #78 | exact imported-source baseline/candidate regression | retained negative control |

## Candidate code

| File | Lines or symbols | Change | Owning patch |
| --- | --- | --- | --- |
| upstream `tarfilter` | `main()`, immediately after `member.uid += args.idshift` and `member.gid += args.idshift` | remove stale `member.pax_headers["uid"]` and `["gid"]` | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| upstream `tests/tarfilter-idshift` | proposed large uid/gid member requiring PAX numeric keys plus ordinary control | large member reads with original IDs after `+7`; ordinary member shifts | both members shift; large PAX values regenerate; payloads survive; inverse shift restores IDs |
| packet `scripts/test_pax_idshift.py` | Python tarfile semantic probe | retained PAX strings override changed fields | removing only numeric keys produces shifted values and keeps unrelated PAX data |
| Linux Fieldwork `tests/test_tarfilter_pax_idshift.py` | exact imported tarfilter plus retained patch | exact baseline loses large-ID shift | candidate passes large/ordinary, payload, regenerated-key, and round-trip assertions |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-19-tarfilter-pax-idshift`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS BRANCH`
- Retained patch: `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
- Retained patch SHA-256: `b86da5f6a2f2f1757b5b3fc0e32ebeabeeadbdebebb4cdc1961d3d1ff5eb3303`
- Intended patch application command:

```sh
git checkout -b linux-fieldwork/unit-19-tarfilter-pax-idshift \
  77ec9be5417ee44c96343d2347145585da1b1f94
git apply --check /path/to/0001-tarfilter-regenerate-shifted-pax-ownership.patch
git apply /path/to/0001-tarfilter-regenerate-shifted-pax-ownership.patch
```

The retained directly applicable patch contains the source hunk. Add the upstream-native test edit in the materialized branch, then commit source and test together before final review.

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| parse PAX numeric ownership | Python `tarfile` reader populates `TarInfo` and `pax_headers` | unchanged | large fixture contains string PAX `uid`/`gid` |
| validate negative shift | `tarfilter` | unchanged | validation precedes mutation and key removal |
| update numeric IDs | `tarfilter` changes `TarInfo.uid`/`gid` | unchanged | source block and ordinary control |
| choose output numeric metadata | stale input PAX strings override shifted fields | Python writer derives metadata from shifted fields after stale-key removal | baseline/candidate probe and PR #78 regression |
| retain unrelated PAX metadata | `tarfilter` filtered PAX dictionary | unchanged except numeric ownership keys | packet probe preserves `comment` keys |
| emit member payload | `tarfile.addfile()` | unchanged | prior regression and packet round trip preserve payloads |

## Overlap and current upstream state

Search date: 2026-08-01.

- The canonical repository head observed was `77ec9be5417ee44c96343d2347145585da1b1f94`.
- `tarfilter` still shows the same uncorrected id-shift block; its latest file commit remains `87b9b385b38795c58bc13ffb33b8724bed27f7a0`.
- Searches of the indexed canonical issue and pull-request pages found no equivalent active PAX id-shift correction.
- Debian sid/forky source `1.5.7-3` retains the same behavior.

This search establishes the absence of an obvious indexed equivalent. Recheck immediately before authorization because Forgejo indexing may omit drafts or unindexed branches.

## Files deliberately not changed

- path normalization and include/exclude logic: unit 20/21 territory;
- no-option passthrough detection: unit 18;
- transform, target, and general PAX path/link metadata: unit 15;
- type filtering and hard-link dependency handling: units 22 and 16;
- user/group names and unrelated PAX keys: numeric `--idshift` does not claim those fields.
