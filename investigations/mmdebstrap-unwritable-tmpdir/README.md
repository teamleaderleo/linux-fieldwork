# mmdebstrap explicit TMPDIR handling

## In simple words

`mmdebstrap` builds a Debian root filesystem in a temporary directory for tar, squashfs, ext2, ext4, and null output. Before this change, Perl silently skipped an explicitly configured `TMPDIR` when that location could not be used and created the root under `/tmp` instead.

The trigger is narrow, but the temporary object is not a tiny scratch file: it is the working Debian root filesystem. Users often set `TMPDIR` specifically because `/tmp` is a small tmpfs or the wrong disk. Silent fallback can therefore put substantial data on the filesystem they were trying to avoid.

The reviewed change treats a non-empty explicit `TMPDIR` as a strict parent directory. Unset and empty values retain normal system-temp selection.

## Question and answer

**Question:** When a caller explicitly sets `TMPDIR`, should `mmdebstrap` silently choose another filesystem if that path is missing, not a directory, or unusable?

**Answer:** No. Use the exact non-empty path at the real `tempdir()` operation and let that operation fail with a path-specific error. Preserve the previous default selection when `TMPDIR` is absent or empty.

## Debian issue history

- Debian bug: `#1135727`, `TMPDIR silently ignored if unwritable`
- Reporter: Marc Haber
- Opened: 2026-05-05 09:13:01 UTC
- Severity: minor
- Found in: `mmdebstrap/1.5.7-3`
- Pre-submission status check: outstanding and unclassified on 2026-07-30
- Patch follow-up sent: 2026-07-30 16:34:37 UTC
- Debbugs acknowledgement received: 2026-07-30 16:37:06 UTC
- `patch` tag added: 2026-07-30 16:37:08 UTC

The report used:

```sh
TMPDIR=/var/tmp/live mmdebstrap sid /dev/null
```

The configured directory was unusable, and the program logged a temporary root below `/tmp`. The reporter expected the configured path to be used or a warning or error.

## Submission result

The reviewed patch was sent through Outlook to `1135727@bugs.debian.org`, with `1135727-submitter@bugs.debian.org` in Cc. The sent attachment was named `0001-honor-explicit-tmpdir-current.patch`; Outlook reported media type `text/x-diff` and size 3915 bytes.

Debbugs confirmed receipt, forwarded the message to package maintainer `josch@debian.org`, and processed `Control: tags -1 + patch`. One receipt added the `patch` tag; a duplicate processing receipt ignored the repeated request because the same tag was already present.

The exact envelope, receipt times, attachment metadata, sent body, follow-up boundary, and verification command are retained in `submission/README.md` and `submission/email.txt`.

These receipts establish delivery and tag processing. Maintainer review, acceptance, package upload, bug closure, complete source-matrix execution, and Debian autopkgtest remain outside the recorded result.

## Source

- Project: Debian `mmdebstrap`
- Imported revision: `debian/1.5.7-3`
- Upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Reviewed implementation merged in Linux Fieldwork: `c7f586470c34ca21a94a15ff340b3eca067f6ce5`
- Local source: `upstream/mmdebstrap/`

## Why the fallback happened

The original call was:

```perl
$options->{root} = tempdir('mmdebstrap.XXXXXXXXXX', TMPDIR => 1);
```

In `File::Temp`, `TMPDIR => 1` delegates directory selection to `File::Spec->tmpdir`. On Unix, that routine checks candidates such as the environment's `TMPDIR` and `/tmp` and returns the first writable location. The fallback was therefore normal library behavior, even though it conflicted with the command's user-facing meaning.

## Reviewed implementation

```perl
my @tempdir_options = (TMPDIR => 1);
if (defined $ENV{TMPDIR} && $ENV{TMPDIR} ne '') {
    @tempdir_options = (DIR => $ENV{TMPDIR});
}
$options->{root}
  = tempdir('mmdebstrap.XXXXXXXXXX', @tempdir_options);
```

This is preferable to the first candidate, which created a separate probe file near startup. The reviewed implementation:

- performs the real operation once;
- has no check-then-use interval;
- changes behavior only where the temporary root is actually created;
- uses `File::Temp`'s documented `DIR` interface;
- preserves absent and empty `TMPDIR` behavior;
- keeps the code near the existing rootfs creation logic.

The native `File::Temp` exception names `tempdir()`, the requested path, and the operating-system error. An additional exception wrapper would add code without giving the caller substantially better diagnostic information.

## Practical impact

