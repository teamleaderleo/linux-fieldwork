# QEMU image builder atomic publication

## In simple words

`mmdebstrap-autopkgtest-build-qemu` created and modified the caller's final image pathname before EFI and partition construction completed. A late failure could therefore leave a partial image or destroy an existing trusted image.

This candidate builds in a private sibling directory and publishes the completed image with one same-filesystem rename only after all mutations succeed.

## Canonical records

- Issue: #191
- Imported source: `upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu`
- Candidate patch: `0001-publish-image-atomically.patch`
- Regression: `tests/test_qemu_builder_atomic_image.py`
- Related signal work: #170 / PR #172

## Baseline publication boundary

The imported script passes final `IMAGE` directly to `mke2fs`, then later modifies it with `truncate`, `sfdisk`, and `dd`. EFI analysis and FAT construction occur between those operations. Cleanup removes only `WORKDIR`.

Thus final-name visibility begins at `mke2fs`, not at the success message.

## Candidate

`prepare_image()`:

1. resolves the existing final parent directory;
2. rejects canonical parent `/` and invalid basenames;
3. normalizes the final pathname to that canonical parent;
4. creates a private sibling directory with `mktemp -d`;
5. chooses an uncreated `image` pathname inside it.

The image file itself is created by `mke2fs`, not by `mktemp`, so its mode follows ordinary creation under the caller's umask rather than becoming 0600.

Every image mutation uses `IMAGE_TMP`:

- `mke2fs`;
- final size extension;
- GPT creation;
- FAT partition copy.

`publish_image()` performs:

```sh
mv --no-target-directory -- "$IMAGE_TMP" "$IMAGE"
rmdir "$IMAGE_TMPDIR"
```

and clears the temporary state. Because the private directory is a sibling of the final pathname, publication uses same-filesystem rename semantics.

Ordinary cleanup removes only the private temporary image and directory. It never removes or restores the caller's final image.

## Negative control and regression

The exact candidate patch is applied to a temporary copy and checked with `/bin/sh -n`. A reduced harness executes the real helper functions.

Required cases:

- existing final sentinel + injected failure: sentinel bytes and mode unchanged, no sibling temporary state;
- absent final + injected failure: final remains absent;
- success: complete bytes atomically replace the old image, effective mode is 0644 under umask 022, no temporary state;
- literal filesystem-root parent and a symlink resolving to root: refusal before temporary creation;
- source contract: all four mutation commands target `IMAGE_TMP`, exactly one publication precedes the success message.

## Compatibility and security boundary

A successful build still replaces an existing final pathname. When that pathname is a symlink, atomic rename replaces the symlink itself rather than following it and overwriting its referent. This is a deliberate safer publication semantic and differs from direct in-place construction.

The candidate does not preserve the mode, ownership, ACLs, or xattrs of a replaced existing image; the new image has normal newly-created-file metadata. It does not fsync the file or parent directory, lock the destination, detect concurrent publishers, or validate the final image contents.

## Signal composition

PR #172 changes signal exit semantics. The final combined source must ensure signal cleanup removes only `IMAGE_TMPDIR` and never deletes an existing `IMAGE`. Parent-only signal promptness and child forwarding remain separate from publication atomicity.

## Cleanup and safety

The regression creates small text files only. It does not run mmdebstrap, mke2fs, partition tools, QEMU, mounts, root operations, or large sparse images. Root-parent negative names are unique and asserted absent.

## Disposition

Retain the candidate and regression. No Debian or external upstream contact is included or authorized.
