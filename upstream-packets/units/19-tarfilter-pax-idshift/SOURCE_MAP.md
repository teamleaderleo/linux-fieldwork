# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `tarfilter`, `main()` id-shift block | file commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0`; repository head `77ec9be5417ee44c96343d2347145585da1b1f94` | Current public source still shifts `member.uid`/`member.gid` and retains stale numeric PAX keys. |
| Upstream tests | `tests/tarfilter-idshift` | imported blob `6956e76aca153147d3a8a6668196d913ebc8a49e` | Existing test owns xattr retention, zero-shift identity, ordinary shifting, and inverse-shift identity. The retained `0002` patch adds the missing forced-large-ID PAX case. |
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
| Unit 19 packet | branch `upstream/unit-19-tarfilter-pax-idshift` | upstream-root source patch, native test patch, semantic probe, drafts, decisions, handoff | current preparation owner |

## Candidate code

| File | Lines or symbols | Change | Owning patch |
| --- | --- | --- | --- |
| upstream `tarfilter` | `main()`, immediately after `member.uid += args.idshift` and `member.gid += args.idshift` | remove stale `member.pax_headers["uid"]` and `["gid"]` | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| upstream `tests/tarfilter-idshift` | large uid/gid member requiring PAX numeric keys plus ordinary control | large member reads with original IDs after `+7`; detector exits 1 with `large ownership was not shifted` | both members shift; large PAX values regenerate; unrelated PAX data and payloads survive; inverse shift restores IDs; detector exits 0 |
| packet `scripts/test_pax_idshift.py` | Python tarfile semantic probe | retained PAX strings override changed fields | removing only numeric keys produces shifted values and keeps unrelated PAX data |
| Linux Fieldwork `tests/test_tarfilter_pax_idshift.py` | exact imported tarfilter plus retained patch | exact baseline loses large-ID shift | candidate passes large/ordinary, payload, regenerated-key, and round-trip assertions |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-19-tarfilter-pax-idshift`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS BRANCH`
- Retained source patch: `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
- Source patch SHA-256: `b86da5f6a2f2f1757b5b3fc0e32ebeabeeadbdebebb4cdc1961d3d1ff5eb3303`
- Retained native test patch: `patches/0002-tests-cover-pax-idshift.patch`
- Native test patch SHA-256: `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc`
- Intended patch application command:

```sh
git checkout -b linux-fieldwork/unit-19-tarfilter-pax-idshift \
  77ec9be5417ee44c96343d2347145585da1b1f94
git apply --check /path/to/0001-tarfilter-regenerate-shifted-pax-ownership.patch
git apply --check /path/to/0002-tests-cover-pax-idshift.patch
git apply /path/to/0001-tarfilter-regenerate-shifted-pax-ownership.patch
git apply /path/to/0002-tests-cover-pax-idshift.patch
```

The two retained patches are preparation artifacts. The intended upstream candidate is one commit changing exactly `tarfilter` and `tests/tarfilter-idshift`, because the source invariant and its regression form one reviewable behavior change.

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| parse PAX numeric ownership | Python `tarfile` reader populates `TarInfo` and `pax_headers` | unchanged | large fixture contains string PAX `uid`/`gid` |
| validate negative shift | `tarfilter` | unchanged | validation precedes mutation and key removal |
| update numeric IDs | `tarfilter` changes `TarInfo.uid`/`gid` | unchanged | source block and ordinary control |
| choose output numeric metadata | stale input PAX strings override shifted fields | Python writer derives metadata from shifted fields after stale-key removal | baseline/candidate probe, PR #78 regression, native detector statuses `1/0` |
| retain unrelated PAX metadata | `tarfilter` filtered PAX dictionary | unchanged except numeric ownership keys | packet probe and native draft preserve `comment` keys |
| emit member payload | `tarfile.addfile()` | unchanged | prior regression, packet round trip, and native draft assertions preserve payloads |
| native regression ownership | ordinary id-shift test lacked a PAX-large discriminator | existing `tests/tarfilter-idshift` covers both ordinary and PAX-large numeric ownership | imported test review and retained `0002` patch |

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
- user/group names and unrelated PAX keys: numeric `--idshift` does not claim those fields;
- shared imported `upstream/mmdebstrap/tarfilter` and test files: the packet retains patches instead of mutating the common import.
