# Unit 01 — mmdebstrap tarfilter regex dialects

State: `ACTIVE`  
Priority-zero issue: #397, unit 01  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-01-tarfilter-regex-dialects`  
External contact authorized: `false`

## TL;DR

The retained candidate distinguishes GNU basic-regex transforms from explicit extended mode, rejects the characterized Python-only and malformed forms before archive output, and retains direct GNU tar differential tests. Internal exact-head evidence is green. The remaining technical gate is an exact rebase onto current canonical Salsa `master`, followed by upstream-native tests, complete-diff review, and overlap recheck.

This session pinned the carrier chain, imported source, ordered patch blobs, and focused test blobs. The runtime could not resolve `github.com` for a local checkout and could not retrieve an exact current Salsa commit, so no current-upstream patch application or fresh execution is claimed.

## Accomplished behavior

Default transforms use the characterized GNU basic-regex spelling. The `x` flag selects the characterized extended spelling. The translator preserves capture numbering, contextual basic anchors, target scopes, and numeric occurrence selection. Unsupported POSIX bracket constructs, unresolved alphabetic escapes, Python-only `(?...)` groups, malformed active intervals, and proven-invalid consecutive basic intervals fail before archive processing. Unmatched extended closing parentheses remain literal when no group is open, matching the retained GNU tar 1.35 controls.

## Why care

The imported implementation compiles transform patterns directly with Python `re`. A default expression such as `s/a+/b/` therefore renames member `aaa` to `b`, while GNU tar's default basic mode leaves `aaa` unchanged. Silent archive-path divergence can alter member names and link targets while producing a plausible archive.

## Scope

### Included

- default GNU basic versus explicit `x` extended dialect selection;
- characterized operators, groups, backreferences, anchors, intervals, and repeated quantifiers;
- rejection of Python-only special groups and unresolved bracket/escape forms;
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
| Upstream base commit | `UNRESOLVED — exact current Salsa master was unavailable in this session` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate head | retained Linux Fieldwork repaired head `55d20a4cc08c93b34961c679bdb73458fea4c408`; internal merge `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f` |
| Linux Fieldwork branch | `upstream/unit-01-tarfilter-regex-dialects` |
| Linux Fieldwork starting head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | `upstream/mmdebstrap/tarfilter`, Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Patch or series path | four ordered patches listed in `SOURCE_MAP.md` |
| Proposed destination | canonical mmdebstrap Salsa project |
| Delivery method | `GitLab/Salsa fork and merge request`; authorization and controlled fork still required |

## Canonical links

- Priority-zero unit: #397 unit 01
- Owning Linux Fieldwork issue: #212
- Canonical implementation and repair: PRs #151, #202, and #216
- Characterization: PR #113
- Draft carrier: PR #211
- Prerequisite source carriers: PRs #68 and #102
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
- cleanup/rerun and complete internal diff review recorded by #212 and PR #216.

### Yet to demonstrate

- exact current canonical Salsa base commit;
- clean application of the ordered patch state onto that exact base;
- upstream-native test entry points on the rebased candidate;
- fresh complete diff and active-equivalent-work search;
- controlled fork, candidate branch, and compare URL.

### Compatibility boundary

The claim covers the executed `LC_ALL=C` GNU tar 1.35 subset. It deliberately rejects unresolved grammar instead of asserting complete GNU/POSIX compatibility.

## Candidate organization

1. prerequisite transform target-scope patch from PR #68;
2. prerequisite numeric occurrence patch from PR #102;
3. regex dialect translation patch from PR #151;
4. consolidated edge/parity repair patch carrying PR #202 and PR #216 behavior.

Current-upstream review must decide whether prerequisites already exist upstream, belong in unit 15, or require an ordered series. The dialect and repair changes themselves belong in one review unit.

## Current disposition

`ACTIVE` — current canonical source retrieval, rebase, upstream tests, and fresh overlap/diff review remain.

## Next human decision

No send decision is ready. After the technical gates pass, decide whether to authorize creation of a controlled Salsa fork and submission of the prepared merge request.

## Authority

Internal repository reads, branch work, packet drafting, rebasing, testing, and issue checkpoints are authorized. External Salsa, Debian, GNU, mailing-list, email, issue, merge-request, comment, or review contact remains unauthorized. No upstream contact occurred during this session.
