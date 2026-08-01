# Unit 19 — tarfilter preserves shifted PAX uid/gid semantics

State: `ACTIVE`  
Priority-zero issue: #397, unit 19  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-19-tarfilter-pax-idshift`  
External contact authorized: `false`

## TL;DR

`tarfilter --idshift` changes `TarInfo.uid` and `TarInfo.gid`, while retained PAX `uid` and `gid` strings can override those shifted values in the emitted archive. The retained source patch removes only the stale numeric PAX keys after validation and shifting, allowing Python to regenerate correct large IDs. The retained native-test patch extends the existing `tests/tarfilter-idshift` owner with a large-ID discriminator that loses on the current model and passes on the candidate model.

The project instructions are now mapped exactly. The focused readiness command is `CMD=./mmdebstrap ./coverage.sh tarfilter-idshift` after `./make_mirror.sh`; it requires QEMU, checks `tarfilter` with Black, and checks the generated native test with ShellCheck and shfmt. A current upstream checkout, controlled candidate branch, and exact QEMU-backed run remain.

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
- native test ownership and exact project gate mapping;
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
| Imported native test identity | `upstream/mmdebstrap/tests/tarfilter-idshift`, blob `6956e76aca153147d3a8a6668196d913ebc8a49e` |
| Prior reviewed candidate | PR #78 head `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Retained source patch | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |
| Retained native-test patch | `patches/0002-tests-cover-pax-idshift.patch` |
| Proposed destination | canonical mmdebstrap repository |
| Delivery method | Forgejo/Gitea fork and pull request; pending explicit authorization |

## Canonical links

- Priority-zero unit: #397 unit 19
- Owning Linux Fieldwork issue: #37
- Canonical Linux Fieldwork PR: #78
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Project instructions and gate map: [`PROJECT_INSTRUCTIONS.md`](PROJECT_INSTRUCTIONS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- current upstream tarfilter still shifts fields while retaining stale PAX numeric keys;
- prior exact-source CI run `30538012863` passed on PR #78 head `8d6443626e4338b180ec0533969bfe4d32b20d52`;
- fresh Python 3.13.5 probe reproduced large-ID baseline failure and candidate success twice with identical output;
- unrelated `comment` PAX metadata and file payloads survived;
- inverse shift restored both ordinary and large IDs;
- the draft native detector exits `1` with `large ownership was not shifted` on the baseline model and exits `0` on the candidate model;
- the exact focused project gate, formatter/linter behavior, QEMU requirement, and Debian autopkgtest skip behavior are recorded.

### Remaining technical work

- clean application to a checked-out current upstream repository head;
- Black success for `tarfilter`;
- generated-test ShellCheck and shfmt success;
- QEMU-backed `CMD=./mmdebstrap ./coverage.sh tarfilter-idshift` success and immediate rerun;
- complete current-upstream two-file diff review;
- controlled fork and clean candidate branch;
- current overlap recheck before authorization.

### Compatibility boundary

The candidate removes only PAX `uid` and `gid` after a successful nonzero shift. Python emits regenerated numeric PAX keys when required and ordinary tar header fields when values fit. Every other retained PAX key, member payload, mode, name, and link field crosses unchanged through this correction.

## Candidate organization

One reviewable upstream commit assembled from two retained preparation patches:

1. `tarfilter: regenerate shifted PAX ownership` — two source lines and the native large-ID regression in `tests/tarfilter-idshift`.

## Current disposition

`ACTIVE` — source behavior, native ownership, detector behavior, and project gate requirements are established; current-upstream materialization and exact QEMU-backed gates remain.

## Next human decision

No send decision is ready. The next internal action is to create or verify a controlled mmdebstrap fork, materialize both retained patches on exact upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`, and run the project-aligned focused gate.

## Authority

Internal reads, branch work, tests, packet drafting, and issue checkpoints are authorized. External issues, pull requests, comments, email, reviews, reactions, and other contact remain unauthorized. No external contact occurred during this pass.