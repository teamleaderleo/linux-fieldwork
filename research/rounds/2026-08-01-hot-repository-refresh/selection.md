# Hot Repository Refresh — Selection Record

Date: 2026-08-01  
Latest overlap correction: 2026-08-02  
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

The first-pass repository-wide PR search missed an issue comment that directly linked libarchive issue #3300 to PR #3317. The 2026-08-02 correction read the issue comments and full PR state: PR #3317 was merged on 2026-07-27 as `e207c4b357998fe826e67306fa61ad039255022f`. The original RAR5 overlong-varint item is therefore retired, not available for independent implementation.

Linux Fieldwork still has no existing record for the BuildKit/go-archive release window, util-linux user-owned FUSE mount issue, or systemd vmspawn bind issue. The earlier ecosystem scan already tracks libarchive PR #3334 for standalone AppleDouble entries, so that work remains an active-fix reference rather than a new implementation candidate.

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

### 2. Retired — libarchive RAR5 overlong varint

Issue #3300 reported that `read_var()` read at most eight bytes but reported or consumed nine when all eight continuation bits remained set. The confirmed effect was a one-byte parser desynchronization and later header CRC failure.

The issue's only comment links the work to PR #3317, `rar5: Improve varint handling`. That PR:

- expanded RAR5 variable integers to the specification's ten-byte maximum;
- used checked multiplication and addition for 64-bit overflow;
- rejected ten continuation bytes instead of consuming beyond the decoded value;
- merged on 2026-07-27 as `e207c4b357998fe826e67306fa61ad039255022f`.

**Decision:** do not create a competing fix. The earlier statement that no equivalent PR existed was wrong because the overlap search did not read issue comments. Future scans must read comments on a selected issue before classifying it as unclaimed.

### 3. Possible follow-up, not yet promoted — RAR5 field-specific varint bounds

Reviewers on PR #3317 raised two related questions that the merged patch intentionally left for follow-up:

- `read_var()` reads ahead ten bytes without an explicit current-header boundary;
- RAR5's header-size field is specified as no longer than three bytes, while the generic helper now permits ten bytes for every caller.

A refreshed issue and PR search found no separate follow-up record. This is not yet a fix candidate because the first step is caller mapping and a distinguishing malformed-header fixture. The probe must establish whether current code can consume bytes from the next block or accept an overlong field-specific encoding while still passing generic 64-bit validation.

**Stop rule:** do not infer a bug solely from the review comments. Promote only after an exact current-source caller map and a fixture distinguish generic ten-byte validity from field-specific limits.

### 4. Independent review only — libarchive AppleDouble PR #3334

PR #3334 is open and mergeable at head `cffa2735739f023e1982d7a4e0d0f33a93ddcf6c`. It already covers a valid pair, adjacent standalone `._` entries, and end-of-archive. Do not create a competing implementation.

A useful bounded review can challenge extension headers, GNU longname/PAX paths, invalid checksums, non-UTF-8 conversion, directory trailing slashes, maximum metadata size, streaming read-ahead, and whether a malformed following header can still cause silent consumption.

### 5. Capability queue — util-linux user-owned FUSE mount

Issue #4253 shows an fd-based FUSE mount successfully reaches `fsmount()`, then libmount's `statx(AT_EMPTY_PATH, STATX_MNT_ID)` fails with `EACCES` for a nonzero FUSE owner. The detached mount is then closed instead of attached. No equivalent pull request appeared in the refreshed search.

Current observed upstream head: `fd82c4043fab942b889f478800118c66edfbc39f`. Repository `AGENTS.md` requires Linux-kernel style, tests, human-only credit, and a `Signed-off-by` line.

**Gate:** root, `/dev/fuse`, fd-based mount support, and safe mount cleanup. Queue behind an environment preflight. A source-only patch without the real FUSE boundary is insufficient.

### 6. VM queue — systemd vmspawn user bind

Issue #43141 reports that a normal `--bind` leaves `userns_fd=-EBADF`, but `start_virtiofsd()` calls `namespace_enter()` unconditionally. An unprivileged caller therefore receives synthetic `EPERM` even though no namespace transition is needed. The issue includes an automated bisect to first bad commit `fd05c6c7593c5e36864d8784df91b878bbf991ab`.

Current observed upstream head: `6a863b4dc31adc49fdfdd5deba32ed1b115adda3`. No equivalent pull request appeared in the refreshed search.

**Gate:** bootable image, kernel, virtiofsd, KVM/QEMU environment, and an ordinary-user run. A unit-level guard test may be useful, but the final proof must read the host probe inside the guest.

### 7. Continue harvesting — Nixpkgs

Nixpkgs remains the hottest repository by commit volume, but the current front page is dominated by package updates and staging merges. Use LF-35 to select one package regression with a pinned good/bad range and no active fix rather than treating repository activity itself as a candidate.

## Immediate execution order

1. BuildKit/go-archive exact dependency matrix and integration proof.
2. Review current Linux Fieldwork unit work before opening another implementation lane.
3. Map the RAR5 field-specific varint callers only if the BuildKit matrix or current unit work is blocked.
4. Review PR #3334 without duplicating its implementation.
5. Run util-linux and systemd preflights when privileged or VM capacity is available.

## Stop rules

Stop and reclassify rather than patch when:

- an equivalent active fix or claim appears;
- issue comments or linked work identify an existing implementation;
- the first failure belongs to dependency selection, fixture construction, missing privilege, or stale source rather than product behavior;
- the candidate requires broad architecture changes before a minimal failing test exists;
- the environment cannot execute the defining boundary;
- cleanup cannot prove the checkout, mounts, processes, sockets, and temporary trees are restored.

## External-contact state

No issue, pull request, comment, review, email, or other upstream contact was created. Any future public action requires explicit authorization after exact-head testing and overlap refresh.
