# Unit 17 — mmdebstrap deterministic directory mtimes and archive-boundary authority

State: `HOLD`  
Priority-zero issue: #397, unit 17  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-17-directory-mtime-authority`  
External contact authorized: `false`

## TL;DR

Root and chrootless tar output diverged on 123 directory mtimes while member identity, type, mode, ownership, size, and regular-file content matched. The retained evidence selects real-directory-only normalization over full timestamp normalization and comparison-only masking. Descriptor-based mutation prevents pathname redirection, while the authority matrix proves that an opened inode can leave the temporary root before mutation.

The unit remains `HOLD` on the archive-boundary ownership discriminator: repeated disposable root and chrootless executions must show whether any live mmdebstrap-owned process can still access or rename the temporary root after `setup()` and immediately before GNU tar. The packet contains a tested evidence-only `/proc` probe for that execution.

Complete review of PR #395 live head `74c996394819c3a717d55193d84336c2e06b3b7c` found a separate candidate defect: `utime($mtime, $mtime, path)` overwrites directory access time. Its dedicated run `30659899105` also stopped at whole-source sid formatting before the real product-helper metadata matrix. PR #395 therefore remains construction history, not a promotable product candidate.

## Desired accomplished behavior

The proposed product result makes direct tar output from root and chrootless mode byte-identical under an explicit `SOURCE_DATE_EPOCH` by converging real directory mtimes while preserving directory access time, older regular-file mtimes, links, xattrs, ACLs, file capabilities, sparse source allocation, foreign-device descendants, and cleanup behavior.

The operation-authority premise remains unsettled. No product implementation is selected for upstream submission.

## Why care

The current `tests/chrootless` contract compares four root/chrootless tar pairs byte-for-byte. Full timestamp normalization destroys intentionally older package-file mtimes. Path-based directory mutation admits replacement and redirection races. Handle-based mutation keeps object identity but can timestamp an inode after it leaves the operation tree.

## Scope

### Included

- direct `tar` output with explicit `SOURCE_DATE_EPOCH`;
- root and chrootless mode convergence;
- directory-only timestamp policy with access-time preservation;
- symlink, hard-link, device, xattr, ACL, capability, sparse-source, cleanup, and rerun controls retained by the carrier chain;
- archive-boundary process ownership and quiescence evidence;
- exact authority choice between operation-owned opened inodes and a no-tree-mutation archive implementation.

### Excluded

- squashfs, ext2, ext4, directory, and null output;
- non-Linux descriptor and `/proc` mechanisms;
- upstream contact or submission;
- a full sid package matrix before the authority discriminator;
- broad package-process lifecycle repair unless the process probe finds a live actor at the archive boundary.

### Split boundary

Timestamp policy and authority belong together because the selected pre-tar mutation is acceptable only under an explicit operation-ownership premise. General descendant shutdown bugs, if observed, become a separate process-lifecycle unit with this packet retaining the discovery receipt.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `NEEDS CURRENT UPSTREAM PIN` |
| Upstream base commit | `NEEDS CURRENT UPSTREAM PIN`; retained imported source is mmdebstrap 1.5.7 |
| Controlled fork | `NEEDS FORK` |
| Current pathname carrier | PR #395 branch `candidate/chrootless-directory-mtime-normalization-v3` |
| Current pathname head | live ref `74c996394819c3a717d55193d84336c2e06b3b7c`; PR body names earlier generation `e700839034a3b1ce3f3ddbfed5cf6d43a4c6987c` |
| Descriptor candidate | PR #389 `0319755b71ec594f2019cf40cd3cf9ee68ad7d60` |
| Authority matrix | PR #394 `cffc0ce00f57050539a0e11f11e609d13e9ca604` |
| Linux Fieldwork branch | `upstream/unit-17-directory-mtime-authority` |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | `upstream/mmdebstrap/mmdebstrap`, version 1.5.7, blob `41aa46f989a2660cebdb0138e0847cde25b269a3` on the unit base |
| Patch or series path | no selected packet product patch; current candidates remain in PR #389 and PR #395 |
| Proposed destination | mmdebstrap GitLab project after policy selection and current-source refresh |
| Delivery method | `GitLab fork and merge request`; controlled fork is absent |

