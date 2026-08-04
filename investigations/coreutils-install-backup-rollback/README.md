# uutils `install`: restore backup after data-copy failure

## TL;DR

GNU `install` 9.7 restores an existing destination when backup mode renamed it aside and the replacement data copy fails. Current uutils source does not.

A staged path-based candidate reproduces GNU's single-actor rollback matrix and passes its focused target gates, but self-review found that its cleanup can delete a replacement inserted by another actor. Source promotion is disabled.

The selected next design does not copy into the final pathname. It uses an operation-owned staging file in the destination directory, publishes completed data with atomic no-clobber semantics, and restores the backup with the same no-clobber rule. A concurrent replacement remains untouched while the original stays recoverable at its backup path.

## Explain like I'm five

The old file is moved aside before the new one is copied. If the new copy breaks, the old file should go back.

The command must not erase a different file that appeared at the same name meanwhile. The safe plan keeps the unfinished copy under a private name and only moves a completed or restored file into the public name when that name is still empty.

## Why care

Without rollback, a failed install can strand the original under a backup name and leave a partial destination. A naïve rollback can be worse: it can remove or overwrite an unrelated replacement that appeared after the failure.

## State and exact identities

- State: `REPAIR DESIGN — PATH-BASED SOURCE HELD`
- Historical canonical base: `uutils/coreutils@a73055191b6d8f144c96bd487c90ae270f30c7a3`
- Current canonical source reference: active fd-bound PR `uutils/coreutils#12063@eb0d2a0d7627cb563bc24dd4982cb45207810105`
- Controlled repository: `teamleaderleo/coreutils`
- Controlled branch: `fieldwork/install-restore-backup-on-copy-error`
- Controlled held head: `9779591587e4e476d303a3d94f9aa80f86d81195`
- Controlled draft PR: `teamleaderleo/coreutils#3`
- Linux Fieldwork branch: `investigate/coreutils-install-backup-rollback`
- Linux Fieldwork PR: `teamleaderleo/linux-fieldwork#431`
- Source promotion: disabled
- Canonical upstream interaction: none

## Question

How should uutils restore a pre-copy backup after data-copy failure without deleting or overwriting a pathname entry that no longer belongs to the failed copy attempt?

## GNU behavior receipt

Using a source symlink to `/proc/self/mem` for deterministic `EIO`:

- no backup: partial destination remains;
- simple/existing/numbered: original destination restored; transient backup removed;
- seeded existing: older numbered backup preserved; transient next backup removed;
- multi-source simple: later source installs and its backup contains the original destination;
- strip/finalization failure: no rollback.

See [`GNU_BEHAVIOR_RECEIPT.md`](GNU_BEHAVIOR_RECEIPT.md) for the exact matrix.

## Held semantic candidate

The staged transformer adds:

- `RestoreBackupFailed` diagnostics;
- `restore_backup_after_copy_failure()`;
- simple, existing, numbered, seeded, and multi-source controls.

Read-only workflow `30852946251`, job `91817127160`, passed:

- fail-closed transformer application;
- repository formatting;
- all focused rollback tests;
- complete `install` test module;
- focused clippy;
- exact held-candidate diff recording;
- explicit hold enforcement.

This proves the single-actor semantic model only. It does not authorize source promotion.

## Why the path-based source is rejected

The held helper performs:

```text
remove_file(final pathname)
rename(backup pathname, final pathname)
```

Between failed copy and cleanup, another actor can replace the final pathname. The helper has no atomic operation that proves and removes only the failed copy's entry.

An inode comparison immediately before unlink does not solve the problem: the pathname can change between comparison and removal.

The active fd-bound PR retains the created `File` for finalization and checks final-path identity, but its current cleanup helper still uses a metadata check followed by pathname removal. The rollback lane must not add a second version of that authority gap.

## Selected race-safe transaction

The complete design is retained in [`RACE_SAFE_DESIGN.md`](RACE_SAFE_DESIGN.md).

For a real, distinct backup transaction:

