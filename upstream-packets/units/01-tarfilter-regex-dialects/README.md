# Unit 01 — mmdebstrap tarfilter regex dialects

State: `ACTIVE`  
Priority-zero issue: #397, unit 01  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-01-tarfilter-regex-dialects`  
External contact authorized: `false`

## TL;DR

The retained candidate distinguishes GNU basic-regex transforms from explicit extended mode, rejects the characterized Python-only and malformed forms before archive output, and retains direct GNU tar differential tests. The internal repaired product head and the later accepted-neighbor proof are green.

This continuation completed the linked-carrier audit through merged PR #220, refreshed Debian archive and BTS overlap evidence, and identified the upstream-native test runner. Debian sid/forky currently publish source package `mmdebstrap 1.5.7-3`; Debian Sources lists its `tarfilter` as 11,453 bytes, and a package-version mirror carries Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, equal to the Linux Fieldwork import. That is strong package-source corroboration, while exact canonical Salsa `master` remains unresolved and therefore still blocks the issue #397 current-upstream gate.

## Accomplished behavior

Default transforms use the characterized GNU basic-regex spelling. The `x` flag selects the characterized extended spelling. The translator preserves capture numbering, contextual basic anchors, target scopes, and numeric occurrence selection. Unsupported POSIX bracket constructs, unresolved alphabetic escapes, Python-only `(?...)` groups, malformed active intervals, and proven-invalid consecutive basic intervals fail before archive processing. Unmatched extended closing parentheses remain literal when no group is open.

The active-`(?` guard also preserves the accepted neighboring forms proved by PR #220:

```text
s/\(?/X/x
s/[(?]/X/x
s/\(/X/x
```

## Why care

The imported implementation compiles transform patterns directly with Python `re`. A default expression such as `s/a+/b/` therefore renames member `aaa` to `b`, while GNU tar's default basic mode leaves `aaa` unchanged. Silent archive-path divergence can alter member names and link targets while producing a plausible archive.

## Scope

### Included

- default GNU basic versus explicit `x` extended dialect selection;
- characterized operators, groups, backreferences, anchors, intervals, and repeated quantifiers;
- rejection of Python-only special groups and unresolved bracket/escape forms;
- accepted escaped-parenthesis and bracket-state neighbors of the group guard;
- malformed active interval and unmatched extended-close parity repairs;
- composition with target scopes and numeric occurrence selectors;
- direct GNU tar 1.35 differentials under `LC_ALL=C`.

### Excluded

- POSIX classes, collating elements, equivalence classes, and locale-sensitive matching;
- GNU alphabetic escapes;
- persistent `flags=` statements and expression lists;
- replacement case-conversion state;
- complete diagnostic parity and denial-of-service policy;
- adjacent transform/PAX semantics owned by unit 15.

### Split boundary

The regex dialect translator remains one reviewable unit because the core and repair patches modify the same parser boundary and share one differential matrix. Broader transform target/PAX behavior remains a prerequisite patch state and a separate upstream semantic unit unless current-source review proves a smaller independently mergeable extraction.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | `mmdebstrap` |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap` |
| Intended base branch | `master` |
| Upstream base commit | `UNRESOLVED — exact current Salsa master unavailable in this runtime` |
| Current Debian archive source | `1.5.7-3` in sid/forky; Salsa tag `debian/1.5.7-3` at abbreviated commit `6fde9997` |
| Debian archive `tarfilter` observation | 11,453 bytes in Debian Sources |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Canonical product carrier | PR #151 head `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`; merge `1a1952a78f79b2473f1f9513c1d5820f58987594` |
| Final grammar repair carrier | PR #216 head `55d20a4cc08c93b34961c679bdb73458fea4c408`; merge `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f` |
| Accepted-neighbor proof carrier | PR #220 head `bb0a79dec47958c6b865d4b382a44baff17ab736`; merge `ed49c01a85e9d363626db5d2973a33b67209e13b` |
| Linux Fieldwork branch | `upstream/unit-01-tarfilter-regex-dialects` |
| Linux Fieldwork starting head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | `upstream/mmdebstrap/tarfilter`, Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Patch or series path | four ordered patches listed in `SOURCE_MAP.md` |
| Proposed destination | canonical mmdebstrap Salsa project |
| Delivery method | `GitLab/Salsa fork and merge request`; authorization and controlled fork still required |

## Canonical links

- Priority-zero unit: #397 unit 01
- Owning Linux Fieldwork issue: #212
- Canonical implementation and repair: PRs #151 and #216
- Superseded duplicate repair: PR #202
- Accepted-neighbor proof history: PR #203, retained and merged through PR #220
- Characterization: PR #113
- Draft carrier: PR #211
- Prerequisite source carriers: PRs #48, #56, #68, and #102
- Parent defect records: issues #36, #63, #98, and #108
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- imported base Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
- exact four-patch order and blob identities;
- baseline direct-Python mismatch and candidate expectations encoded in focused tests;
- 23-test GNU tar 1.35 matrix previously passed twice on the repaired branch and twice on current-main synthetic merges;
- hosted exact-head run `30581672669` / job `625` passed repaired head `55d20a4cc08c93b34961c679bdb73458fea4c408`;
- PR #220 exact-head CI `30582215292` / 634 succeeded; direct inherited suite passed twice, current-main focused suite passed 15/15, and full regex discovery passed 38/38;
- Debian archive source remains `1.5.7-3`, with no BTS entry found for equivalent tarfilter regex-dialect work in the 2026-08-01 search;
- native runner identified: `coverage.py` copies `./tarfilter` to `shared/tarfilter`, and README documents `CMD=./mmdebstrap ./coverage.py ...` for individual tests.

### Yet to demonstrate

- exact current canonical Salsa `master` commit and `tarfilter` blob;
- clean application or regeneration on that exact base;
- focused GNU matrix on the exact current-source candidate;
- upstream-native focused and broader execution on the rebased candidate;
- complete current-source diff and Salsa issue/MR overlap review;
- controlled fork, candidate branch, and compare URL.

### Compatibility boundary

The claim covers the executed `LC_ALL=C` GNU tar 1.35 subset. Unresolved grammar fails early instead of expanding the claim to complete GNU/POSIX compatibility.

## Candidate organization

1. prerequisite transform target-scope patch from PR #68;
2. prerequisite numeric occurrence patch from PR #102;
3. regex dialect translation patch from PR #151;
4. consolidated edge/parity repair patch carrying PR #202 and PR #216 behavior;
5. proof-only accepted-neighbor test from PR #220, with no product-source change.

Current-upstream review must decide whether prerequisites already exist upstream, belong in unit 15, or require an ordered series. The dialect and repair changes themselves belong in one review unit.

## Current disposition

`ACTIVE` — exact canonical Salsa source retrieval, current-source application/regeneration, current-source tests, and Salsa overlap/diff review remain.

## Next human decision

No send decision is ready. After the technical gates pass, decide whether to authorize creation of a controlled Salsa fork and submission of the prepared merge request.

## Authority

Internal repository reads, branch work, packet drafting, rebasing, testing, and issue checkpoints are authorized. External Salsa, Debian, GNU, mailing-list, email, issue, merge-request, comment, or review contact remains unauthorized. No upstream contact occurred during this work.
