# Unit 22 — mmdebstrap tarfilter regular-file type class

State: `ACTIVE`  
Priority-zero issue: #397, unit 22  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-22-tarfilter-regular-type-class`  
External contact authorized: `false`

## TL;DR

The retained candidate makes `--type-exclude=REGTYPE` and `--type-exclude=0` treat tar type flags `b"0"` and `b"\0"` as one regular-file class. Historical exact-source CI at candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7` passed run `30537313944`, including a baseline negative control that leaks the NUL-type member.

Canonical upstream is `josch/mmdebstrap` `main@77ec9be5417ee44c96343d2347145585da1b1f94`. Its relevant `tarfilter` content matches Linux Fieldwork Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` and still maps `REGTYPE`/`0` only to `tarfile.REGTYPE`, so the defect remains current.

This packet now carries the proposed upstream-native shell test, its exact `coverage.txt` registration stanza, and a Linux Fieldwork gate that requires native failure on the unchanged source, zero-fuzz patch application, and two candidate passes. Internal draft PR #410 exists solely to obtain exact-head Linux Fieldwork CI. The hosted run is queued; queued is not success. The unit remains `ACTIVE` until hosted exact-source and complete-upstream native gates are reviewed.

## Accomplished behavior

`REGTYPE` and numeric selector `0` exclude both regular-file encodings accepted by Python's `tarfile` module and GNU tar. Other member classes remain independent, and a `DIRTYPE` control preserves both regular payloads byte-for-byte.

## Why care

A caller selecting the documented regular-file class can otherwise receive a legacy NUL-flagged regular payload. The source currently uses a byte-specific definition for filtering and a class definition for payload copying, so the same member is “not regular” at exclusion time and regular at output time.

## Scope

### Included

- `TypeFilterAction` mapping for `REGTYPE` and `0`;
- archive fixture with `REGTYPE`, `AREGTYPE`, and directory controls;
- baseline leak, candidate exclusion, selector-alias, retained-payload, and over-filtering checks;
- current-upstream source verification;
- upstream-native test placement and registration;
- exact-source Linux Fieldwork integration gate;
- bounded active-overlap search.

### Excluded

- type-excluded hard-link dependency handling, owned by unit 16;
- transforms and PAX/path metadata semantics, owned by unit 15;
- GNU basic/extended transform regex compatibility, owned by unit 01;
- other tarfilter fixes in units 18–21;
- vendor-specific or unknown type flags;
- public upstream submission.

### Split boundary

This unit changes only selector-to-type-class mapping. It does not alter member ordering, link resolution, path rewriting, metadata handling, or archive output encoding. Adjacent tarfilter patches may be composed for a complete-gate run, but their completion order does not block this unit's independent implementation, test, or review.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current upstream `tarfilter` | relevant content matches blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; `REGTYPE`/`0` still stores only `tarfile.REGTYPE` |
| Debian package mirror | `debian/1.5.7-3`, resolved commit `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | proposed `linux-fieldwork/unit-22-tarfilter-regular-type-class` only after authorization and fork creation |
| Candidate head | retained Linux Fieldwork source candidate `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7` |
| Linux Fieldwork branch | `upstream/unit-22-tarfilter-regular-type-class` |
| Internal integration PR | draft PR #410 |
| Linux Fieldwork head | see `HANDOFF.md` and issue #397 checkpoint |
| Imported/local source identity | `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Source patch | `patches/0001-tarfilter-treat-nul-as-regular.patch` |
| Proposed native test | `native/tests/tarfilter-regular-type-class` |
| Proposed native registry entry | `native/coverage.txt.fragment` |
| Exact-source integration gate | `tests/test_unit22_tarfilter_native_packet.py` |
| Proposed destination | canonical `josch/mmdebstrap` Forgejo project |
| Delivery method | controlled fork branch and pull request; `NEEDS FORK` |

## Canonical links

- Priority-zero unit: #397 unit 22
- Owning Linux Fieldwork issue: #76
- Canonical historical candidate: PR #77, merged as `4b9e24b0b20c1398dcae825310c6b7d0d5c273d0`
- Current internal integration: draft PR #410
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- Python 3.13.5 classifies both `tarfile.REGTYPE` and `tarfile.AREGTYPE` members as regular files and round-trips their distinct type bytes and payloads.
- GNU tar 1.35 lists and extracts both encodings as ordinary regular files.
- Current upstream `main@77ec9be5417ee44c96343d2347145585da1b1f94` still carries the defective selector mapping.
- Historical exact-source baseline removes `REGTYPE` and retains `AREGTYPE` under `--type-exclude=REGTYPE`.
- The retained one-line candidate excludes both encodings for selector spellings `REGTYPE` and `0`.
- `DIRTYPE` remains independent and preserves both regular payloads.
- Historical Linux Fieldwork CI run `30537313944` succeeded on exact candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`.
- A proposed upstream-native shell test and exact `coverage.txt` stanza are retained.
- The native shell test fails on a faithful baseline model and passes twice on the candidate model.
- Unit 01 owns `TransformAction` grammar; unit 15 owns transform/link/PAX behavior; unit 16 owns hard-link dependency state. None owns regular selector membership.
- A bounded current Forgejo issue/pull-request search found no equivalent visible work; refresh before submission.

### Pending demonstration

- draft PR #410 exact-head CI completion and log review;
- shellcheck/shfmt acceptance through the actual upstream test path;
- complete checkout at `77ec9be5417ee44c96343d2347145585da1b1f94`;
- clean source/test/registry application with zero fuzz and zero offsets;
- focused upstream-native execution, relevant broader gate, cleanup, and immediate rerun;
- executable test mode in the final upstream diff;
- complete composed diff and refreshed overlap review.

### Compatibility boundary

The candidate broadens only the existing regular selector to the second standard/legacy regular-file byte. It leaves all other type selectors, unknown type flags, retained member bytes, paths, links, metadata, status handling, and diagnostics unchanged.

## Candidate organization

One upstream commit:

1. `tarfilter: treat NUL and 0 as regular-file types`
   - one-line `TypeFilterAction` correction;
   - `tests/tarfilter-regular-type-class`;
   - matching `coverage.txt` registration.

## Current disposition

`ACTIVE` — implementation, native test design, current-source identity, cross-consumer semantics, and bounded overlap review are complete. Hosted exact-source integration and complete-checkout upstream gates remain ordinary technical work.

## Next human decision

No decision is required yet. After the remaining technical gates pass, the unit moves to `READY FOR AUTHORIZATION` for review and a deliberate send/hold decision.

## Authority

Internal repository reads, branch creation, packet drafting, internal draft PRs, rebasing, testing, review, and issue checkpoints are authorized. No upstream issue, pull request, email, comment, review, fork contact, or other public interaction has been authorized or made.
