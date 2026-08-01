# Unit 22 — mmdebstrap tarfilter regular-file type class

State: `ACTIVE`  
Priority-zero issue: #397, unit 22  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-22-tarfilter-regular-type-class`  
External contact authorized: `false`

## TL;DR

The retained candidate makes `--type-exclude=REGTYPE` and `--type-exclude=0` treat tar type flags `b"0"` and `b"\0"` as one regular-file class. The exact Linux Fieldwork candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7` passed focused CI run `30537313944`; its negative control proves the baseline leaks the NUL-type member.

Current upstream is now identified as `josch/mmdebstrap` `main@77ec9be5417ee44c96343d2347145585da1b1f94`. Its `tarfilter` still maps `REGTYPE`/`0` only to `tarfile.REGTYPE`, so the defect remains current. Review of units 01, 15, and 16 shows no direct source-owner conflict: unit 22 changes `TypeFilterAction`, while those units own transform parsing/metadata and hard-link dependency logic. Technical work remains, so this unit is `ACTIVE` until current-upstream native-test integration and execution are complete.

## Accomplished behavior

`REGTYPE` and numeric selector `0` exclude both regular-file encodings accepted by Python's `tarfile` module. Other member classes remain independent.

## Why care

A caller selecting the regular-file class can otherwise receive a legacy NUL-flagged regular payload. The raw type-byte comparison violates the option's class-level meaning.

## Scope

### Included

- `TypeFilterAction` mapping for `REGTYPE` and `0`;
- archive fixture with `REGTYPE`, `AREGTYPE`, and directory controls;
- baseline leak, candidate exclusion, selector-alias, and over-filtering checks;
- current-upstream source verification and native-test placement.

### Excluded

- type-excluded hard-link dependency handling, owned by unit 16;
- transforms and PAX/path metadata semantics, owned by unit 15;
- GNU basic/extended transform regex compatibility, owned by unit 01;
- other tarfilter fixes in units 18–21;
- vendor-specific or unknown type flags.

### Split boundary

This unit changes only selector-to-type-class mapping. It does not alter member ordering, link resolution, path rewriting, metadata handling, or archive output. Adjacent tarfilter patches may be composed for a complete-gate run, but their completion order does not block this unit's independent implementation or review.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current upstream `tarfilter` | still contains `items.append(tarfile.REGTYPE)` for `REGTYPE`/`0`; relevant source matches imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Debian package mirror | `debian/1.5.7-3`, resolved commit `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | proposed `linux-fieldwork/unit-22-tarfilter-regular-type-class` after authorization and fork creation |
| Candidate head | retained Linux Fieldwork source candidate `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7` |
| Linux Fieldwork branch | `upstream/unit-22-tarfilter-regular-type-class` |
| Linux Fieldwork head | see `HANDOFF.md` and issue #397 checkpoint |
| Imported/local source identity | `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Patch or series path | `patches/0001-tarfilter-treat-nul-as-regular.patch` |
| Proposed destination | canonical `josch/mmdebstrap` Forgejo project |
| Delivery method | controlled fork branch and pull request; `NEEDS FORK` |

## Canonical links

- Priority-zero unit: #397 unit 22
- Owning Linux Fieldwork issue: #76
- Canonical Linux Fieldwork PR or composition: #77, merged as `4b9e24b0b20c1398dcae825310c6b7d0d5c273d0`
- Predecessor issue and PR: #76 and #77
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- Python classifies both `tarfile.REGTYPE` and `tarfile.AREGTYPE` members as regular files.
- Imported baseline removes `REGTYPE` and retains `AREGTYPE` under `--type-exclude=REGTYPE`.
- Current upstream `main@77ec9be5417ee44c96343d2347145585da1b1f94` still carries the same defective selector mapping.
- The retained one-line candidate excludes both encodings for selector spellings `REGTYPE` and `0`.
- `DIRTYPE` remains independent and prevents an over-filtering false positive.
- Linux Fieldwork CI run `30537313944` succeeded on exact candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`.
- Unit 01 owns `TransformAction` regex grammar; unit 15 owns transform/link/PAX behavior; unit 16 owns hard-link dependency state. None requires unit 22 to wait for a final patch order.
- Upstream-native individual tests run through `coverage.py`, with the project documenting `CMD=./mmdebstrap ./coverage.py --dist unstable <test-name>`.

### Pending demonstration

- materialized checkout at exact upstream commit `77ec9be5417ee44c96343d2347145585da1b1f94`;
- clean patch application in that checkout;
- placement of the regression in mmdebstrap's current native test suite;
- focused native test and relevant broader gate on the exact candidate;
- cleanup and immediate rerun;
- complete candidate diff and overlap review on the materialized checkout.

### Compatibility boundary

The candidate broadens only the existing regular selector to the second POSIX/Python-accepted regular-file byte. It leaves all other type selectors and raw member bytes unchanged.

## Candidate organization

One source patch and one focused archive-level regression belong in a single upstream commit because the test directly defines the selector class corrected by the source line.

1. `tarfilter: treat NUL and 0 as regular-file types`

## Current disposition

`ACTIVE` — current upstream and source ownership are resolved. Native-test integration, exact-checkout execution, cleanup/rerun, and complete-diff review remain technical work.

## Next human decision

No decision is required yet. After the remaining technical gates pass, the unit will move to `READY FOR AUTHORIZATION` for your review and send/hold decision.

## Authority

Internal repository reads, branch creation, packet drafting, retained patch/test work, rebasing, testing, and issue checkpoints are authorized. No upstream issue, pull request, email, comment, review, fork contact, or other public interaction has been authorized or made.
