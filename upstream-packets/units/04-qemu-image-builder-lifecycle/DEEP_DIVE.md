# Deep dive

## Baseline lifecycle

The builder creates the filesystem directly at `IMAGE`, then later extends, partitions, and copies the FAT image into the same pathname. The final name therefore appears before all failure points have completed. Cleanup owns only `WORKDIR`, and one trap action is shared by ordinary exit and INT/TERM/QUIT.

Two defects compose in the same source region:

1. direct final-name writes expose or replace output before success;
2. a cleanup-only signal trap can return to interrupted control flow and resume later work.

The focused patches overlap mechanically in the `WORKDIR`/cleanup/trap block. PR #195 is the reviewed composition.

## Candidate lifecycle

`prepare_image()` validates the original destination spelling, resolves the existing parent, refuses a parent resolving to `/`, creates a private sibling directory, and assigns an uncreated `image` path inside it. Keeping the temporary directory beside the destination makes the final rename same-filesystem.

Every image mutator receives `IMAGE_TMP`. `publish_image()` performs exactly one rename to `IMAGE`, clears ownership of the moved temporary file, and removes the empty private directory. Unexpected residue produces a warning and remains available for diagnosis.

`exit_cleanup()` captures the command result, disables all traps, runs cleanup, and promotes cleanup failure only when the command result was zero. `signal_exit()` disables traps, cleans once, and preserves the signal-derived status over cleanup errors.

## Publication truth

Before the rename, the final pathname remains the caller's prior object or remains absent. After the rename, the completed image is the committed result. A later signal can change the wrapper result while leaving the already-published image intact.

## Path interpretation repair

The first canonical composition accepted an existing directory argument ending in `/`. `dirname` and `basename` could reinterpret that spelling as a nested `directory/directory` destination. The repaired composition rejects the original trailing-slash spelling before `mktemp`.

## Packet extraction repair

The retained internal patch was generated against a source slice beginning at `WORKDIR=`. Its first hunk was `@@ -1,12 +1,78 @@`; when applied to the full script, `patch` had to locate that hunk hundreds of lines later. Issue #397 requires a patch applying without offsets.

The packet regenerates source coordinates against the complete upstream file:

- first lifecycle hunk: source line 318;
- `mke2fs` hunk: source line 406;
- final mutation hunks: source lines 465, 474, and 483.

The packet regression explicitly rejects the sliced-tail coordinate and requires these full-file coordinates. An exact imported-source test applies with `--fuzz=0`, rejects any transcript containing `offset` or `fuzz`, and runs `sh -n`.

## Result precedence

| Primary event | Cleanup result | Final result |
| --- | --- | --- |
| success | success | 0 |
| success | failure 74 | 74 |
| command failure 42 | any cleanup failure | 42 |
| HUP | any cleanup failure | 129 |
| INT | any cleanup failure | 130 |
| QUIT | any cleanup failure | 131 |
| TERM | any cleanup failure | 143 |

## Compatibility choices

- A final symlink is replaced as a directory entry; its referent remains unchanged.
- New file mode follows producer creation under the caller's umask.
- Replaced inode metadata is not copied.
- A destination directly below `/`, including through a symlinked parent, is refused.
- Parent-only signal delivery may wait until a foreground command returns.

## Evidence boundary

The retained dynamic matrix uses small files and real shell signals. It establishes pathname ownership, publication, result precedence, cleanup, and rerun behavior. It does not execute `mmdebstrap`, filesystem creation, partition tools, mounts, QEMU, or multi-gigabyte images in this pass.
