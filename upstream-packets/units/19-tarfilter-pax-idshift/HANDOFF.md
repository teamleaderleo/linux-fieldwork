# Current handoff

Updated: `2026-08-01 08:09 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-19-tarfilter-pax-idshift` |
| Linux Fieldwork parent head before this final handoff commit | `480a3d596bf8c458138eac1acbd6bd738007174a` |
| Linux Fieldwork final head | the commit containing this `HANDOFF.md`; exact SHA is recorded in the #397 `UNIT CHECKPOINT` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, repository default branch |
| Upstream repository head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current tarfilter file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Imported/local tarfilter blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Imported native test blob | `6956e76aca153147d3a8a6668196d913ebc8a49e` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Source patch | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |
| Source patch SHA-256 | `b86da5f6a2f2f1757b5b3fc0e32ebeabeeadbdebebb4cdc1961d3d1ff5eb3303` |
| Native test patch | `patches/0002-tests-cover-pax-idshift.patch` |
| Native test patch SHA-256 | `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc` |
| Owning issue/PR | issue #37; PR #78 |
| Prior reviewed candidate | `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Latest workflow/run | Linux Fieldwork CI `30538012863`, success on prior reviewed candidate |

## Current bounded claim

Current mmdebstrap `tarfilter` retains PAX `uid` and `gid` strings after `--idshift` changes the numeric fields. Those strings override shifted large IDs during output serialization. Removing only the two stale numeric PAX keys after successful validation and shifting corrects large-ID output while preserving ordinary header behavior, unrelated PAX metadata, payloads, and inverse-shift ownership.

The existing native owner is `tests/tarfilter-idshift`. Its retained extension has an executable losing path: the baseline model exits `1` with `large ownership was not shifted`; the candidate model exits `0`.

## Work completed in this pass

- resumed the complete packet at branch head `79b748c20523306f4558a762b81a4f88f823dd0e`;
- re-read the exact imported native `tests/tarfilter-idshift` at blob `6956e76aca153147d3a8a6668196d913ebc8a49e`;
- confirmed the existing test already owns PAX xattr retention, zero-shift byte identity, ordinary ownership shifting, extraction checks, and inverse-shift byte identity;
- selected that file as the native regression owner;
- created `patches/0002-tests-cover-pax-idshift.patch`;
- added a large PAX uid/gid fixture plus an ordinary control, regenerated-key checks, unrelated-PAX and payload checks, and an inverse-shift check;
- extracted and executed the new detector against source-faithful baseline and candidate models;
- recorded baseline status `1`, candidate status `0`, exact diagnostic, and all patch/model/block digests in `TESTS.md`;
- updated `SOURCE_MAP.md` with both ordered patches and the exact two-file intended upstream fence;
- updated `DECISIONS.md` with native test ownership and one-commit packaging;
- removed all disposable `/tmp` files used by this pass;
- preserved the external-contact boundary.

## Changed paths in this continuation

- `upstream-packets/units/19-tarfilter-pax-idshift/patches/0002-tests-cover-pax-idshift.patch`
- `upstream-packets/units/19-tarfilter-pax-idshift/TESTS.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/SOURCE_MAP.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/DECISIONS.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/HANDOFF.md`

## Complete retained packet

- `README.md`
- `SOURCE_MAP.md`
- `DEEP_DIVE.md`
- `TESTS.md`
- `DECISIONS.md`
- `UPSTREAM_ISSUE.md`
- `UPSTREAM_PR.md`
- `HANDOFF.md`
- `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
- `patches/0002-tests-cover-pax-idshift.patch`
- `scripts/test_pax_idshift.py`

## Distinguishing observations

- current public tarfilter still increments `member.uid` and `member.gid` with no PAX numeric-key repair;
- current tarfilter file commit remains `87b9b385b38795c58bc13ffb33b8724bed27f7a0` while repository head is `77ec9be5417ee44c96343d2347145585da1b1f94`;
- baseline large ID after `+7`: `1000000000:1000000001`;
- baseline ordinary ID after `+7`: `1007:1008`;
- candidate large ID after `+7`: `1000000007:1000000008`, with matching regenerated PAX strings;
- candidate ordinary ID after `+7`: `1007:1008`, without numeric PAX keys;
- unrelated PAX comments `keep-large` and `keep-small` survived;
- inverse `-7` restored large and ordinary ownership;
- native detector baseline: status `1`, stderr `large ownership was not shifted`;
- native detector candidate: status `0`, empty stderr;
- `tests/tarfilter-idshift` is the narrow native owner; a separate test file would duplicate its setup and option contract;
- indexed canonical issue/PR search found no equivalent active correction on 2026-08-01.

