# Unit 19 — tarfilter preserves shifted PAX uid/gid semantics

State: `ACTIVE`  
Priority-zero issue: #397, unit 19  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-19-tarfilter-pax-idshift`  
External contact authorized: `false`

## TL;DR

`tarfilter --idshift` changes `TarInfo.uid` and `TarInfo.gid`, while retained PAX `uid` and `gid` strings can override those shifted values in the emitted archive. The candidate removes only the stale numeric PAX keys after validation and shifting, allowing Python to regenerate correct large IDs. The existing native `tests/tarfilter-idshift` test now carries a forced-large-ID discriminator plus an ordinary control.

A controlled writable branch now exists in `teamleaderleo/mmdebstrap` at candidate head `07e89c68dbed198b04bb60aeb1947433f6ead0b0`. Its base repository is a package-source mirror with a different commit lineage from canonical Forgejo, but the two target base blobs exactly match the packet/import blobs. The branch cleanly changes only `tarfilter` and `tests/tarfilter-idshift`.

The project-aligned readiness command is `CMD=./mmdebstrap ./coverage.sh tarfilter-idshift` after `./make_mirror.sh`; it requires QEMU, checks `tarfilter` with Black, and checks the generated native test with ShellCheck and shfmt. Exact canonical-lineage materialization and the QEMU-backed run remain.

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
- controlled fork and branch materialization;
- current-upstream identity and overlap refresh.

### Excluded

- tarfilter path, transform, strip, hard-link, and type-filter semantics;
- byte-preserving no-option passthrough, owned by unit 18;
- broader transform/path/link/PAX metadata work, owned by unit 15;
- user/group name rewriting;
- public upstream submission or contact.

### Split boundary

This unit changes only the two numeric PAX keys whose stale values contradict `--idshift`. Rebuilding all PAX metadata would broaden compatibility risk and overlap unit 15.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Canonical head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current canonical tarfilter file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Controlled repository | `teamleaderleo/mmdebstrap` |
| Controlled repository type | GitHub package-source mirror; not canonical commit lineage |
| Controlled base branch/head | `master` at `574048f2a720057b75e56622003932f344dc700a` |
| Candidate branch | `linux-fieldwork/unit-19-tarfilter-pax-idshift` |
| Candidate head | `07e89c68dbed198b04bb60aeb1947433f6ead0b0` |
| Candidate source commit | `1cd61501e18b5ffd861eceac9b70b1284fb0a0b6` |
| Candidate source blob | `8c40acebba1734a26140790cfc59b72c62a98971` |
| Candidate native-test blob | `cd749c063e754c4503771988fa1e5802076db0b0` |
| Base source blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Base native-test blob | `6956e76aca153147d3a8a6668196d913ebc8a49e` |
| Linux Fieldwork branch | `upstream/unit-19-tarfilter-pax-idshift` |
| Linux Fieldwork starting head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Prior reviewed candidate | PR #78 head `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Retained source patch | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |
| Retained native-test patch | `patches/0002-tests-cover-pax-idshift.patch` |
| Proposed destination | canonical mmdebstrap repository |
| Delivery method | canonical Forgejo pull request after exact-lineage preparation and explicit authorization |

## Packet links

- [`SOURCE_MAP.md`](SOURCE_MAP.md)
- [`DEEP_DIVE.md`](DEEP_DIVE.md)
- [`TESTS.md`](TESTS.md)
- [`PROJECT_INSTRUCTIONS.md`](PROJECT_INSTRUCTIONS.md)
- [`FORK_MATERIALIZATION.md`](FORK_MATERIALIZATION.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- [`UPSTREAM_PR.md`](UPSTREAM_PR.md)
- [`HANDOFF.md`](HANDOFF.md)

## Current result

### Demonstrated

- current canonical tarfilter still shifts fields while retaining stale PAX numeric keys;
- prior exact-source CI run `30538012863` passed on PR #78 head `8d6443626e4338b180ec0533969bfe4d32b20d52`;
- fresh Python 3.13.5 probe reproduced large-ID baseline failure and candidate success twice with identical output;
- unrelated `comment` PAX metadata and file payloads survived;
- inverse shift restored both ordinary and large IDs;
- the native detector exits `1` with `large ownership was not shifted` on the baseline model and exits `0` on the candidate model;
- the exact focused project gate, formatter/linter behavior, QEMU requirement, and Debian autopkgtest skip behavior are recorded;
- a controlled candidate branch exists and is ahead by two commits, behind by zero, with exactly two changed paths;
- the controlled base versions of both target files exactly match the packet/import blobs;
- the materialized candidate contains the expected two-line source correction and native regression;
- no commit statuses or workflow checks were attached to the candidate head when inspected.

### Remaining technical work

- import or fetch the canonical commit lineage into a controlled repository and rebuild the candidate on the exact reviewed canonical head or its current successor;
- Black success for `tarfilter`;
- generated-test ShellCheck and shfmt success;
- QEMU-backed `CMD=./mmdebstrap ./coverage.sh tarfilter-idshift` success and immediate rerun;
- exact canonical-lineage two-file diff review;
- current overlap recheck before authorization.

### Compatibility boundary

The candidate removes only PAX `uid` and `gid` after a successful nonzero shift. Python emits regenerated numeric PAX keys when required and ordinary tar header fields when values fit. Every other retained PAX key, member payload, mode, name, and link field crosses unchanged through this correction.

## Candidate organization

The controlled branch currently contains two commits for traceability:

1. `1cd61501e18b5ffd861eceac9b70b1284fb0a0b6` — `tarfilter: regenerate shifted PAX ownership`;
2. `07e89c68dbed198b04bb60aeb1947433f6ead0b0` — `tests: cover PAX ownership id shifting`.

The intended upstream submission remains one reviewable commit combining the two-file behavior and regression.

## Current disposition

`ACTIVE` — source behavior, native ownership, detector behavior, project gate requirements, and a controlled mirror branch are established. Canonical-lineage materialization and exact QEMU-backed gates remain.

## Next internal action

Run the project-native focused gate on the controlled branch if a suitable QEMU-capable environment is available, while separately preparing an exact canonical-lineage branch. Record exact commands, statuses, outputs, cleanup, and rerun receipts before authorization.

## Authority

Internal reads, branch work, tests, packet drafting, and issue checkpoints are authorized. External issues, pull requests, comments, email, reviews, reactions, and other contact remain unauthorized. No canonical-upstream contact occurred during this pass.