The frequency is unknown because there is no usage telemetry for this condition. It requires all of the following:

1. an output format that uses a temporary root: tar, squashfs, ext2, ext4, or null;
2. a non-empty explicit `TMPDIR`;
3. a configured path that is missing, is a regular file, is unwritable, or is inaccessible in the selected privilege or namespace context.

Most invocations that leave `TMPDIR` alone are unaffected. A valid explicit directory is also unaffected.

For an affected invocation, the impact can be operationally meaningful:

- a large temporary root can land on a small `/tmp` filesystem or RAM-backed tmpfs;
- the command can later fail with `ENOSPC` far from the configuration mistake;
- disk or memory consumption occurs on an unexpected filesystem;
- automation may continue long enough to make diagnosis harder.

The fallback does not by itself corrupt a successful output. Debian classified the report as minor, which is consistent with a narrow trigger and a clear workaround. A separate older Debian report, `#1052471`, also concerns temporary-directory accessibility in these output paths, showing that temp-root placement has produced real operational problems before, though it is a different defect.

## Expanded verification

Run:

```sh
bash investigations/mmdebstrap-unwritable-tmpdir/deep_review.sh
```

GitHub Actions run `30512275538` on Ubuntu 24.04.4 LTS verified:

- unset `TMPDIR`: status 0, normal `/tmp/mmdebstrap.*` selection;
- empty `TMPDIR`: status 0, normal `/tmp/mmdebstrap.*` selection;
- writable explicit directory: status 0, exact parent honored, cleanup complete;
- unwritable explicit directory: failed, exact path named, no fallback selected;
- missing explicit directory: failed, exact path named, no fallback selected;
- regular file supplied as `TMPDIR`: failed, exact path named, no fallback selected.

It also passed:

- `perl -c`;
- `perlcritic --severity 4`;
- maximum source-code line length of 79 characters;
- POD rendering through `pod2man`;
- exact reviewed-block check;
- ShellCheck and `shfmt` on the rendered upstream regression test.

The runner recorded `perltidy` v20230309. The imported source contains formatting markers for perltidy 20220613, and the newer formatter rewrites many untouched lines. A whole-file formatter comparison is therefore recorded as toolchain-dependent rather than presented as a candidate failure.

## Test-suite scale

The source inventory found:

- 120 registered test definitions and 120 matching test files;
- 3,501 lines across the test scripts;
- 283 generated matrix cases before runtime filters;
- 274 potentially runnable cases on amd64 after static skip expressions;
- 45 definitions requiring root;
- 22 definitions requiring QEMU;
- 27 definitions requiring an isolated apt configuration.

The complete suite was not run here. It requires a prepared local Debian mirror and includes real root creation, several modes and formats, output comparisons, and QEMU cases. The suite runner reports per-case and total timing when executed. The focused deep review, dependency setup, inventory, and artifact handling completed in about 34 seconds; that is not an estimate for the full suite.

See `results/suite-inventory.md` and `results/suite-inventory.json`.

## Documentation improvement

The embedded manual previously described `TMPDIR` only as a tarball concern. The same temporary-root path also serves squashfs, ext2, ext4, and null output. The reviewed wording now names those formats and distinguishes:

- absent or empty `TMPDIR`: use the system temporary location;
- non-empty explicit `TMPDIR`: use that parent and fail if it cannot be used.

## Evidence boundary

This establishes behavior on GitHub-hosted Ubuntu 24.04.4 LTS using the imported Debian revision and the real `mmdebstrap` dry-run path in `chrootless` mode. The focused runtime checks cover six environment states and the relevant source branch. The complete source suite, Debian autopkgtest environment, other architectures, and every privilege mode remain untested in Linux Fieldwork.

The submission evidence adds Outlook envelope and attachment metadata plus automated Debbugs delivery and tag receipts. It does not add maintainer review or a post-send byte comparison of the mailbox attachment.

## References

- Debian bug: `https://bugs.debian.org/1135727`
- Debian manpage: `https://manpages.debian.org/testing/mmdebstrap/mmdebstrap.1.en.html`
- Perl `File::Temp`: `https://perldoc.perl.org/File%3A%3ATemp`
- Perl `File::Spec`: `https://perldoc.perl.org/File%3A%3ASpec`

## Authority

A patch follow-up was sent to the already-open Debian bug #1135727 and processed by Debbugs. Issue #194 records that public thread as the sole current external-contact exception. Every other upstream issue, email, patch, merge request, comment, or review still requires a deliberate decision.