# Unit 17 — mmdebstrap deterministic directory mtimes and archive-boundary authority

State: `HOLD`  
Priority-zero issue: #397, unit 17  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-17-directory-mtime-authority`  
External contact authorized: `false`

## TL;DR

Root and chrootless tar output diverged on 123 directory mtimes while member identity, type, mode, ownership, size, and regular-file content matched. The retained evidence selects real-directory-only normalization over full timestamp normalization and comparison-only masking. Descriptor-based mutation prevents pathname redirection, while the authority matrix proves that an opened inode can leave the temporary root before mutation.

This unit remains `HOLD` on one discriminator: repeated disposable root and chrootless executions must show whether any live mmdebstrap-owned process can still access or rename the temporary root after `setup()` and immediately before GNU tar. This pass added and locally tested an evidence-only `/proc` probe for that execution.

## Accomplished behavior

The proposed product result makes direct tar output from root and chrootless mode byte-identical under an explicit `SOURCE_DATE_EPOCH` by converging real directory mtimes while preserving older regular-file mtimes, links, xattrs, ACLs, file capabilities, sparse source allocation, foreign-device descendants, and cleanup behavior.

The operation-authority premise remains unsettled. No product implementation is selected for upstream submission yet.

## Why care

The current `tests/chrootless` contract compares four root/chrootless tar pairs byte-for-byte. Full timestamp normalization destroys intentionally older package-file mtimes. Path-based directory mutation admits replacement and redirection races. Handle-based mutation keeps object identity but can timestamp an inode after it leaves the operation tree.

## Scope

### Included

- direct `tar` output with explicit `SOURCE_DATE_EPOCH`;
- root and chrootless mode convergence;
- directory-only timestamp policy;
- symlink, hard-link, device, xattr, ACL, capability, sparse-source, cleanup, and rerun controls already retained by the carrier chain;
- archive-boundary process ownership and quiescence evidence;
- exact authority choice between operation-owned opened inodes and a no-tree-mutation archive implementation.

### Excluded

- squashfs, ext2, ext4, directory, and null output;
- non-Linux descriptor and `/proc` mechanisms;
- upstream contact or submission;
- a full sid package matrix before the authority discriminator;
- broad package-process lifecycle repair unless the process probe finds a live actor at the archive boundary.

### Split boundary

The timestamp policy and authority decision belong together because the selected pre-tar mutation is acceptable only under an explicit operation-ownership premise. General descendant shutdown bugs, if observed, become a separate process-lifecycle unit with this packet retaining the discovery receipt.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `NEEDS CURRENT UPSTREAM PIN` |
| Upstream base commit | `NEEDS CURRENT UPSTREAM PIN`; retained imported source is mmdebstrap 1.5.7 |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | current Linux Fieldwork carrier `candidate/chrootless-directory-mtime-normalization-v3` |
| Candidate head | live GitHub ref `74c996394819c3a717d55193d84336c2e06b3b7c`; PR body still names earlier generation `e700839034a3b1ce3f3ddbfed5cf6d43a4c6987c` |
| Descriptor candidate | PR #389 `0319755b71ec594f2019cf40cd3cf9ee68ad7d60` |
| Authority matrix | PR #394 `cffc0ce00f57050539a0e11f11e609d13e9ca604` |
| Linux Fieldwork branch | `upstream/unit-17-directory-mtime-authority` |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | `upstream/mmdebstrap/mmdebstrap`, version 1.5.7, blob `41aa46f989a2660cebdb0138e0847cde25b269a3` on the unit base |
| Patch or series path | current candidates remain in PR #389 and PR #395; this packet adds an evidence probe only |
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
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- run 999 reached `(242/284) chrootless` after 154 completed package tests;
- the real package delta contained 123 paths, all directories, with timestamp-only differences;
- current clamp behavior preserves the divergence;
- full normalization converges archives and destroys an intentionally older regular-file mtime;
- real-directory-only normalization converges the focused archives while preserving the package-file mtime;
- symlink, hard-link, foreign-device, user-xattr, sparse-source, real ACL, file-capability, cleanup, and immediate-rerun boundaries have retained controls;
- descriptor mutation prevents old-path replacement from redirecting the timestamp write;
- current-membership checking rejects an inode already outside the root and retains a final check-to-mutation race;
- source order is `setup($options)`, hook-channel close, then pathname-based GNU tar;
- the packet process probe detects live descendants with root references, separates zombies, reports group/session/cgroup signals, excludes itself, and writes atomic JSON.

### Not yet demonstrated

- repeated real root and chrootless boundary snapshots;
- absence or presence of live owned actors at both archive phases;
- a selected authority policy based on those snapshots;
- exact current upstream base and overlap refresh;
- focused real sid `chrootless` candidate execution on a selected implementation;
- clean rerun of that real package case;
- complete upstream-native review and formatting gates.

### Compatibility boundary

The current candidate surface is Linux, root/chrootless, direct tar, explicit `SOURCE_DATE_EPOCH`, and non-dry-run operation. Other modes and formats retain current behavior. The process probe is evidence-only and requires Linux `/proc` visibility sufficient to inspect the worker and relevant processes.

## Candidate organization

No upstream series is selected. The internal review order is:

1. process-quiescence evidence at the two exact archive phases;
2. authority decision recorded in `DECISIONS.md`;
3. one selected product implementation, likely either bounded pre-tar directory normalization under an explicit quiescent-tree premise or a separately proven archive-header implementation;
4. focused real sid root/chrootless regression and immediate rerun;
5. current upstream refresh and submission draft completion.

## Current disposition

`HOLD` — blocker: operation authority after a discovered directory leaves the temporary root. Discriminator: repeated root/chrootless process snapshots immediately after `setup()` and immediately before tar, with exact live/zombie ancestry, group/session/cgroup identity, and temporary-root references.

## Next human decision

No send decision is ready. After the runtime receipts exist, the repository owner chooses whether the observed process boundary supports operation-owned opened inodes through archive completion or requires the no-tree-mutation route.

## Authority

Internal repository reads, branch commits, packet work, synthetic tests, and disposable process evidence are authorized. External contact remains unauthorized. No upstream issue, merge request, email, review, package upload, or release action occurred.
