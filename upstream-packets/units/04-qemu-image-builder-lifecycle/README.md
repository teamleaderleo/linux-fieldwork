# Unit 04 — mmdebstrap QEMU image publication and signal lifecycle

State: `ACTIVE`  
Priority-zero issue: #397, unit 4  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-04-qemu-image-builder-lifecycle`  
Internal review carrier: draft PR #400  
External contact authorized: `false`

## TL;DR

The canonical Linux Fieldwork composition from issue #193 and merged PR #195 is packaged as one upstream-root patch. The patch builds the QEMU image under a private sibling directory, publishes once through rename, preserves prior output on failure and pre-publication signals, terminates on HUP/INT/QUIT/TERM, and cleans owned temporary state once.

Current upstream `main` is `77ec9be5417ee44c96343d2347145585da1b1f94`. The builder's latest upstream change is `ff91e582194f99c72c460815d2fc32018aad9e97`, and the Linux Fieldwork import has Git blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3`, matching the reviewed public mirror copy. The packet repairs the retained integration patch's sliced-source hunk coordinates and now uses upstream-root paths plus complete-file coordinates. A repository test requires zero fuzz, zero offsets, complete `sh -n`, exact source-routing assertions, and the repaired reduced lifecycle model.

Draft PR #400 exists only inside Linux Fieldwork to run CI and review. Upstream contact remains unauthorized and none occurred.

## Accomplished behavior

- Image construction uses a private sibling directory on the destination filesystem.
- `mke2fs`, `truncate`, `sfdisk`, and `dd` mutate only the private image.
- One final `mv --no-target-directory` publishes the completed image.
- Existing output survives ordinary failure and pre-publication HUP, INT, QUIT, or TERM.
- Signal handlers terminate with statuses 129, 130, 131, and 143.
- Cleanup runs once and preserves the primary command or signal result.
- A cleanup failure becomes the result after an otherwise successful exit.
- A published image survives a later signal.
- Immediate reruns use the same destination successfully.
- Trailing-slash destinations and parents resolving to `/` are rejected before private state is created.

## Why care

The baseline writes directly to the caller-selected final pathname and uses cleanup-only signal traps. A late failure can expose a partial image or damage an existing valid image. A wrapper-only signal can clean temporary files, resume later work, and report a misleading result.

## Scope

### Included

- Private same-filesystem image construction.
- Atomic final-name publication by one rename.
- HUP/INT/QUIT/TERM termination semantics.
- Once-only cleanup and explicit result precedence.
- Existing-output preservation, post-publication signal behavior, reruns, and path rejection.

### Excluded

- Signal forwarding or escalation to foreground children.
- File or directory `fsync` durability.
- Concurrent-publisher locking.
- Completed-image content validation.
- Preservation of metadata from a replaced inode.
- Recursive deletion of unexpected post-publication residue.
- Full multi-gigabyte image construction in this packet pass.

### Split boundary

Focused PR #172 remains signal-mechanism evidence and PR #192 remains publication-mechanism evidence. Their cleanup/trap edits overlap. Merged PR #195 is the single composition and therefore the only source candidate for this upstream unit.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Builder's latest upstream commit | `ff91e582194f99c72c460815d2fc32018aad9e97` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate identity | patch SHA-256 `0ef272d4613e1744957630c5de7da081e248601f934aa98efb43ea22b143c4dd` |
| Linux Fieldwork branch | `upstream/unit-04-qemu-image-builder-lifecycle` |
| Linux Fieldwork internal PR | `#400` |
| Imported/local source identity | Git blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3`; identical to reviewed public mirror file |
| Patch or series path | `patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch` |
| Proposed destination | mmdebstrap Forgejo pull request |
| Delivery method | One pull request after explicit authorization |

## Canonical links

- Priority-zero unit: #397 unit 4
- Owning Linux Fieldwork issue: #193
- Canonical Linux Fieldwork composition: #195, merge `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145`
- Predecessor issues and PRs: #170 / #172 and #191 / #192
- Internal packet review: draft PR #400
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- Canonical component-carrier composition and supersession are resolved.
- Current imported source and the reviewed public mirror file have identical Git blob identity.
- The upstream-root patch uses complete-file hunk coordinates at source lines 318, 406, 465, 474, and 483.
- Historical exact-head CI on PR #195 passed the complete composed behavior and source syntax.
- The packet's reduced real `/bin/sh` model passes baseline/candidate TERM, failure, success, post-publication TERM, mode, private-state cleanup, and trailing-slash rejection.
- A repository-level test now applies the packet to the exact imported source with `--fuzz=0`, rejects offset/fuzz transcripts, runs `sh -n`, checks all image mutators, and requires exactly one publication rename.

### Remaining gates

- Linux Fieldwork draft PR #400 CI completion for the current packet head.
- Upstream-native `shellcheck` and `shfmt -d` on a checkout at the exact upstream base.
- A real `mmdebstrap-autopkgtest-build-qemu` image construction on current Debian tooling.
- Controlled fork branch and exact candidate commit.

### Compatibility boundary

Publication replaces the final pathname itself, including a symlink, through rename. A new inode follows producer/umask metadata and does not inherit the replaced inode's mode, ownership, ACLs, or xattrs. A parent resolving to `/` is deliberately refused by the composed contract.

## Candidate organization

One patch belongs in one pull request because cleanup ownership, signal termination, private construction, and publication touch the same lifecycle and must be reviewed together.

1. `0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch`

## Current disposition

`ACTIVE` — current packet CI, upstream-native static checks, and one real builder gate remain.

## Next human decision

No send decision is required yet. Complete the named technical gates, review the exact upstream diff, then decide whether to authorize creation of the public pull request.

## Authority

Internal repository work, rebasing, testing, review, draft preparation, and draft PR #400 are authorized by #397. External issues, pull requests, emails, comments, and reviews remain unauthorized. None occurred.
