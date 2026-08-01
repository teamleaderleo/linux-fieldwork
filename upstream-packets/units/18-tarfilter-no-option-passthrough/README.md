# Unit 18 — mmdebstrap tarfilter byte-preserving no-option passthrough

State: `READY FOR AUTHORIZATION`  
Priority-zero issue: #397, unit 18  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-18-tarfilter-no-option-passthrough`  
External contact authorized: `false`

## TL;DR

Current mmdebstrap `main` still routes a no-option `tarfilter` invocation through Python tar parsing because `argparse` always creates `args.strip_components`. The retained correction applies to the exact current source with `--fuzz=0`, copies no-operation input byte-for-byte, and tests every modifying option category. The exact committed regression passed twice, the complete branch diff remains bounded, and the current visible upstream issue/pull-request search found no equivalent work.

The technical packet is complete. Human authorization is required before creating or using a public controlled fork or contacting upstream.

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
| Controlled fork | `NEEDS FORK — authorization required` |
| Candidate source branch | `NEEDS FORK — authorization required` |
| Exact candidate patch blob | `9f856f389c7a991813dbe9d959edaf94c1155dec` |
| Patched `tarfilter` SHA-256 | `8fec7cf1b1c6e314714e9a0347a7485f41d176e5cbc2769904f10af84a07e4ac` |
| Candidate source/test head | `748f95cf0470d2c9ba96b8432c3cac7d2267aaeb` plus packet/receipt commits |
| Linux Fieldwork branch | `upstream/unit-18-tarfilter-no-option-passthrough` |
| Linux Fieldwork head | branch `HEAD`; exact final SHA is recorded in the #397 checkpoint |
| Imported/local source identity | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Linux Fieldwork patch blob | `44428ecf8d83a6edf2fca4f4da030129daacb13f` |
| Committed regression blob | `0b8a0e092a6dd2bf7481e077e7c7ec0f27b461bb` |
| Patch path | `patches/0001-tarfilter-restore-no-option-passthrough.patch` |
| Proposed destination | canonical mmdebstrap repository |
| Delivery method | `Gitea/Forgejo fork and pull request`; controlled fork required |

## Canonical links

- Priority-zero unit: #397 unit 18
- Owning Linux Fieldwork issue: #29
- Canonical Linux Fieldwork PR: #46
- Duplicate carrier: #27
- Composition carrier: #33
- Related active-sparse carrier: #23
- Investigation: `investigations/tarfilter-no-option-passthrough/README.md`
- Reusable note: `notes/filesystems/no-op-archive-filters-must-preserve-bytes.md`
- Exact focused receipt: `artifacts/2026-08-01-focused-regression.json`
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- canonical upstream remains at repository head `77ec9be5417ee44c96343d2347145585da1b1f94` and displays the same unreachable guard in `tarfilter` commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0`;
- the old retained patch applied with fuzz 2, while the refreshed patch applies with `patch --fuzz=0` and compiles;
- exact source, patch, regression, and upstream-shaped patch blob identities were recomputed before execution;
- the committed focused suite passed 3/3 in `10.181s`, then passed 3/3 on a clean rerun in `8.617s`;
- the baseline rewrites gzip input;
- the candidate preserves plain, gzip, bzip2, xz, GNU sparse, strip-zero, and ID-shift-zero inputs byte-for-byte;
- each active operation category produces its expected semantic result;
- the upstream-shaped patch applies with zero fuzz and produces patched-source SHA-256 `8fec7cf1…`;
- the complete branch diff contains only patch packaging, focused tests, and the unit packet;
- the six currently visible open upstream issues are unrelated, and targeted issue/pull-request searches found no no-option passthrough equivalent.

### Authorization-dependent work

- create or identify the controlled public fork;
- apply the retained patch as one fork-native commit;
- run the same focused commands in that checkout;
- submit the prepared pull request only after explicit authorization.

### Compatibility boundary

Explicit numeric zero follows the existing implementation's truthiness behavior. A caller-supplied transform remains an active operation even when its expression happens to leave a particular member unchanged.

## Candidate organization

One source patch and its focused regression belong together:

1. restore value-aware no-operation selection;
2. prove byte identity and active-operation routing.

## Current disposition

`READY FOR AUTHORIZATION` — the technical scavenger hunt is complete. The remaining decision is whether to authorize controlled-fork creation and upstream submission.

## Next human decision

Authorize or decline creation/use of a controlled mmdebstrap fork and submission of the prepared pull request. External contact remains separately unauthorized until that decision is explicit.

## Authority

Internal reads, commits, tests, packet drafting, and #397 checkpoints are authorized. External contact remains unauthorized, and none occurred.
