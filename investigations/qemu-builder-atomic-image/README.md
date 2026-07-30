# QEMU image builder atomic publication

## In simple words

`mmdebstrap-autopkgtest-build-qemu` created and modified the caller's final image pathname before EFI and partition construction completed. A late failure could therefore leave a partial image or destroy an existing trusted image.

This focused candidate builds in a private sibling directory and publishes the completed image with one same-filesystem rename only after all mutations succeed. PR #195 is the canonical composition with signal handling.

## Canonical records

- Issue: #191
- Focused candidate: PR #192
- Integration candidate: issue #193 / PR #195
- Imported source: `upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu`
- Candidate patch: `0001-publish-image-atomically.patch`
- Regression: `tests/test_qemu_builder_atomic_image.py`
- Related signal work: #170 / PR #172

## Baseline publication boundary

The imported script passes final `IMAGE` directly to `mke2fs`, then later modifies it with `truncate`, `sfdisk`, and `dd`. EFI analysis and FAT construction occur between those operations. Cleanup removes only `WORKDIR`.

Thus final-name visibility begins at `mke2fs`, not at the success message.

## Candidate

`prepare_image()`:

1. resolves the existing final parent directory, including an explicitly selected filesystem-root parent;
2. rejects invalid basenames;
3. normalizes the final pathname to that canonical parent;
4. creates a private sibling directory with `mktemp -d`;
5. chooses an uncreated `image` pathname inside it.

The image file itself is created by `mke2fs`, not by `mktemp`, so its mode follows ordinary creation under the caller's umask rather than becoming 0600.

Every image mutation uses `IMAGE_TMP`:

- `mke2fs`;
- final size extension;
- GPT creation;
- FAT partition copy.

`publish_image()` first performs the one committing operation:

```sh
mv --no-target-directory -- "$IMAGE_TMP" "$IMAGE"
```

It then clears active temporary-image ownership and attempts to remove the now-empty private directory. Directory cleanup after the rename is best effort. If unexpected residue prevents `rmdir`, the command emits a warning but keeps the successful publication result truthful.

Because the private directory is a sibling of the final pathname, publication uses same-filesystem rename semantics.

Ordinary pre-publication cleanup removes only the private temporary image and directory. It never removes or restores the caller's final image.

## Negative control and regression

The exact candidate patch is applied to a temporary copy and checked with `/bin/sh -n`. A reduced harness executes the real helper functions.

Required cases:

- existing final sentinel + injected failure: sentinel bytes and mode unchanged, no sibling temporary state;
- absent final + injected failure: final remains absent;
- success: complete bytes atomically replace the old image, effective mode is 0644 under umask 022, no temporary state;
- final symlink: publication replaces the symlink itself while preserving its referent byte-for-byte;
- unexpected post-rename residue: final image is complete, status remains success, a warning names the retained private directory, and the published image is absent from that directory;
- source contract: all four mutation commands target `IMAGE_TMP`, exactly one publication precedes the success message, and publication precedes active-state clearing.

## Execution record

Exact focused head `f6d438e978f03c52de48a9c3465de0d825b809bd` passed Linux Fieldwork CI run `30570114067`. The complete repository unit suite, exact patch application, full candidate shell syntax, six focused publication scenarios, and repository shell/help checks passed.

PR #195 then composed this mechanism with terminating HUP/INT/QUIT/TERM handling and explicit cleanup-failure precedence. Its exact head `dec8133d1e90de51dae603bc2b195ed1ae32b0ac` passed Linux Fieldwork CI run `30577530343`.

## Compatibility and security boundary

This focused candidate supports an explicit final pathname directly below `/`. The integrated candidate follows issue #193's stricter contract and refuses a parent resolving to `/` before mutation. The combined decision in PR #195 supersedes this focused compatibility choice for final promotion.

A successful build still replaces an existing final pathname. When that pathname is a symlink, atomic rename replaces the symlink itself while preserving its referent. A new inode does not preserve the mode, ownership, ACLs, or xattrs of a replaced image.

The candidate does not fsync the file or parent directory, lock the destination, detect concurrent publishers, or validate final image contents. Unexpected post-publication residue remains in the private directory with a warning for diagnosis.

## Signal composition

PR #195 proves that signal cleanup removes only active pre-publication private state, preserves an existing final image, returns HUP/INT/TERM statuses 129/130/143, leaves a published final image intact, and permits immediate rerun. Parent-only signal promptness and child forwarding remain separate boundaries.

## Cleanup and safety

The regression creates small text files only. It does not run mmdebstrap, mke2fs, partition tools, QEMU, mounts, root operations, or large sparse images.

## Disposition

**READY FOR FINAL HUMAN CHECK as a focused mechanism record.** Use PR #195 as the canonical combined landing candidate. No Debian or external upstream contact is included or authorized.
