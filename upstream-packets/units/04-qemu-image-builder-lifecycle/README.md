# Unit 04 — mmdebstrap QEMU image publication and signal lifecycle

State: `ACTIVE`  
Priority-zero issue: #397, unit 4  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-04-qemu-image-builder-lifecycle`  
External contact authorized: `false`

## TL;DR

The canonical Linux Fieldwork composition from issue #193 and merged PR #195 has been extracted into one upstream-root patch. The patch builds the QEMU image under a private sibling directory, publishes once through rename, preserves prior output on failure and pre-publication signals, terminates on HUP/INT/QUIT/TERM, and cleans owned temporary state once.

Current upstream still carries the byte-identical imported builder source. During extraction, the retained integration patch was found to use sliced-tail hunk coordinates (`@@ -1...`) and to rely on a large application offset. This packet regenerates the hunk coordinates against the full 487-line upstream file and adds an exact-source no-offset/no-fuzz gate. Local reduced lifecycle tests pass; the exact repository-source application, `sh -n`, `shellcheck`, and `shfmt` gates remain to execute on the branch or an upstream checkout.

## Accomplished behavior

- Image construction uses a private sibling directory on the destination filesystem.
- `mke2fs`, `truncate`, `sfdisk`, and `dd` mutate only the private image.
- One final `mv --no-target-directory` publishes the completed image.
- Existing output survives ordinary failure and pre-publication HUP, INT, QUIT, or TERM.
- Signal handlers terminate with statuses 129, 130, 131, and 143.
- Cleanup runs once and preserves the primary command or signal status.
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
| Candidate head | `NEEDS EXACT APPLY COMMIT` |
| Linux Fieldwork branch | `upstream/unit-04-qemu-image-builder-lifecycle` |
| Linux Fieldwork starting head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | Git blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3`; identical to public mirror file |
| Patch or series path | `patches/0001-mmdebstrap-autopkgtest-build-qemu-publish-atomically.patch` |
| Proposed destination | mmdebstrap Forgejo pull request |
| Delivery method | One pull request after explicit authorization |

## Canonical links

- Priority-zero unit: #397 unit 4
- Owning Linux Fieldwork issue: #193
- Canonical Linux Fieldwork PR or composition: #195, merge `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145`
- Predecessor issues and PRs: #170 / #172 and #191 / #192
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
- Current imported source and public mirror file have identical Git blob identity.
- Upstream-root patch paths and full-file hunk coordinates are packaged.
- Seven local packet tests ran: six passed and the exact-source checkout test skipped because the source tree was unavailable in the container.
- Reduced real `/bin/sh` cases cover failure, success, HUP/INT/TERM, post-publication TERM, cleanup precedence, rerun, mode, and trailing-slash rejection.

### Not yet demonstrated

- Patch application with zero fuzz and zero offsets against an actual checkout at the exact upstream base.
- Complete candidate `sh -n`, upstream `shellcheck`, and upstream `shfmt -d` on that checkout.
- Upstream-native builder execution or full image construction.
- Controlled fork branch and exact candidate commit.

### Compatibility boundary

Publication replaces the final pathname itself, including a symlink, through rename. A new inode follows producer/umask metadata and does not inherit the replaced inode's mode, ownership, ACLs, or xattrs. A parent resolving to `/` is deliberately refused by the composed contract.

## Candidate organization

One patch belongs in one pull request because cleanup ownership, signal termination, private construction, and publication touch the same lifecycle and must be reviewed together.

1. `0001-mmdebstrap-autopkgtest-build-qemu-publish-atomically.patch`

## Current disposition

`ACTIVE` — the exact current-upstream application and upstream-native static gates remain.

## Next human decision

No decision is required yet. Execute the exact-source gate and static checks; after a green complete-diff review, decide whether to authorize creation of the public pull request.

## Authority

Internal repository work, rebasing, testing, review, and draft preparation are authorized by #397. External issues, pull requests, emails, comments, and reviews remain unauthorized. None occurred.
