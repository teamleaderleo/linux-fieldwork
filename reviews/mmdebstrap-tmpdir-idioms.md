# mmdebstrap TMPDIR implementation review

## Finding

The first candidate fixed the observed bug but validated `TMPDIR` with a separate probe file near the start of the program. That approach was broader than the documented tarball behavior and introduced a check-then-use interval before the real rootfs directory was created.

## Revised approach

At the actual rootfs `tempdir()` call:

- keep `TMPDIR => 1` when the environment variable is absent or empty;
- use `DIR => $ENV{TMPDIR}` when the caller supplied a non-empty value.

`File::Temp` documents `DIR` as the exact parent directory and `TMPDIR => 1` as using `File::Spec->tmpdir`. `File::Spec->tmpdir` intentionally selects the first writable candidate, which explains the original silent fallback.

This removes the separate probe, avoids a check-then-use interval, and limits the change to the tarball/image/null-output path that actually creates the temporary rootfs.

## Test expectations

- an unusable explicit directory produces an error naming that path and no `/tmp/mmdebstrap.*` fallback;
- a usable explicit directory remains honored and is cleaned up;
- Perl and shell syntax checks pass.

No Debian upstream interaction is part of this review.