## Exact new evidence

- complete native-test diff SHA-256: `1e0e984de35ca911ad2a015bc1046b1ecd861790b5bb39fe43b45a38a2f7b609`;
- retained `0002` patch SHA-256: `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc`;
- extracted detector block SHA-256: `5b8baf56cfd1c5264654ea395494d362dc28167e85dd221d93dba2a443631043`;
- baseline model SHA-256: `988f7d6a93f253ff7a02eb270d666f0c6ed2cfe99e9d0ca5bdef8dd0748d7487`;
- candidate model SHA-256: `0a88fb2f61fe43efcb85d81888bbac825ba09d7c9a3b40917d357b922cd6419f`.

## Gates completed

- prior exact imported-source regression: PASS on PR #78 exact head;
- prior independent exact-head review: ACCEPT;
- prior Linux Fieldwork CI: PASS, run `30538012863`;
- packet semantic probe: PASS on Python 3.13.5;
- immediate probe rerun and output comparison: PASS;
- current source persistence review: complete;
- indexed overlap refresh: complete;
- imported native test-owner review: complete;
- native test patch drafting: complete;
- native detector losing/winning model run: expected FAIL/PASS;
- retained patch packaging review: complete for `git apply --check` and `git apply` order;
- packet cleanup verification: `cleanup-ok`.

## Red or neutral runs classified

- early PR #78 patch revisions: patch-packaging failures before semantic execution; superseded by final block-replacement candidate;
- native detector baseline model: intended product failure, status `1`, exact diagnostic `large ownership was not shifted`;
- current upstream clone attempt: execution-environment DNS failure; zero source mutation occurred;
- complete upstream-native test: unexecuted because a current checkout and controlled fork remain unavailable.

## Cleanup state

All disposable source copies, generated diffs, extracted detector scripts, model scripts, outputs, and PAX archives under `/tmp` were removed and verified absent. This pass started no services, sockets, mounts, containers, locks, or package operations. The branch intentionally retains the packet files and two ordered patches. Shared imported source and test files remain unchanged.

## First incomplete step

Apply both retained patches, in order, to an exact checkout of upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`, then run the complete native `tests/tarfilter-idshift` through the project's focused test entry point.

## Next safe action

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap mmdebstrap
cd mmdebstrap
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git checkout -b linux-fieldwork/unit-19-tarfilter-pax-idshift

packet=/path/to/linux-fieldwork/upstream-packets/units/19-tarfilter-pax-idshift

git apply --check "$packet/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch"
git apply --check "$packet/patches/0002-tests-cover-pax-idshift.patch"
git apply "$packet/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch"
git apply "$packet/patches/0002-tests-cover-pax-idshift.patch"

git diff --check
git diff -- tarfilter tests/tarfilter-idshift
```

Then identify and run the repository's focused entry point for `tests/tarfilter-idshift`. Record the exact command, status, output, cleanup, immediate rerun, and resulting candidate commit in `TESTS.md` before considering broader gates.

## Unresolved blockers

- technical: exact current-head application and complete native test execution;
- compatibility: alternate Python and external tar-reader matrix remain optional review questions after the native gate;
- overlap: indexed search is clean; recheck before authorization;
- environment or tooling: this execution environment could not resolve the canonical Forgejo or GitHub hosts for cloning;
- authority: external contact is unauthorized;
- destination: controlled upstream fork and candidate branch are absent.

## Files to read first

1. `README.md`
2. `HANDOFF.md`
3. `TESTS.md`
4. `SOURCE_MAP.md`
5. `DECISIONS.md`
6. `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
7. `patches/0002-tests-cover-pax-idshift.patch`
8. issue #37 and PR #78 exact head/review

## External-contact state

`false; none occurred`. The #397 claim and checkpoint are internal Linux Fieldwork coordination actions. No upstream issue, pull request, comment, email, review, reaction, or other public upstream action occurred.

## Do not repeat

- avoid rebuilding every PAX key; it risks unrelated metadata loss;
- avoid assigning numeric PAX strings directly to ordinary IDs; key removal preserves the writer's representation choice;
- avoid using the early malformed PR #78 patch revisions;
- avoid creating a second upstream test file before new evidence changes the ownership decision;
- avoid editing shared `upstream/mmdebstrap/tarfilter` or its test on the packet branch;
- avoid folding unit 18 no-option passthrough or unit 15 broader metadata work into this candidate;
- avoid rerunning the packet model merely to rediscover the baseline; proceed to exact current-head application and the complete native test.
