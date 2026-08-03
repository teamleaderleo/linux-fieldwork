# Fork fix and review pass — 2026-08-03

State: `ACTIVE — direct go-archive gate green; fork fixes/tests in CI`  
Branch: `research/fork-fixes-2026-08-03`  
External-contact state: `none; controlled forks and Linux Fieldwork only`

## Coordination boundary

The current Linux Fieldwork retirement record parks unit 16/mmdebstrap. This pass did not reopen or modify that unit.

No claim was treated as an exclusive lock. Before creating work, issue comments, linked pull requests, current source, and controlled forks were checked for existing fixes.

## 1. BuildKit / go-archive release readiness

### Direct library result

The exact four-version implied-parent matrix is green on Linux Fieldwork PR #416.

- exact technical head: `243b27ae7e9862dda5f6f6c64481eeef8e4c424b`;
- workflow run: `30793638884`;
- retained receipt: `investigations/buildkit-go-archive-release-readiness/artifacts/direct-implied-parent-matrix-2026-08-03.md`.

Observed split under equal unprivileged runner identity mapping:

| Candidate | Exact commit | Implied-parent result | Explicit-parent control |
| --- | --- | --- | --- |
| v0.2.0 | `263611f5f0914b2a153d86dae2042d13be6a88c4` | pass | pass |
| v0.2.1 | `0bfb09625293006825b7a57ffca9b9552eb9d872` | required failure | pass |
| v0.3.0 | `1c23372e409716c3691a540871806083644f348a` | required failure | pass |
| repaired main | `9e6d2c7c969f4871fe6ded98ae0e28963fde311f` | pass | pass |

### BuildKit integration carrier

Controlled fork: `teamleaderleo/buildkit`  
Draft PR: #1  
Rollback base: `275d6864ff0ce91a06225af5f5b012887bd257cf`  
Carrier head: `b0df8f0aed8961bb9aabc40ad10aa9430ccadfae`

The read-only carrier replaces go-archive ephemerally and invokes the existing BuildKit integration harness for:

- `TestDockerfileAddArchiveWithImpliedParentDir`;
- `TestDockerfileAddArchiveThroughAbsoluteSymlink`;
- OCI worker only.

Run `30795414508` failed before module changes because a shallow PR checkout did not expose `HEAD^2`. No product test ran. Base commit `36cb79571cd5fe037981843fd575ad787c90d733` replaces that brittle ancestry check with the pull-request event head SHA. Corrected run `30796767974` is the run to interpret.

Do not recommend a dependency bump before that integration result plus hard-link inode, relative-escape, whiteout/deferred-metadata, cleanup/rerun, and performance evidence.

## 2. util-linux user-owned FUSE mount

Issue: util-linux #4253  
Controlled fork: `teamleaderleo/util-linux`

### Source classification

Do not create a duplicate source patch. Current base already contains maintainer commit:

- `1cb24d37de96f32596164ce738713c0c04086044`

That commit makes mount-ID lookup best effort by ignoring the return from `mnt_fs_fetch_ids()` instead of propagating the `statx()` failure.

### Missing regression proof

Test branch: `test/fuse-owner-statx-optional`  
Exact test head: `78a3502d5c3d60b58c39fa68e0c510677aa6b9a0`  
Fork draft PR: #2

Added executable test:

- `tests/ts/mount/fuse-owner-statx`;
- opens `/dev/fuse`;
- creates an fd-based FUSE mount with UID/GID 65534;
- verifies the target is attached with `findmnt`;
- lazy-unmounts, closes the FUSE descriptor, and removes the mountpoint;
- skips unless root, `CAP_SYS_ADMIN`, `/dev/fuse`, and fd-based mount support are available.

Ordinary repository CI compiles/packages the test but does not establish that the privileged mount test executed.

Exact proof carrier: fork draft PR #3  
Carrier head: `d89bdb09eaf7a1ebcb341030a79d5a7ac18f2def`  
Workflow run to interpret: `30796684340`

That carrier performs a native build and runs exactly `sudo ./tests/run.sh --show-diff mount/fuse-owner-statx`, retaining a PASS or capability-SKIP classification.

## 3. systemd vmspawn ordinary bind

Issue: systemd #43141  
Controlled fork: `teamleaderleo/systemd`  
Fix branch: `fix/vmspawn-bind-userns-guard`  
Exact source head: `b35bf743b042a0db82a6fbcf6bf21a6e6419591d`  
Fork draft PR: #5

### Defect

A normal `systemd-vmspawn --user --bind` leaves `userns_fd=-EBADF`, but `start_virtiofsd()` called `namespace_enter()` unconditionally. `namespace_enter()` checks `CAP_SYS_ADMIN` even when every namespace descriptor is invalid, producing synthetic `EPERM` for the ordinary user.

### Fork fix

Guard the namespace transition with `userns_fd >= 0`. This preserves mapped `--bind-user` behavior and skips only the absent transition for ordinary binds.

The final branch differs from `main` only in `src/vmspawn/vmspawn.c`; temporary automation files were removed before opening the real PR.

Static exact-block replacement and `git diff --check` passed in run `30794925014`. Multiple GCC and architecture build jobs have passed. Remaining full build/lint/unit queues must finish before build-green classification.

Final product proof still requires a bootable image/kernel, virtiofsd, ordinary-user guest-visible bind, and a mapped-user control.

## 4. libarchive AppleDouble PR #3334 review

Upstream PR head reviewed: `cffa2735739f023e1982d7a4e0d0f33a93ddcf6c`  
Controlled fork: `teamleaderleo/libarchive`  
Review-test head: `0ff721a7d96274f08a43ff5d080448c8b6a6152a`  
Fork draft PR: #6  
Workflow run to interpret: `30795921904`

### Review concern

`is_mac_metadata_entry()` supports a pathname available only through `archive_entry_pathname_w()`. The new `mac_metadata_matches_next_entry()` matcher uses narrow `archive_entry_pathname()` values and returns true when conversion is unavailable. Returning true consumes the current `._` entry as metadata without proving that its decoded name matches the following entry.

### Discriminator

The added test writes:

1. standalone UTF-8 `._π` with `standalone metadata`;
2. unrelated `unrelated` with `ordinary data`.

It reads under the `C` locale with `hdrcharset=UTF-8` and `mac-ext=1`. The required result is that `._π` remains the first returned wide pathname, followed by `unrelated`.

Do not post upstream feedback until the exact-head test executes and the failure is classified. If it fails as predicted, repair the matcher on the fork and rerun before proposing review text.

## Review sweep

At the last review query, there were no human review submissions or new discussion on:

- Linux Fieldwork PR #416;
- BuildKit fork PR #1;
- util-linux fork PRs #2 and #3;
- systemd fork PR #5;
- libarchive fork PR #6;
- upstream libarchive PR #3334.

Refresh this list before interpreting CI or making any public-contact decision.

## External-contact guard

No upstream issue, pull request, review, comment, email, mailing-list post, or package upload was created. All writes are confined to controlled forks and Linux Fieldwork.