## Canonical links

- Priority-zero unit: #397 unit 17
- Owning policy issue: #380
- Authority issue: #392
- Evidence matrix: PR #383
- Symlink identity repair: PR #386
- Device-boundary repair: PR #388
- xattr and sparse-source repair: PR #390
- real mount, ACL, capability, cleanup, and rerun gate: PR #391
- descriptor candidate: PR #389
- authority matrix: PR #394
- current pathname product carrier: PR #395; PR #393 is superseded construction history
- complete live-head review: [`LIVE_HEAD_REVIEW.md`](LIVE_HEAD_REVIEW.md)
- packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- tests and receipts: [`TESTS.md`](TESTS.md)
- decisions: [`DECISIONS.md`](DECISIONS.md)
- current handoff: [`HANDOFF.md`](HANDOFF.md)
- upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- run 999 reached `(242/284) chrootless` after 154 completed package tests;
- the real package delta contained 123 paths, all directories, with timestamp-only differences;
- current clamp behavior preserves the divergence;
- full normalization converges archives and destroys an intentionally older regular-file mtime;
- real-directory-only normalization converges focused archives while preserving the package-file mtime;
- symlink, hard-link, foreign-device, user-xattr, sparse-source, real ACL, file-capability, cleanup, and immediate-rerun boundaries have retained controls;
- descriptor mutation prevents old-path replacement from redirecting the timestamp write;
- current-membership checking rejects an inode already outside the root and retains a final check-to-mutation race;
- source order is `setup($options)`, hook-channel close, then pathname-based GNU tar;
- the packet process probe detects live descendants with root references, separates zombies, reports group/session/cgroup signals, excludes itself, and writes atomic JSON;
- complete PR #395 live-head review covered all nine changed paths;
- PR #395 overwrites directory atime and lacks an atime reversing control;
- dedicated run `30659899105` failed at sid whole-source formatting, skipped the real product matrix, and retained no receipt artifact;
- Linux Fieldwork CI `30659899178` / 1099 succeeded on the same head.

### Not yet demonstrated

- repeated real root and chrootless boundary snapshots;
- absence or presence of live owned actors at both archive phases;
- a selected authority policy based on those snapshots;
- a product candidate preserving directory atime under the selected authority model;
- exact current upstream base and overlap refresh;
- focused real sid `chrootless` candidate execution on a selected implementation;
- clean rerun of that real package case;
- complete upstream-native review and formatting gates.

### Compatibility boundary

The intended candidate surface is Linux, root/chrootless, direct tar, explicit `SOURCE_DATE_EPOCH`, and non-dry-run operation. Other modes and formats retain current behavior. The process probe is evidence-only and requires Linux `/proc` visibility sufficient to inspect the worker and relevant processes.

## Candidate organization

No upstream series is selected. The internal review order is:

1. process-quiescence evidence at the two exact archive phases;
2. authority decision recorded in `DECISIONS.md`;
3. an access-time reversing control and a candidate that changes directory mtime only;
4. one selected product implementation under the chosen authority model;
5. focused real sid root/chrootless regression and immediate rerun;
6. current upstream refresh and submission draft completion.

## Current disposition

`HOLD` — primary blocker: operation authority after a discovered directory leaves the temporary root. Discriminator: repeated root/chrootless process snapshots immediately after setup and immediately before tar, with exact live/zombie ancestry, group/session/cgroup identity, and temporary-root references.

PR #395 has additional local blockers: directory-atime overwrite, path check-to-mutation identity, and a dedicated run that never reached the real product matrix.

## Next human decision

No send decision is ready. After runtime receipts exist, the repository owner chooses whether the observed process boundary supports operation-owned opened inodes through archive completion or requires the no-tree-mutation route.

## Authority

Internal repository reads, branch commits, packet work, synthetic tests, disposable process evidence, and Linux Fieldwork issue checkpoints are authorized. External contact remains unauthorized. No upstream issue, merge request, email, review, package upload, or release action occurred.
