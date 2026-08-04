# Race-safe backup rollback design

## Decision

Do not remove a failed destination by resolving the final pathname after the copy error.

For a real backup transaction, copy into an operation-owned named staging file in the destination directory. Publish the completed staging inode to the final name with an atomic no-clobber operation. Restore the backup after copy failure with the same no-clobber rule.

This removes the check-then-unlink race from the held candidate. A pathname inserted by another actor is never deleted or overwritten.

## Why the held design is rejected

The held semantic candidate performs:

```text
remove_file(final pathname)
rename(backup pathname, final pathname)
```

It has no stable authority over the final pathname at cleanup time. Even an inode comparison immediately before `remove_file()` leaves a gap between the comparison and unlink.

The candidate passes the GNU behavior matrix in single-actor tests, but its destructive cleanup authority is not safe enough for promotion.

## Required primitives

The transaction needs:

1. a uniquely named staging file created with exclusive, no-follow semantics in the destination directory;
2. an open file handle retained through copy and finalization;
3. no-clobber publication from staging name to final name;
4. no-clobber restoration from backup name to final name;
5. unlink only of names created or retained by this operation.

The current workspace already carries the `tempfile` crate, although `uu_install` does not yet depend on it. A named temporary file in the target directory is one viable staging owner.

Rustix exposes `linkat()` broadly and `renameat_with(..., RenameFlags::NOREPLACE)` on supported kernels. A same-directory hard-link publication is sufficient for a regular-file candidate:

```text
link staging -> final       # fails if final exists
unlink staging
```

Restoration uses the same sequence:

```text
link backup -> final        # fails if final exists
unlink backup
```

The link operation is the no-clobber decision. There is no separate existence check.

`renameat_with(NOREPLACE)` may be used where its platform support is explicit, but the design must not silently fall back to overwriting rename.

## Transaction state machine

### Entry

The existing destination has already been moved to a distinct backup path by `perform_backup()`.

```text
final: absent
backup: original inode
staging: absent
```

### Copy preparation

Create a named staging file in `final.parent()` using exclusive creation. Retain its file handle and exact staging path.

```text
final: absent
backup: original inode
staging: operation-owned new inode
```

### Data-copy failure

1. close or retain the failed staging handle as needed for diagnostics;
2. unlink only the operation-owned staging name;
3. publish `backup -> final` with no-clobber semantics;
4. after successful publication, unlink the backup name;
5. return the original copy error.

Successful rollback:

```text
final: original inode
backup: absent
staging: absent
```

Concurrent replacement conflict:

```text
final: unrelated replacement, untouched
backup: original inode, retained
staging: absent
result: restoration-conflict error
```

The conflict result is safer than deleting or displacing the replacement. The original remains recoverable at the backup path.

### Data-copy success

1. publish `staging -> final` with no-clobber semantics;
2. unlink the staging name after successful publication;
3. retain the open file handle;
4. run fd-bound strip, ownership, permissions, timestamps, and supported security-context work;
5. verify final-path identity before reporting success.

After publication:

```text
final: new inode
backup: original inode
staging: absent
```

A publication conflict leaves the concurrent final entry untouched, removes the operation-owned staging name, retains the original backup, and returns a conflict error.

### Finalization failure

Rollback does not apply after completed copy publication.

- strip failure may remove the published destination only through the fd-bound identity owner;
- chown, chmod, timestamp, or later failure that leaves the entry does not restore the old destination;
- the original remains at the backup path, matching the recorded GNU phase boundary.

## Relationship to upstream PR 12063

The active fd-bound proposal changes copy functions to return the created `File`, performs post-copy operations through that handle, and checks final-path identity before success.

The rollback candidate should be modeled on top of that ownership transfer, not beside it.

The bounded integration points are:

- backup mode with a distinct backup path selects staged copy;
- staging copy returns the open file handle;
- no-clobber publication occurs after complete data copy and before finalization;
- the existing fd-bound finalizer receives the published file handle;
- no-backup behavior remains outside this rollback lane.

This lane does not need to redesign all safe-copy traversal or replace the broader fd-bound work.

## Error policy

The source candidate needs distinct diagnostics for:

- staging-file creation failure;
- staging publication conflict/failure;
- backup restoration conflict/failure.

When copy failure and restoration failure both occur:

1. retain or report the original copy error;
2. return the restoration error as the controlling recovery failure;
3. preserve the original at the backup path;
4. never overwrite an occupied final pathname.

## Required controls

### Existing semantic controls

- simple, existing, and numbered backup restoration after source read failure;
- seeded existing mode preserves the older numbered backup;
- multi-source simple mode permits the later successful source and preserves the original backup;
- no backup mode retains its existing partial-destination behavior;
- strip/finalization failure does not restore the old destination.

### New ownership controls

1. **Concurrent final replacement during copy failure**
   - replacement remains byte-for-byte unchanged;
   - original remains at the backup path;
   - staging name is absent;
   - command reports restoration conflict.

2. **Concurrent final replacement before successful publication**
   - replacement remains unchanged;
   - completed staging inode is removed or retained only under its private name for diagnosis;
   - original remains at backup path;
   - command reports publication conflict.

3. **Open-handle identity after publication**
   - published final path resolves to the same inode as the retained staging handle;
   - finalization uses that handle.

4. **No-clobber helper reversal**
   - absent final permits publication;
   - occupied final rejects publication without modifying either inode.

5. **Cleanup authority**
   - every unlink target is either the unique staging name or a backup name after successful no-clobber publication;
   - no code path unlinks the final pathname merely because metadata matched earlier.

## Executable model

`tests/test_coreutils_install_backup_rollback_model.py` exercises the filesystem transaction with same-directory hard links.

It is model evidence only. It does not prove Rust integration, target portability, copy/finalization behavior, or compatibility with PR 12063.

## Promotion gate

Do not permit a source-only candidate until:

1. the guarded transformation applies to one exact fd-bound source head;
2. the target diff contains the intended dependency, source, locale, and tests only;
3. the concurrent replacement controls execute deterministically;
4. focused tests, the complete `install` module, formatting, clippy, and relevant inherited workflows pass;
5. the complete current diff is reviewed against current canonical main;
6. temporary carrier files are absent from the source candidate.

Canonical upstream contact remains separately unauthorized.
