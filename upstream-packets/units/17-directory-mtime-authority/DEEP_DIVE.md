# Deep dive

## Question and observed failure

The real current-sid carrier completed 154 package tests and first failed at `(242/284) chrootless`. Root and chrootless archives differed on the same 123 paths; every path was a directory. Member names, types, modes, uid/gid, sizes, and ordinary file content matched. Root-mode directories were at the selected epoch, while chrootless retained older package directory mtimes.

The bounded product question is settled at the policy level: direct root/chrootless tar output under explicit `SOURCE_DATE_EPOCH` is expected to converge byte-for-byte without flattening unrelated package-file timestamps or directory access time. The remaining primary question is who retains mutation authority over a directory inode during final archive preparation.

## Source mechanism

The imported mmdebstrap 1.5.7 source computes the archive mtime from `SOURCE_DATE_EPOCH` and invokes GNU tar with `--mtime=@EPOCH --clamp-mtime`. Clamp changes only members newer than the epoch. Root-mode construction tends to create or touch directories after the epoch, while chrootless package extraction can preserve older package directory mtimes.

The final worker calls `setup($options)`, sends and closes the hook channel, then creates the archive. Root and chrootless tar creation uses pathname traversal with `-C $options->{root}`. This source order establishes a completed setup phase. It does not prove that every owned helper has exited or lost access to the temporary root.

## Reproduction narrative

PR #383 built otherwise equivalent trees containing nested directories with old/new mtimes and one deliberately old regular file. Current clamp left directory-only divergence. Full normalization converged the archives and erased the package-file mtime. Real-directory-only normalization converged the archives while preserving that file mtime. Comparison-only normalization explained the diff while leaving product bytes unequal.

Run 999 is the real-package anchor. Focused carriers expanded the boundary across symlinks, hard links, device pruning, xattrs, sparse source files, ACLs, file capabilities, cleanup, and rerun.

## Approach history

### Approach A — full timestamp normalization

- mechanism: remove clamp and assign the selected epoch to every archive member;
- result: byte convergence;
- cost: destroys intentionally older regular-file mtimes;
- disposition: rejected as overbroad.

### Approach B — comparison-only directory normalization

- mechanism: normalize directory mtimes only in the comparison view;
- result: normalized manifests match while product archives remain different;
- cost: weakens the explicit byte-identity regression and reproducibility contract;
- disposition: fallback only after an explicit contract change; currently rejected.

### Approach C — path-based pre-tar directory mutation

- mechanism: enumerate real same-device directories and apply timestamp changes by pathname;
- result: focused convergence and broad metadata controls;
- costs:
  - a replacement between identity check and pathname mutation can redirect the write or change a regular file;
  - PR #395 live head passes the epoch as both `utime` arguments and therefore overwrites directory access time;
- disposition: PR #384 rejected for replacement authority; PR #395 remains construction history and is also rejected as an access-time-preserving candidate.

### Approach D — descriptor-retained pre-tar mutation

- mechanism: open directories through pinned parent descriptors with no-follow flags, retain device/mount/inode identity, and timestamp the opened handle;
- result: old-path replacement cannot redirect the write; focused controls and repository gates passed on PR #389;
- cost: an opened inode can be renamed outside the temporary root and still receive the timestamp;
- disposition: mechanically viable, policy hold.

### Approach E — best-effort current-membership check

- mechanism: walk `..` through descriptors immediately before mutation and compare identities to the pinned root;
- result: rejects an inode already outside and accepts in-root rename or move-back;
- cost: an inode can move out after the final check and before handle-based mutation;
- disposition: records a narrower policy without an atomic guarantee; no implementation selected.

### Approach F — archive-header-only normalization

- mechanism: leave the live tree untouched and rewrite directory headers in the archive stream;
- result: avoids live-tree membership authority in principle;
- cost: re-enters GNU PAX, xattr, link, and sparse transformation risks already demonstrated by earlier tar-filter work;
- disposition: retained alternative requiring a complete archive compatibility matrix.

### Approach G — explicit quiescent-tree premise

- mechanism: prove that no live owned actor can mutate the completed root after setup and before tar, then define discovered directories as operation-owned through archive completion;
- work added: packet-local process snapshot probe and four passing focused controls;
- result: probe mechanics established; real root/chrootless receipts absent;
- disposition: next authority discriminator.

## PR #395 complete live-head review

All nine changed paths at head `74c996394819c3a717d55193d84336c2e06b3b7c` were reviewed. Full notes are in [`LIVE_HEAD_REVIEW.md`](LIVE_HEAD_REVIEW.md).

### Directory access-time regression

The product patch uses:

```perl
1 == utime($mtime, $mtime, $File::Find::name)
```

Perl interprets the first argument as access time and the second as modification time. The helper changes both. Earlier PR #384 review had already narrowed this behavior by preserving the observed atime. PR #395 reintroduced the broader mutation.

