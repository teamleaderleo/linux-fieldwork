# Unit 07 — mmdebstrap file-mirror setup and cleanup confinement

State: `ACTIVE`  
Priority-zero issue: #397, unit 07  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-07-file-mirror-confinement`  
External contact authorized: `false`

## TL;DR

The merged Linux Fieldwork carrier proves one setup-plus-cleanup repair for `hooks/file-mirror-automount`: resolve sources and destinations, require targets to remain strict children of the generated root, preserve the configured `file:` URI path for terminal source symlinks, reject every parent component, store constrained NUL-delimited cleanup entries, and preflight the complete marker before destructive actions.

This pass applied the composed packet patch to the controlled GitHub fork `teamleaderleo/mmdebstrap`. The candidate branch is `linux-fieldwork/unit-07-file-mirror-confinement` at `8b8dce6910badeda1e72e28f471fa220a22eea7d`, based on `master@574048f2a720057b75e56622003932f344dc700a`. The complete fork diff contains only the setup and cleanup hooks. The exact candidate bytes passed shell syntax and a disposable 10-check fake-command matrix. No pull request or upstream contact was created.

## Accomplished behavior

Setup canonicalizes the generated root and existing source, refuses `/` as a generated root, keeps the configured URI spelling as the in-root destination when required, resolves destination symlinks, requires a strict descendant, and records one canonical root-relative marker entry only after a successful action.

Cleanup treats the marker as untrusted input. It validates every entry before the first `umount` or `rm -r`, revalidates each entry immediately before acting, retains the marker when validation or an action fails, and removes it only after a complete successful action pass.

## Why care

The baseline constructs `mount`, hook-helper copy/upload, `umount`, and `rm -r` targets through textual path concatenation. Traversal components, a destination-parent symlink, a generated root resolving to `/`, or a corrupted marker can select a host path outside the generated root. Sequential cleanup can also remove valid early entries before discovering a later escape.

## Scope

### Included

- `hooks/file-mirror-automount/setup00.sh`;
- `hooks/file-mirror-automount/customize00.sh`;
- generated-root refusal;
- repository and included-package target confinement;
- terminal source-symlink URI compatibility;
- parent-component rejection;
- canonical relative NUL marker entries;
- complete cleanup preflight and per-action revalidation;
- disposable fake mount, unmount, copy, and removal evidence.

### Excluded

- package-test scheduling for `root-without-cap-sys-admin` (#153 / PR #158);
- local HTTP mirror readiness (#79 / PR #90);
- Debian package-test dependency and current-sid lanes tracked by #53;
- descriptor-relative pathname operations;
- private mount namespaces;
- privileged real-mount integration;
- real non-root hook-socket transfer.

### Split boundary

The adjacent carriers change package-test scheduling or service lifecycle. They share a test environment with this hook but modify different source owners and prove different claims. This unit changes only the file-mirror setup/cleanup contract.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Canonical upstream head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled test fork | `https://github.com/teamleaderleo/mmdebstrap` |
| Fork base branch | `master` |
| Fork base commit | `574048f2a720057b75e56622003932f344dc700a` |
| Candidate source branch | `linux-fieldwork/unit-07-file-mirror-confinement` |
| Candidate head | `8b8dce6910badeda1e72e28f471fa220a22eea7d` |
| Candidate setup Git blob | `80bf3f3ef4f5535ca802d91ac8bc6f3c2999a70c` |
| Candidate cleanup Git blob | `30ff2c56d83b5bedd91ec62e65f4c6a18bd4a6f6` |
| Candidate setup SHA-256 | `f750be95ada2a3e39c972653158092f907f153ff0ca07c2200a326bcc11920be` |
| Candidate cleanup SHA-256 | `867443a4fd2737f5275c11180f1f17d6f7bc92d487e476327834764c06a8afc7` |
| Linux Fieldwork branch | `upstream/unit-07-file-mirror-confinement` |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Baseline setup blob | `6ccbdaf2ba97c77c4e5223ac5280acd51a998424` |
| Baseline cleanup blob | `b6b9b46afdd9dad01df3abcb514475326162e42c` |
| Patch path | `patches/0001-file-mirror-automount-containment.patch` |
| Patch SHA-256 | `928533ff01be39ba66c5350f7951706fd7f017448449c2671bb95a271db75f25` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | upstream pull request after explicit authorization; current GitHub fork is a controlled test carrier |

## Canonical links

- Priority-zero unit: #397 unit 07
- Owning Linux Fieldwork issue: #164
- Canonical Linux Fieldwork PR: #179
- Controlled fork candidate: `teamleaderleo/mmdebstrap` branch `linux-fieldwork/unit-07-file-mirror-confinement`
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- canonical upstream and packaged-source identities were reconciled;
- fork baseline hook blobs equal the packet baseline exactly;
- the composed patch maps to a fork branch with only two changed paths;
- fork candidate head is two commits ahead and zero commits behind its base;
- both candidate scripts pass `/bin/sh -n`;
- candidate content hashes equal the packet receipts;
- a fresh disposable 10-check matrix passed traversal rejection, root refusal, ordinary repository mapping, terminal source-symlink reachability, parent-component rejection, local package confinement, root cleanup preflight/correction/rerun, fakechroot cleanup preflight/correction/rerun, and cleanup symlink-escape rejection;
- historical exact-head carrier CI run `30580904313` passed the broader five-file regression set at PR #179 head `6db473c5e3e462a93f583e7c33a76a93ed1102b8`.

### Not yet demonstrated

- hosted CI attached to fork candidate head `8b8dce6910badeda1e72e28f471fa220a22eea7d`;
- exact-current canonical Forgejo archive application at `77ec9be5417ee44c96343d2347145585da1b1f94`;
- final overlap search immediately before authorization;
- real bind mount/unmount and real non-root hook-helper transfer.

### Compatibility boundary

- harmless `.` and repeated separators normalize;
- every configured `..` component is rejected;
- terminal source symlinks remain usable by separating canonical host source from the APT-visible destination spelling;
- historical leading-slash cleanup markers are rejected during an active run;
- GNU `realpath` and GNU `xargs` behavior is required;
- pathname or marker replacement between validation and action remains possible for a sufficiently capable concurrent actor.

## Candidate organization

The controlled fork currently has two commits because GitHub contents writes were applied file by file:

1. `b18095f0a9916ad70872f6740ffae033fda9b034` — setup target confinement and URI-path behavior;
2. `8b8dce6910badeda1e72e28f471fa220a22eea7d` — cleanup marker preflight and action-time revalidation.

The public upstream packet remains one logical setup/cleanup unit. Commit organization can be squashed or retained after review.

## Current disposition

`ACTIVE` — the controlled fork candidate and disposable exact-byte matrix are complete. Hosted exact-head CI, canonical-archive application, final overlap review, and authorization remain.

## Next human decision

After the remaining internal gates pass, decide whether to authorize an upstream submission and which repository transport to use.

## Authority

Internal repository reads, controlled-fork branch work, tests, patch composition, review, and drafting are authorized. No pull request, upstream issue, comment, email, or review was created. External contact remains unauthorized.