1. rename the old destination to its backup path;
2. create an exclusive named staging file in the destination directory;
3. copy source data into that staging file while retaining its open handle;
4. on data-copy failure, remove only the private staging name and restore `backup -> final` with atomic no-clobber publication;
5. on data-copy success, publish `staging -> final` with atomic no-clobber publication;
6. retain the open handle for fd-bound finalization;
7. never unlink the final pathname merely because it matched an earlier metadata observation.

A same-directory hard-link followed by unlink provides the needed no-clobber publication for regular files:

```text
link private-name -> final-name
unlink private-name
```

If `final-name` already exists, the link fails without modifying either entry.

Rustix also exposes `renameat_with(..., RenameFlags::NOREPLACE)` on supported platforms. The implementation may use that primitive where available, but it must never fall back to an overwriting rename.

## Conflict outcomes

### Copy failure, final name still absent

- private staging name removed;
- backup published to final without clobber;
- backup name removed;
- original copy error returned.

### Copy failure, concurrent replacement present

- replacement remains untouched;
- original remains at backup path;
- staging name removed;
- restoration-conflict error returned.

### Copy success, final name still absent

- staging inode published to final;
- private staging name removed;
- open handle retained for finalization;
- original remains at backup path according to backup mode.

### Copy success, concurrent replacement present

- replacement remains untouched;
- staging name removed or retained only under its private diagnostic name;
- original remains at backup path;
- publication-conflict error returned.

## Executable filesystem model

`tests/test_coreutils_install_backup_rollback_model.py` provides five reversing controls:

1. absent final pathname permits backup restoration;
2. concurrent replacement survives copy-failure rollback untouched;
3. completed staging publication preserves open-handle inode identity;
4. concurrent replacement blocks completed-copy publication without overwrite;
5. a no-clobber conflict preserves both source and destination names.

This is model-executed evidence. It does not establish Rust target integration, cross-platform support, finalization behavior, or compatibility with the active fd-bound source.

## Relationship to upstream PR 12063

The active PR changes `copy_file()` and `copy_file_safe()` to return the created `File`, performs Unix finalization through that handle, and checks final-path identity before success.

The rollback candidate should be modeled on top of that source:

- only backup mode with a distinct backup path selects staged copy;
- no-backup behavior remains unchanged;
- no-clobber publication happens after complete data copy and before finalization;
- the existing fd-bound finalizer receives the published staging handle;
- strip and later finalization failures remain outside rollback.

Maintainer feedback on that PR requests Rustix APIs, formatting, and clippy. The next carrier keeps those constraints.

## Required target controls

Existing behavior controls remain required:

- simple, existing, numbered, seeded, and multi-source rollback;
- no-backup partial destination behavior;
- strip failure does not restore the old destination.

New ownership controls are mandatory:

- concurrent replacement during failed copy is untouched and original remains at backup;
- concurrent replacement before successful publication is untouched;
- published final path matches the retained staging handle;
- no-clobber helper rejects occupied final path without modifying either inode;
- all cleanup targets are operation-owned staging or backup names.

## Evidence boundary

Established:

- GNU single-actor rollback semantics for the recorded Linux fixture;
- held path-based semantic candidate passes focused and full target gates;
- path-based cleanup lacks safe destructive authority;
- same-directory no-clobber publication has the required reversal in the retained filesystem model.

Not established:

- a complete Rust candidate on the fd-bound source;
- deterministic target-native concurrent replacement controls;
- non-Linux publication primitive compatibility;
- integration with SELinux, special files, empty backup suffix, or destination write failures;
- current canonical contribution readiness.

## Next step

Prepare a read-only guarded carrier against one exact fd-bound source head. The carrier must apply the staging transaction, add deterministic concurrent replacement controls, run focused and complete `install` gates, and retain the full source diff. Source promotion remains disabled until that exact candidate receives complete-diff acceptance.

No canonical-upstream issue, pull request, comment, review, email, reaction, release, deployment, or patch submission has been authorized or made.
