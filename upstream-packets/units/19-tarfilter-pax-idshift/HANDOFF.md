# Current handoff

Updated: `2026-08-01 07:53 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-19-tarfilter-pax-idshift` |
| Linux Fieldwork parent head before this final handoff commit | `bac2f37aa2a514b03e7a71dc621b146361298df6` |
| Linux Fieldwork final head | the commit containing this `HANDOFF.md`; exact SHA is recorded in the #397 `UNIT CHECKPOINT` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, repository default branch |
| Upstream repository head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current tarfilter file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Imported/local tarfilter blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Retained patch | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |
| Retained patch SHA-256 | `b86da5f6a2f2f1757b5b3fc0e32ebeabeeadbdebebb4cdc1961d3d1ff5eb3303` |
| Owning issue/PR | issue #37; PR #78 |
| Prior reviewed candidate | `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Latest workflow/run | Linux Fieldwork CI `30538012863`, success on prior reviewed candidate |

## Current bounded claim

Current mmdebstrap `tarfilter` retains PAX `uid` and `gid` strings after `--idshift` changes the numeric fields. Those strings override shifted large IDs during output serialization. Removing only the two stale numeric PAX keys after successful validation and shifting corrects large-ID output, preserves ordinary header behavior, unrelated PAX metadata, and payloads, and supports an inverse-shift round trip.

## Work completed in this pass

- read issue #397, packet protocol, index, issue #37, its comment, PR #78 metadata, full changed-file patch, and review;
- refreshed current canonical repository, tarfilter file, Debian source package, native test presence, and indexed overlap;
- claimed unit 19 internally and created `upstream/unit-19-tarfilter-pax-idshift` from main `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`;
- created the complete required packet bundle;
- retained a clean upstream-root two-line source patch;
- added a packet-local Python PAX semantic regression;
- ran the regression twice on Python 3.13.5 and compared identical outputs;
- recorded exact baseline, candidate, round-trip, digests, environment, exclusions, decisions, drafts, and unexecuted gates;
- preserved the external-contact boundary.

## Changed paths

- `upstream-packets/units/19-tarfilter-pax-idshift/README.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/SOURCE_MAP.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/DEEP_DIVE.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/TESTS.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/DECISIONS.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/UPSTREAM_ISSUE.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/UPSTREAM_PR.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/HANDOFF.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
- `upstream-packets/units/19-tarfilter-pax-idshift/scripts/test_pax_idshift.py`

## Distinguishing observations

- current public tarfilter still increments `member.uid` and `member.gid` with no PAX numeric-key repair;
- current tarfilter file commit remains `87b9b385b38795c58bc13ffb33b8724bed27f7a0` even though repository head advanced to `77ec9be5417ee44c96343d2347145585da1b1f94`;
- baseline large ID after `+7`: `1000000000:1000000001`;
- baseline ordinary ID after `+7`: `1007:1008`;
- candidate large ID after `+7`: `1000000007:1000000008`, with matching regenerated PAX strings;
- candidate ordinary ID after `+7`: `1007:1008`, without numeric PAX keys;
- unrelated PAX comments `keep-large` and `keep-small` survived;
- inverse `-7` restored large and ordinary ownership;
- indexed canonical issue/PR search found no equivalent active correction on 2026-08-01;
- existing upstream-native `tests/tarfilter-idshift` is the correct test owner and needs a forced-large-ID extension.

## Gates completed

- prior exact imported-source regression: PASS on PR #78 exact head;
- prior independent exact-head review: ACCEPT;
- prior Linux Fieldwork CI: PASS, run `30538012863`;
- fresh semantic probe: PASS on Python 3.13.5;
- immediate rerun and output comparison: PASS;
- current source persistence review: complete;
- indexed overlap refresh: complete;
- retained patch packaging review: complete; use `git apply --check` and `git apply`.

## Red or neutral runs classified

- early PR #78 patch revisions: patch-packaging failures before semantic execution; superseded by final block-replacement candidate;
- current upstream clone attempt: execution-environment DNS failure; no source mutation occurred;
- broad upstream-native gates: unexecuted because a current checkout and controlled fork were unavailable.

## Cleanup state

The fresh probe created disposable files under `/tmp` and used in-memory tar archives. It started no services, sockets, mounts, containers, locks, or package operations. The packet branch intentionally retains the documents, patch, and script listed above. The shared imported source remains unchanged.

## First incomplete step

Obtain a current upstream checkout at `77ec9be5417ee44c96343d2347145585da1b1f94`, verify the retained source patch with `git apply --check`, inspect the exact current `tests/tarfilter-idshift`, and add the forced-large-ID regression in its native shell style.

## Next safe action

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap mmdebstrap
cd mmdebstrap
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git checkout -b linux-fieldwork/unit-19-tarfilter-pax-idshift
git apply --check \
  /path/to/linux-fieldwork/upstream-packets/units/19-tarfilter-pax-idshift/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch
git apply \
  /path/to/linux-fieldwork/upstream-packets/units/19-tarfilter-pax-idshift/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch
sed -n '1,240p' tests/tarfilter-idshift
```

Then extend `tests/tarfilter-idshift` with the large PAX uid/gid fixture and record the exact focused baseline/candidate command before running it.

## Unresolved blockers

- technical: native shell-test edit and exact current-head gate remain;
- compatibility: alternate Python and external tar-reader matrix remain optional review questions;
- overlap: indexed search is clean; recheck before authorization;
- environment or tooling: this execution environment could not resolve GitHub or Forgejo hosts for cloning;
- authority: external contact is unauthorized;
- destination: controlled upstream fork and candidate branch are absent.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. issue #37 and PR #78 exact head/review
7. current upstream `tarfilter` and `tests/tarfilter-idshift`

## External-contact state

`false; none occurred`. The #397 claim and checkpoint are internal Linux Fieldwork coordination actions. No upstream issue, pull request, comment, email, review, or other public upstream action occurred.

## Do not repeat

- avoid rebuilding every PAX key; it risks unrelated metadata loss;
- avoid assigning numeric PAX strings to ordinary IDs; key removal preserves the writer's representation choice;
- avoid using the early malformed PR #78 patch revisions;
- avoid editing shared `upstream/mmdebstrap/tarfilter` on the packet branch;
- avoid folding unit 18 no-option passthrough or unit 15 broader metadata work into this candidate;
- avoid rerunning the packet semantic probe solely to rediscover the baseline; proceed to native current-head materialization.
