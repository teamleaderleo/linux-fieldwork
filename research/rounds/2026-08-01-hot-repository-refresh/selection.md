# Hot Repository Refresh — Selection Record

Date: 2026-08-01  
Programme routes: `filesystems-images` LF-14, `ecosystem-contributions` LF-35/LF-36, `rootless-execution`, and `services-resources`  
Branch: `research/hot-repos-2026-08-01`  
External-contact state: `false; public state was read only`

## Purpose

Refresh the 2026-07-30 ecosystem candidate scan against repositories that are actively changing now, avoid duplicating active fixes, and promote one bounded current-CI investigation with exact source identities, controls, and stop rules.

The selection rule follows `START_HERE.md` and `FIELD_GUIDE.md`: prefer an exact revision, a small distinguishing fixture, a consequential result, an available environment, and a clear owner. Baseline and candidate must run under the same conditions, cleanup must be explicit, and a red run must be classified before product edits.

## Repositories checked

- `moby/buildkit`
- `moby/go-archive`
- `libarchive/libarchive`
- `util-linux/util-linux`
- `systemd/systemd`
- `NixOS/nixpkgs`

Linux Fieldwork overlap searches found no existing record for the BuildKit/go-archive release window, libarchive RAR5 overlong-varint issue, util-linux user-owned FUSE mount issue, or systemd vmspawn bind issue. The earlier ecosystem scan already tracks libarchive PR #3334 for standalone AppleDouble entries, so that work remains an active-fix reference rather than a new implementation candidate.

## Ranking

### 1. Promote now — BuildKit/go-archive release readiness

**Why now:** BuildKit merged rollback PR #7005 at `275d6864ff0ce91a06225af5f5b012887bd257cf` on 2026-07-31 after go-archive v0.2.1 broke Dockerfile `ADD` for a directory entry with an implied parent. BuildKit added integration tests for implied parents, extraction through `/var/run -> /run`, and hard-link identity.

The two source repairs have since merged to go-archive `main`:

- implied parents: PR #92, merge `279fa6d455e5a39d8e24e67dd236abee6e2de08b`;
- absolute symlink and hard-link resolution: PR #93, merge/current observed head `9e6d2c7c969f4871fe6ded98ae0e28963fde311f`.

The user's BuildKit fork is still at `df0761886a20e368d75e0aa6bb3f20874f58b692`, immediately before the rollback's test additions. That makes the next action concrete: refresh the fork or create a controlled branch from exact upstream rollback head, replace go-archive with exact current `main`, and run the new integration cases plus go-archive's own suite.

**First probe:** compare four dependency states under the same BuildKit test fixture:

1. last known good v0.2.0;
2. regressing v0.2.1;
3. released v0.3.0 without later repairs;
4. go-archive current `main` at `9e6d2c7...`.

**Required discriminators:**

- implied parent is missing versus explicit;
- final entry is a directory versus regular file;
- absolute symlink target exists versus is created during extraction;
- regular file and hard-link source traverse the absolute symlink;
- relative symlink escape remains rejected;
- `Untar` and `UnpackLayer` agree;
- whiteout, opaque-whiteout, and deferred directory timestamp paths retain the same root-relative identity;
- repeated run has identical file tree, inode relationships, and cleanup state.

**Performance boundary:** PR #93 explicitly describes its path resolution as a compatibility workaround and points to future handle-relative operations. Record syscall/time deltas against v0.2.0 before recommending a BuildKit bump.

**Decision:** opened `investigations/buildkit-go-archive-release-readiness/`.

### 2. Fast novel code candidate — libarchive RAR5 overlong varint

Issue #3300 reports that `read_var()` reads at most eight bytes but reports or consumes nine when all eight continuation bits remain set. The confirmed effect is a one-byte parser desynchronization and later header CRC failure. The report deliberately does not claim memory corruption or exploitability.

