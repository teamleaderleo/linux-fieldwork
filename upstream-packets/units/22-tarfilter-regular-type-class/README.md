# Unit 22 — mmdebstrap tarfilter regular-file type class

State: `HOLD`  
Priority-zero issue: #397, unit 22  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-22-tarfilter-regular-type-class`  
External contact authorized: `false`

## TL;DR

The retained candidate makes `--type-exclude=REGTYPE` and `--type-exclude=0` treat tar type flags `b"0"` and `b"\0"` as one regular-file class. The exact Linux Fieldwork candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7` passed focused CI run `30537313944`; its negative control proves the imported baseline leaks the NUL-type member. Submission remains on hold until the active tarfilter series establishes the final upstream patch order and an exact current Salsa checkout is available for rebase and native-test placement.

## Accomplished behavior

`REGTYPE` and numeric selector `0` exclude both regular-file encodings accepted by Python's `tarfile` module. Other member classes remain independent.

## Why care

A caller selecting the regular-file class can otherwise receive a legacy NUL-flagged regular payload. The raw type-byte comparison violates the option's class-level meaning.

## Scope

### Included

- `TypeFilterAction` mapping for `REGTYPE` and `0`;
- archive fixture with `REGTYPE`, `AREGTYPE`, and directory controls;
- baseline leak, candidate exclusion, selector-alias, and over-filtering checks.

### Excluded

- type-excluded hard-link dependency handling, owned by unit 16;
- transforms and PAX/path metadata semantics, owned by unit 15;
- other tarfilter fixes in units 01 and 18–21;
- vendor-specific or unknown type flags.

### Split boundary

This unit changes only selector-to-type-class mapping. It does not alter member ordering, link resolution, path rewriting, metadata handling, or archive output.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended base branch | `master` |
| Upstream base commit | Current exact `master` unresolved in this runtime; retained import resolves `debian/1.5.7-3` to `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | proposed `linux-fieldwork/unit-22-tarfilter-regular-type-class` after fork creation |
| Candidate head | retained Linux Fieldwork source candidate `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7` |
| Linux Fieldwork branch | `upstream/unit-22-tarfilter-regular-type-class` |
| Linux Fieldwork head | see `HANDOFF.md` |
| Imported/local source identity | `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Patch or series path | `patches/0001-tarfilter-treat-nul-as-regular.patch` |
| Proposed destination | Debian mmdebstrap Salsa project |
| Delivery method | `GitLab/Salsa fork and merge request`; fork still needed |

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
- Imported baseline `debian/1.5.7-3` removes `REGTYPE` and retains `AREGTYPE` under `--type-exclude=REGTYPE`.
- The retained one-line candidate excludes both encodings for selector spellings `REGTYPE` and `0`.
- `DIRTYPE` remains independent and prevents an over-filtering false positive.
- Linux Fieldwork CI run `30537313944` succeeded on exact candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`.

### Pending demonstration

- clean application to an exact current Salsa `master` commit;
- placement in mmdebstrap's current native test suite;
- focused native test and broader relevant gate on that exact candidate;
- composition after active tarfilter units settle their final order.

### Compatibility boundary

The candidate broadens only the existing regular selector to the second POSIX/Python-accepted regular-file byte. It leaves all other type selectors and raw member bytes unchanged.

## Candidate organization

One source patch and one focused archive-level regression belong in a single upstream commit because the test directly defines the selector class corrected by the source line.

1. `tarfilter: treat NUL and 0 as regular-file types`

## Current disposition

`HOLD` — blocker: the final patch layer cannot be selected until active tarfilter units 01, 15, and 16 publish their final candidate order and an exact current Salsa checkout can be inspected. Discriminator: those packets identify their final heads/order and a current `master` commit is fetched for clean application plus native-test execution.

## Next human decision

No send decision is ready. After the hold discriminator clears, decide whether to authorize creation of the controlled Salsa fork and merge request.

## Authority

Internal repository reads, branch creation, packet drafting, retained patch/test work, and issue checkpoints are authorized. No upstream issue, merge request, email, comment, review, or other contact has been authorized or made.
