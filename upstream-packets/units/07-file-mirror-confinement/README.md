# Unit 07 — mmdebstrap file-mirror setup and cleanup confinement

State: `ACTIVE`  
Priority-zero issue: #397, unit 07  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-07-file-mirror-confinement`  
External contact authorized: `false`

## TL;DR

The merged Linux Fieldwork carrier already proves a coherent setup-plus-cleanup repair for `hooks/file-mirror-automount`: resolve sources and destinations, require every target to remain a strict child of the generated root, preserve the configured `file:` URI path for terminal source symlinks, reject every parent component, store constrained NUL-delimited cleanup entries, and preflight the complete marker before destructive actions.

This pass reconciled the carrier with current upstream `main`, composed the three retained local patches into one upstream-path patch, and verified exact application plus POSIX shell syntax. The packet remains `ACTIVE` until the complete fake destructive-command matrix is rerun from the packet patch and the full upstream-facing diff receives an exact-head review.

## Accomplished behavior

Setup canonicalizes the generated root and existing source, refuses `/` as a generated root, keeps the configured URI spelling as the in-root destination when required, resolves destination symlinks, requires a strict descendant, and records one canonical root-relative marker entry only after a successful action.

Cleanup treats the marker as untrusted input. It validates every entry before the first `umount` or `rm -r`, revalidates each entry immediately before acting, retains the marker when validation or an action fails, and removes it only after a complete successful action pass.

## Why care

The baseline constructs `mount`, hook-helper copy/upload, `umount`, and `rm -r` targets through textual path concatenation. Traversal components, a destination-parent symlink, a generated root resolving to `/`, or a corrupted marker can therefore select a host path outside the generated root. Sequential cleanup can also remove valid early entries before discovering a later escape.

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
- a privileged real-mount integration fixture;
- real non-root hook-socket transfer.

### Split boundary

The adjacent carriers change package-test scheduling or service lifecycle. They share a test environment with this hook but modify different source owners and prove different claims. This unit changes only the file-mirror setup/cleanup contract.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS FORK` |
| Candidate head | packet patch SHA-256 `928533ff01be39ba66c5350f7951706fd7f017448449c2671bb95a271db75f25` |
| Linux Fieldwork branch | `upstream/unit-07-file-mirror-confinement` |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | setup blob `6ccbdaf2ba97c77c4e5223ac5280acd51a998424`; cleanup blob `b6b9b46afdd9dad01df3abcb514475326162e42c` |
| Patch or series path | `patches/0001-file-mirror-automount-containment.patch` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo fork and pull request; explicit authorization still required |

## Canonical links

- Priority-zero unit: #397 unit 07
- Owning Linux Fieldwork issue: #164
- Canonical Linux Fieldwork PR: #179
- Adjacent scheduling carrier: #153 / PR #158
- Adjacent HTTP readiness carrier: #79 / PR #90
- Central package-test history: #53
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- current official upstream head identified;
- official hook history shows no file-mirror change after the March 2024 hook commit;
- Debian sid remains on mmdebstrap `1.5.7-3`;
- current packaged setup and cleanup blobs match the Linux Fieldwork imported blobs exactly;
- retained patches 0001, 0002, and 0003 apply in order to those exact source bytes;
- the composed upstream-path patch applies the complete final contract;
- both resulting scripts pass `/bin/sh -n`;
- historical exact-head carrier CI run `30580904313` passed the five-file fake-action matrix at PR #179 head `6db473c5e3e462a93f9ba0bc975dbc46164f863b`.

### Not yet demonstrated

- packet-patch execution of the complete five-file fake destructive-command matrix on the unit branch;
- hosted CI for the packet branch exact head;
- exact-head complete-diff review of the packet patch and public drafts;
- real bind mount/unmount and real non-root hook-helper transfer.

### Compatibility boundary

- harmless `.` and repeated separators normalize;
- every configured `..` component is rejected;
- terminal source symlinks remain usable by separating canonical host source from the APT-visible destination spelling;
- historical leading-slash cleanup markers are rejected during an active run;
- GNU `realpath` and GNU `xargs` behavior is required;
- pathname or marker replacement between validation and action remains possible for a sufficiently capable concurrent actor.

## Candidate organization

One composed patch is proposed upstream because both hook files implement one lifecycle promise and the three local patches are review-history increments rather than independent user-facing features.

1. `patches/0001-file-mirror-automount-containment.patch` — setup containment, URI-path compatibility, parent-component policy, canonical markers, cleanup preflight, and action-time revalidation.

## Current disposition

`ACTIVE` — current-source reconciliation and a composed patch are complete; packet-exact matrix execution and exact-head review remain.

## Next human decision

After the remaining internal gates pass, decide whether to authorize creation of a controlled fork and an upstream pull request.

## Authority

Internal repository reads, branch work, tests, patch composition, review, and drafting are authorized. External issue creation, fork creation, pull request creation, comments, email, or any other upstream contact remain unauthorized and have not occurred.
