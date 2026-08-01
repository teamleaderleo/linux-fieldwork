# Unit 19 — tarfilter preserves shifted PAX uid/gid semantics

State: `ACTIVE`  
Priority-zero issue: #397, unit 19  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-19-tarfilter-pax-idshift`  
External contact authorized: `false`

## TL;DR

`tarfilter --idshift` changes `TarInfo.uid` and `TarInfo.gid`, while retained PAX `uid` and `gid` strings can override those shifted values in the emitted archive. The retained two-line source patch removes only the stale numeric PAX keys after validation and shifting, allowing Python to regenerate correct large IDs. The prior exact-source regression passed, and a fresh Python 3.13.5 semantic probe reproduced the losing baseline, corrected output, unrelated-PAX preservation, and negative-shift round trip. A current upstream checkout, native test edit, and exact candidate branch remain to be materialized.

## Accomplished behavior

ID shifting produces the requested numeric ownership for ordinary members and members whose identities require PAX extended headers. Shifted large IDs are regenerated into PAX `uid` and `gid` fields, unrelated PAX metadata and payload bytes remain intact, and applying the inverse shift restores the original ownership.

## Why care

The current command exits successfully while silently leaving large PAX-carried IDs unchanged. Downstream images can therefore receive incorrect ownership even though ordinary header-sized controls appear correct.

## Scope

### Included

- stale PAX `uid` and `gid` authority after a validated nonzero `--idshift`;
- ordinary and PAX-large numeric ID controls;
- unrelated PAX metadata and payload preservation;
- positive shift and inverse negative-shift round trip;
- current-upstream identity and overlap refresh.

### Excluded

- tarfilter path, transform, strip, hard-link, and type-filter semantics;
- byte-preserving no-option passthrough, owned by unit 18;
- broader transform/path/link/PAX metadata work, owned by unit 15;
- user/group name rewriting;
- external submission or contact.

### Split boundary

This unit changes only the two numeric PAX keys whose stale values contradict `--idshift`. Rebuilding all PAX metadata would broaden compatibility risk and overlap unit 15.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `master` / repository default branch shown as current main line |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` (repository head observed 2026-08-01) |
| Current tarfilter file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Linux Fieldwork branch | `upstream/unit-19-tarfilter-pax-idshift` |
| Linux Fieldwork starting head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Prior reviewed candidate | PR #78 head `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Patch or series path | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |
| Proposed destination | canonical mmdebstrap repository |
| Delivery method | Forgejo/Gitea fork and pull request; pending explicit authorization |

## Canonical links

- Priority-zero unit: #397 unit 19
- Owning Linux Fieldwork issue: #37
- Canonical Linux Fieldwork PR: #78
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- current upstream tarfilter still shifts fields without removing stale PAX numeric keys;
- the Linux Fieldwork import is the same retained tarfilter blob used by the accepted candidate;
- prior exact-source CI run `30538012863` passed on PR #78 head `8d6443626e4338b180ec0533969bfe4d32b20d52`;
- fresh Python 3.13.5 probe reproduced large-ID baseline failure and candidate success twice with identical output;
- unrelated `comment` PAX metadata and file payloads survived;
- inverse shift restored both ordinary and large IDs.

### Not yet demonstrated

- clean application to a checked-out current upstream repository head;
- upstream-native `tests/tarfilter-idshift` extension and execution on the exact candidate head;
- complete current-upstream ordinary gate;
- controlled fork and clean candidate branch;
- exhaustive external tar-reader interoperability.

### Compatibility boundary

The candidate removes only PAX `uid` and `gid` after a successful nonzero shift. Python emits regenerated numeric PAX keys when required and ordinary tar header fields when values fit. Every other retained PAX key, member payload, mode, name, and link field crosses unchanged through this correction.

## Candidate organization

One reviewable patch:

1. `tarfilter: regenerate shifted PAX ownership` — two source lines plus an upstream-native large-ID regression to be added during materialization.

## Current disposition

`ACTIVE` — source behavior and focused semantics are established; current-upstream branch materialization and native gates remain.

## Next human decision

No send decision is ready. The next internal action is to create or verify a controlled mmdebstrap fork, materialize the patch and native test on exact upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`, and run the focused gate.

## Authority

Internal reads, branch work, tests, packet drafting, and issue checkpoints are authorized. External issues, pull requests, comments, email, reviews, and other contact remain unauthorized. No external contact occurred during this pass.
