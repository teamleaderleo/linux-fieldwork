# Unit 18 — mmdebstrap tarfilter byte-preserving no-option passthrough

State: `ACTIVE`  
Priority-zero issue: #397, unit 18  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-18-tarfilter-no-option-passthrough`  
External contact authorized: `false`

## TL;DR

Current mmdebstrap `main` still routes a no-option `tarfilter` invocation through Python tar parsing because `argparse` always creates `args.strip_components`. The retained correction now applies to the exact source with `--fuzz=0`, copies no-operation input byte-for-byte, and tests every modifying option category. An exact branch test run and final overlap refresh remain before authorization readiness.

## Accomplished behavior

`tarfilter` copies stdin to stdout byte-for-byte when path, PAX, type, strip, transform, and ID-shift operations are all inactive. Explicit `--strip-components=0` and `--idshift=0` retain no-operation behavior. Any active operation enters the archive rewrite path.

## Why care

The old guard is unreachable. A no-option call decompresses and re-emits compressed archives as uncompressed PAX and can route GNU sparse metadata through a lossy rewrite path.

## Scope

### Included

- value-aware no-operation predicate;
- exact refreshed patch carrier;
- plain, gzip, bzip2, xz, and GNU PAX sparse byte-identity regression;
- active path, PAX, type, strip, transform, and ID-shift controls.

### Excluded

- sparse-member rewriting while an operation is active;
- path normalization, dotfile identity, and parent retention;
- transform dialect and replacement semantics;
- PAX uid/gid ID-shift repair.

### Split boundary

PR #23 owns active sparse rewriting. Units 15, 19, 20, and 21 own adjacent tarfilter semantics. Unit 18 changes only selection of the existing byte-copy path.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current upstream tarfilter commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS FORK` |
| Candidate source/test head | `748f95cf0470d2c9ba96b8432c3cac7d2267aaeb` plus packet commits |
| Linux Fieldwork branch | `upstream/unit-18-tarfilter-no-option-passthrough` |
| Linux Fieldwork head | branch `HEAD`; exact final SHA is recorded in the #397 checkpoint |
| Imported/local source identity | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Patch path | `investigations/tarfilter-no-option-passthrough/tarfilter-no-option-passthrough.patch` |
| Proposed destination | canonical mmdebstrap repository |
| Delivery method | `Gitea fork and pull request`; controlled fork required |

## Canonical links

- Priority-zero unit: #397 unit 18
- Owning Linux Fieldwork issue: #29
- Canonical Linux Fieldwork PR: #46
- Duplicate carrier: #27
- Composition carrier: #33
- Related active-sparse carrier: #23
- Investigation: `investigations/tarfilter-no-option-passthrough/README.md`
- Reusable note: `notes/filesystems/no-op-archive-filters-must-preserve-bytes.md`
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- current upstream displays the same six modifying option categories and unreachable guard;
- local imported source is byte-identical to the current upstream `tarfilter` content shown at its last file commit;
- the previous retained patch applied with fuzz 2;
- the refreshed patch applies with `patch --fuzz=0` and compiles;
- the baseline rewrites gzip input;
- the candidate preserves plain, gzip, bzip2, xz, GNU sparse, strip-zero, and ID-shift-zero inputs byte-for-byte;
- each active operation category produces its expected semantic result.

### Yet to demonstrate

- exact committed branch test execution in a clean checkout or hosted job;
- final current overlap search across upstream issues and pull requests;
- controlled fork identity and candidate source commit.

### Compatibility boundary

Explicit numeric zero follows the existing implementation's truthiness behavior. A caller-supplied transform remains an active operation even when its expression happens to leave a particular member unchanged.

## Candidate organization

One source patch and its focused regression belong together:

1. restore value-aware no-operation selection;
2. prove byte identity and active-operation routing.

## Current disposition

`ACTIVE` — one clean exact-branch test run and current overlap refresh remain.

## Next human decision

No human decision is required yet. After the remaining technical gates, the repository owner chooses whether to authorize creating the controlled fork and contacting upstream.

## Authority

Internal reads, commits, tests, packet drafting, and #397 checkpoints are authorized. External contact remains unauthorized, and none occurred.