Current observed upstream head: `8c4acda5e74bc61c0436bbdf1f6a955e6141e3f6`. No equivalent pull request appeared in the refreshed search. The user's libarchive fork has additional internal evidence work at `5cbeac6081fd4ea07ea71f6a8d3d8988f4449d68`, so a new fix branch must start from refreshed upstream rather than assuming the fork's default branch is current.

**First probe:** construct the smallest normal/overlong RAR5 pair, prove exact byte consumption through the API, then add a `DEFINE_TEST` regression before changing `read_var()`.

**Controls:** valid one- through eight-byte encodings, eight-byte terminated maximum, eight continuation bytes at header end, truncated input, both `pvalue_len` and consuming call modes, and immediate next-header alignment.

**Why second:** small, current-CI compatible, likely one source function plus one test. It is the best direct implementation candidate after the BuildKit release-window validation.

### 3. Independent review only — libarchive AppleDouble PR #3334

PR #3334 is open and mergeable at head `cffa2735739f023e1982d7a4e0d0f33a93ddcf6c`. It already covers a valid pair, adjacent standalone `._` entries, and end-of-archive. Do not create a competing implementation.

A useful bounded review can challenge extension headers, GNU longname/PAX paths, invalid checksums, non-UTF-8 conversion, directory trailing slashes, maximum metadata size, streaming read-ahead, and whether a malformed following header can still cause silent consumption.

### 4. Capability queue — util-linux user-owned FUSE mount

Issue #4253 shows an fd-based FUSE mount successfully reaches `fsmount()`, then libmount's `statx(AT_EMPTY_PATH, STATX_MNT_ID)` fails with `EACCES` for a nonzero FUSE owner. The detached mount is then closed instead of attached. No equivalent pull request appeared in the refreshed search.

Current observed upstream head: `fd82c4043fab942b889f478800118c66edfbc39f`. Repository `AGENTS.md` requires Linux-kernel style, tests, human-only credit, and a `Signed-off-by` line.

**Gate:** root, `/dev/fuse`, fd-based mount support, and safe mount cleanup. Queue behind an environment preflight. A source-only patch without the real FUSE boundary is insufficient.

### 5. VM queue — systemd vmspawn user bind

Issue #43141 reports that a normal `--bind` leaves `userns_fd=-EBADF`, but `start_virtiofsd()` calls `namespace_enter()` unconditionally. An unprivileged caller therefore receives synthetic `EPERM` even though no namespace transition is needed. The issue includes an automated bisect to first bad commit `fd05c6c7593c5e36864d8784df91b878bbf991ab`.

Current observed upstream head: `6a863b4dc31adc49fdfdd5deba32ed1b115adda3`. No equivalent pull request appeared in the refreshed search.

**Gate:** bootable image, kernel, virtiofsd, KVM/QEMU environment, and an ordinary-user run. A unit-level guard test may be useful, but the final proof must read the host probe inside the guest.

### 6. Continue harvesting — Nixpkgs

Nixpkgs remains the hottest repository by commit volume, but the current front page is dominated by package updates and staging merges. Use LF-35 to select one package regression with a pinned good/bad range and no active fix rather than treating repository activity itself as a candidate.

## Immediate execution order

1. BuildKit/go-archive exact dependency matrix and integration proof.
2. libarchive RAR5 normal/overlong fixture and source review.
3. review PR #3334 only if the first two are blocked.
4. run util-linux and systemd preflights when privileged/VM capacity is available.

## Stop rules

Stop and reclassify rather than patch when:

- an equivalent active fix or claim appears;
- the first failure belongs to dependency selection, fixture construction, missing privilege, or stale source rather than product behavior;
- the candidate requires broad architecture changes before a minimal failing test exists;
- the environment cannot execute the defining boundary;
- cleanup cannot prove the checkout, mounts, processes, sockets, and temporary trees are restored.

## External-contact state

No issue, pull request, comment, review, email, or other upstream contact was created. Any future public action requires explicit authorization after exact-head testing and overlap refresh.
