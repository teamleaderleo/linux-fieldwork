# uutils `install`: restore backup after data-copy failure

## TL;DR

When uutils `install` is asked to make a backup, it renames the existing destination before copying. If `copy_file()` then fails, current source returns without restoring the renamed destination. GNU `install` 9.7 rolls that transaction back: it removes any partial destination, restores the original path, and removes the transient backup.

A controlled candidate is staged on `teamleaderleo/coreutils` and deliberately excludes later strip, ownership, permissions, timestamps, SELinux, and verbose-output failures. Those happen after the data copy completes and have different GNU cleanup behavior.

## Explain like I'm five

Before replacing `dest/file`, backup mode moves the old file out of the way. If reading the new source breaks, the old file should be moved back. uutils currently leaves the old file under a backup name and may leave a broken new file at `dest/file`.

## Why care

The destination can stop containing its original bytes after a failed install. In a multi-source command, a later source can also overwrite the simple backup that held the original destination, losing the only intact copy.

## Current state

- State: `EXECUTING`
- Canonical source base: `uutils/coreutils@a73055191b6d8f144c96bd487c90ae270f30c7a3`
- Controlled branch: `teamleaderleo/coreutils:fieldwork/install-restore-backup-on-copy-error`
- Controlled staged head: `41c7b608f715e8ac4552fd825dd569d4c15f6e33`
- Controlled draft PR: `teamleaderleo/coreutils#3`
- Clean comparison base: `teamleaderleo/coreutils:base/canonical-main-20260803`
- Hosted gate: coreutils run `30799467577`, queued at this checkpoint
- First incomplete step: execute the fail-closed transformer, focused tests, complete install test module, formatting, and clippy
- Cleanup state: source branch contains a temporary transformer and workflow; a green push gate must remove both and produce a source/test-only head
- Next safe action: inspect the first completed workflow step and repair its actual owner
- External-contact state: no canonical-upstream issue, PR, comment, review, email, or patch submission authorized or made

## Intent and precedent

`perform_backup()` currently renames the destination to a backup path. `copy()` then calls `copy_file()` and propagates any error directly. There is no visible rollback between those operations.

GNU behavior separates two phases:

- data-copy failure: restore the pre-copy destination;
- post-copy finalization failure such as strip: do not restore it.

This is separate from just-created destination ownership in issue #12926. A failed data copy must not reserve the destination name. The correct repair is rollback, followed by normal processing of later operands.

## Question

When backup mode has already renamed an existing destination and `copy_file()` fails, should uutils restore the destination and remove the transient backup before returning the copy error?

## Source

- Project: uutils/coreutils
- Base commit: `a73055191b6d8f144c96bd487c90ae270f30c7a3`
- Staged head: `41c7b608f715e8ac4552fd825dd569d4c15f6e33`
- Candidate source commit: pending hosted promotion
- Controlled repository: `teamleaderleo/coreutils`
- Imported source tree: none; exact Git identities are the source boundary

## Environment

- GNU reference: `/usr/bin/install`, GNU coreutils 9.7
- Reference fixtures: disposable local Linux temporary directories
- Deterministic source error: symlink to `/proc/self/mem`, producing `EIO`
- Hosted candidate environment: GitHub Actions `ubuntu-latest`
- Candidate toolchain: stable Rust with rustfmt and clippy

## Baseline behavior

Current source performs:

1. rename destination to backup path;
2. call `copy_file()`;
3. return its error directly.

A read failure can therefore leave a partial destination and the original at the backup path. A later simple-backup operation can rename the partial destination over that backup.

## Candidate

Add `restore_backup_after_copy_failure()` and invoke it only when:

- `perform_backup()` returned a distinct backup path; and
- `copy_file()` returned an error.

The helper removes any partial destination and renames the backup to the original path. If restoration succeeds, return the original copy error. If restoration fails, report the copy error and return a distinct restoration error.

The candidate skips a nominal backup path equal to the destination, preserving the existing empty-suffix behavior for the separate shared backup-suffix fix.

## Reproduction

See [`GNU_BEHAVIOR_RECEIPT.md`](GNU_BEHAVIOR_RECEIPT.md).

Representative command:

```sh
ln -s /proc/self/mem source/file
printf original > dest/file
install --backup=simple source/file dest/file
```

GNU exits 1 for the read error, leaves `dest/file` containing `original`, and leaves no `dest/file~`.

## Results

The candidate is staged by `.fieldwork/apply-install-backup-rollback.py`. It uses exact single-occurrence replacements so source drift fails before compilation.

Focused candidate tests cover:

- simple, existing, and numbered backup restoration;
- multi-source simple mode retaining the original backup for a later successful source;
- seeded existing mode preserving an older numbered backup and removing the transient new backup.

No candidate test result is claimed until hosted execution completes.

## Interpretation

The backup rename and data copy form one recoverable transaction. Finalization begins only after `copy_file()` succeeds, so finalization cleanup must remain outside this rollback.

## Evidence boundary

The candidate has not received a green executable receipt. Restore-failure diagnostics, ENOSPC write failures, dangling-symlink destinations, non-Linux platforms, SELinux, and empty backup suffixes are not independently demonstrated. The GNU evidence uses a source-side `EIO` fixture.

## Next step

Inspect run `30799467577`. On green promotion, verify temporary files were removed, inspect the final source/test/locale diff, compare against current canonical main, update this record with exact blobs and job receipts, and retain the draft without canonical-upstream contact.

## Authority

No canonical-upstream interaction has been authorized or made. Draft `teamleaderleo/coreutils#3` exists only in the controlled fork.