The candidate test requires the exact two-epoch call and lacks a directory-atime reversing control. The real metadata probe also lacks an atime assertion. Green synthetic results therefore do not establish the stated access-time boundary.

### Exact-head execution status

- Linux Fieldwork CI `30659899178` / 1099: success;
- dedicated run `30659899105` / 25, job `91253360438`: failure;
- generated merge: `a7fa7fe838e499ee52912c7be276cc89cfad4dec`;
- patch-context, syntax, and synthetic candidate step: passed;
- sid whole-source formatting: failed at char 1676, line 42;
- real product-helper metadata step: skipped;
- receipt artifact: absent.

The formatting failure is an evidence-harness ownership issue. It does not clear or disprove product behavior. It also means the live helper never executed the dedicated real metadata matrix.

## Current technical selection

Directory-only normalization remains the selected policy class. The implementation remains unselected between descriptor-retained pre-tar mutation under an explicit quiescent-tree premise and a fully controlled archive-header implementation.

Every selected implementation must preserve observed directory access time. PR #395 live head fails that requirement before the authority question is considered.

## Why the changes belong together

Timestamp policy, access-time preservation, and operation authority govern the same source interval and mutation. Sending a directory-only patch without these premises would hide central review choices. A process-lifecycle defect discovered by the runtime probe would split into its own correction because descendant shutdown owns different code and failure behavior.

## Compatibility analysis

### Archive bytes and metadata

- direct root/chrootless tar bytes are intended to converge;
- older regular-file mtimes remain observable;
- directory access time remains unchanged;
- symlink objects and targets remain unchanged;
- hard-link identity remains intact;
- xattrs, ACLs, file capabilities, and sparse source allocation have retained controls;
- foreign-device descendants remain outside the operation;
- directory output and converter formats stay outside the current candidate.

### Process and filesystem authority

- pathname mutation admits replacement redirection;
- descriptor mutation retains object identity across rename;
- identity does not prove current tree membership;
- current-membership checking retains a final move-out race;
- final GNU tar traversal itself depends on a stable completed pathname tree;
- runtime snapshots must distinguish live actors, zombies, group/session/cgroup affiliation, and direct temporary-root references.

### Platform boundary

The descriptor and process-probe mechanisms are Linux-specific. Non-Linux behavior remains unchanged and requires a separate design if the selected upstream correction depends on these mechanisms.

## Negative controls and losing mutations

The retained matrix loses under current clamp and full normalization for different reasons. Symlink and replacement controls fail unsafe path classifiers. Device controls fail recursive walks that cross the archive device. The authority matrix visibly timestamps an inode moved outside after a successful membership check. The packet probe controls include a live descendant with ancestry and root references, a zombie child, a process name containing spaces, and a CLI run that excludes the probe PID and leaves no temporary JSON file.

A missing negative control remains explicit: record directory atime before candidate normalization and require exact preservation afterward. That control would fail PR #395 live head.

## Current and historical review

The project README documents bit-for-bit reproducible output under `SOURCE_DATE_EPOCH`. The chrootless regression uses byte comparison. Earlier project history also treated timestamp reconciliation as part of reproducibility. These facts support a product correction and place comparison-only masking behind an explicit policy change.

PR #395 contains an identity mismatch: the body names `e700839...`, while the live head is `74c996394819c3a717d55193d84336c2e06b3b7c`. The complete live-head review is now retained in this packet.

## Remaining questions and exact discriminators

1. **Are live owned actors present after setup or immediately before tar?** Instrument repeated disposable root and chrootless executions with the packet probe at both phases; retain JSON receipts.
2. **Can any observed live actor access the temporary root?** Require ancestry plus `/proc` cwd/root/exe/fd evidence, and review process group/session/cgroup signals separately.
3. **Does the probe alter the answer?** The probe PID is labeled and excluded; add an adjacent run without the probe and compare package result and process cleanup.
4. **Which authority policy wins?** If repeated runs are quiescent, review the operation-owned-inode premise against final pathname tar. If a live actor remains, identify and repair its lifecycle before tree mutation. If quiescence cannot be established, build the archive-header compatibility matrix.
5. **Which candidate preserves directory atime?** Add a losing atime control, repair the helper, and rerun the real metadata matrix twice.
6. **What is current upstream?** Refresh the upstream base and active overlap after the authority route is selected.

## Evidence boundary

The packet probe controls executed on Linux 6.12.13 x86_64 with Python 3.13.5. This work did not modify or execute mmdebstrap locally, run root/chrootless package creation, mount filesystems, contact upstream, or select a product patch. PR #395 execution facts come from its exact GitHub workflow records.

## Reopen triggers

- a runtime receipt shows a live actor or root reference at either archive phase;
- current upstream changed the setup/tar ordering or process ownership;
- PR #389, #394, or #395 advances to a new head;
- a candidate demonstrates directory-atime preservation under real metadata execution;
- an archive-header implementation demonstrates complete PAX/xattr/link/sparse extraction compatibility;
- explicit upstream guidance changes the reproducibility or directory-mtime contract.
