# Draft upstream pull request

## Title

QEMU builder: publish completed images atomically and terminate signal cleanup

## Summary

The QEMU image builder now constructs its output in a private sibling directory and exposes the final pathname only through one same-filesystem rename after all image mutations succeed.

Signal cleanup now terminates with conventional HUP, INT, QUIT, and TERM statuses. Cleanup runs once, preserves the primary command or signal result, and reports cleanup failure after an otherwise successful exit.

## Behavior

- preserve an existing image on ordinary failure and pre-publication signals;
- keep an absent destination absent on failure;
- route `mke2fs`, `truncate`, `sfdisk`, and `dd` to the private image;
- publish once before the success message;
- keep a published image after a later signal;
- permit an immediate rerun on the same destination;
- reject trailing-slash image arguments and resolved root parents before mutation.

## Tests

The focused regression applies the patch with zero fuzz and requires zero offsets, checks the complete candidate with `sh -n`, and runs reduced real `/bin/sh` lifecycle cases for failure, signal, publication, cleanup precedence, path rejection, and rerun behavior.

Upstream static checks to list in the final submitted version:

```text
shellcheck --exclude=SC2016 mmdebstrap-autopkgtest-build-qemu
shfmt --binary-next-line --case-indent --indent 2 --simplify -d mmdebstrap-autopkgtest-build-qemu
```

## Limits

Parent-only signal delivery can remain deferred while the shell waits for a foreground child. This change adds no signal forwarding, fsync durability, concurrent-publisher lock, image validation, or metadata inheritance from a replaced inode. Unexpected post-publication residue is retained with a warning.

This draft remains internal pending explicit authorization.
