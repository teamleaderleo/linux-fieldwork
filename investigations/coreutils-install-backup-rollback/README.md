# uutils `install`: restore backup after data-copy failure

## TL;DR

GNU `install` 9.7 restores an existing destination when backup mode renamed it aside and the replacement data copy fails. Current uutils source does not.

A staged semantic candidate reproduces GNU's rollback matrix, but self-review found that its cleanup resolves the destination pathname after failure and could delete a replacement inserted by another actor. Source promotion is therefore disabled. A promotable repair must retain the created destination identity—preferably its open file descriptor—and restore only when the pathname still names that same object.

## Explain like I'm five

The old file is moved aside before the new one is copied. If the new copy breaks, the old file should go back.

But the repair must also check that the broken file it removes is still the file this command created. A stranger could have put a different file at the same name meanwhile.

## Why care

Without rollback, a failed install can strand the original under a backup name and leave a partial destination. A naïve rollback can be worse: it can remove or overwrite an unrelated replacement that appeared after the failure.

## Current state

- State: `HOLD`
- Canonical source base: `uutils/coreutils@a73055191b6d8f144c96bd487c90ae270f30c7a3`
- Controlled branch: `teamleaderleo/coreutils:fieldwork/install-restore-backup-on-copy-error`
- Controlled held head: `9779591587e4e476d303a3d94f9aa80f86d81195`
- Controlled draft PR: `teamleaderleo/coreutils#3`
- Clean comparison base: `teamleaderleo/coreutils:base/canonical-main-20260803`
- Source promotion: disabled
- Next safe action: design rollback around the created destination handle or exact file identity, preferably with the fd-bound install work in upstream PR `#12063`
- External-contact state: no canonical-upstream interaction authorized or made

## Question

How should uutils restore a pre-copy backup after data-copy failure without deleting a pathname replacement that no longer belongs to the failed copy attempt?

## GNU behavior receipt

Using a source symlink to `/proc/self/mem` for deterministic `EIO`:

- no backup: partial destination remains;
- simple/existing/numbered: original destination restored; transient backup removed;
- seeded existing: older numbered backup preserved; transient next backup removed;
- multi-source simple: later source installs and its backup contains the original destination;
- strip/finalization failure: no rollback.

See [`GNU_BEHAVIOR_RECEIPT.md`](GNU_BEHAVIOR_RECEIPT.md) for the exact matrix.

## Baseline operation

Current source performs:

```text
rename old destination to backup
copy new source to destination
return copy error directly
```

The missing semantic transition is:

```text
copy fails before commitment
remove only the partial destination created by this attempt
rename backup back to destination
```

## Held candidate

The staged transformer adds:

- `RestoreBackupFailed` diagnostics;
- `restore_backup_after_copy_failure()`;
- focused simple/existing/numbered/seeded/multi-source tests.

Its behavior is useful evidence, and the read-only workflow may still compile and run it. It may not promote source.

## Self-review failure

The helper currently does:

```text
remove_file(destination pathname)
rename(backup pathname, destination pathname)
```

Between the failed copy and cleanup, the pathname can be removed and replaced. The helper has no descriptor or inode/device identity for the partial file, so it cannot prove that the entry it removes belongs to this operation.

This is especially inappropriate while `install` already has active work to keep copy and finalization bound to the created file descriptor.

## Required design boundary

A promotable implementation should:

1. retain the destination handle when creation succeeds, including when the subsequent data transfer fails;
2. record or derive its stable file identity;
3. before unlinking, verify that the destination pathname still resolves to that object;
4. refuse destructive cleanup on mismatch;
5. restore the backup only after safe removal or verified absence;
6. keep data-copy rollback separate from strip and later finalization failures.

A custom error carrying the open destination handle, or integration with fd-returning copy/finalization work, is preferable to another path metadata check.

## Evidence boundary

The GNU semantics are established for the recorded Linux fixture. No safe source implementation is complete. The held transformer does not establish race-safe cleanup, non-Linux behavior, or integration with fd-bound finalization.

## Next step

Keep the source draft on hold. Review the current state of upstream PR `#12063` and restack the transaction model only when the created file identity can remain available through a failed copy. Add a deterministic pathname-replacement negative control before permitting source promotion.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.