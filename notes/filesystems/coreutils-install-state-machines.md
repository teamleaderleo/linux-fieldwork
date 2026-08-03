# Coreutils `install`: two file-replacement state machines

## In simple words

Two nearby bugs can look like one bug because both involve the same destination path, but they ask different questions.

1. **Destination ownership:** Did this command successfully finish the data-copy step for this name? If yes, a later source in the same command must not silently overwrite it.
2. **Backup rollback:** Did this command move the old destination aside and then fail before the replacement data copy completed? If yes, put the old destination back.

Keeping those questions separate prevents a tempting but wrong fix: treating a failed copy as a successfully created destination. GNU behavior shows that a failed data copy does not reserve the name; when a real backup was made, the old destination is restored instead.

## The literal example

Start with:

```text
dest/file = original
source1/file = unreadable source
source2/file = second
```

Run:

```sh
install --backup=simple -t dest source1/file source2/file
```

The intended sequence is:

```text
1. Move dest/file to dest/file~.
2. Try to copy source1/file to dest/file.
3. The data copy fails.
4. Remove any partial dest/file.
5. Move dest/file~ back to dest/file.
6. Continue to source2/file.
7. Move the restored original to dest/file~.
8. Install source2/file as dest/file.
```

Final state:

```text
dest/file  = second
dest/file~ = original
```

The first failed source never owns `dest/file`. The later successful source does.

## State machine A: per-invocation destination ownership

The owner is the multi-source command invocation.

### States

- `Unowned`: no earlier operand completed the data-copy step for this destination.
- `Owned`: an earlier operand completed the data-copy step for this destination.
- `Released`: a later finalization failure removed the destination entry, so the name can be used again.

### Transitions

| Event | Transition |
|---|---|
| source stat failure | stay `Unowned` |
| `--compare` determines no copy is needed | stay `Unowned` |
| data copy fails | stay `Unowned` |
| data copy completes | `Unowned -> Owned` |
| chown/chmod/metadata failure leaves file present | stay `Owned` |
| strip failure removes destination | `Owned -> Released` |
| later same-name source in ordinary/simple/existing mode | reject while `Owned` |
| explicit numbered-backup mode | allow repeated destination |

The important discriminator is not “did the function return `Ok`?” Finalization can fail after the installed data already exists. The important event is “did the data-copy phase complete?”

## State machine B: pre-copy backup transaction

The owner is one replacement attempt.

### States

- `NoBackup`: no existing destination was renamed aside.
- `BackedUp`: the old destination now exists at a distinct backup path.
- `Committed`: the replacement data copy completed.
- `RolledBack`: the replacement data copy failed, any partial destination was removed, and the backup was restored.

### Transitions

| Event | Transition |
|---|---|
| destination missing or backup mode off | stay `NoBackup` |
| distinct backup rename succeeds | `NoBackup -> BackedUp` |
| data copy completes | `BackedUp -> Committed` |
| data copy fails | `BackedUp -> RolledBack` |
| strip/finalization fails after data copy | remain `Committed`; do not restore old destination |

Rollback is deliberately narrower than “any later error.” Once the data copy completed, GNU treats the replacement as having happened even if stripping or metadata finalization later fails.

## Why `cp` is not direct implementation precedent

`cp` often copies a regular destination to its backup path rather than renaming the only original away. That means the original destination can remain available until replacement. `install` currently renames the destination before copying, so it needs an explicit rollback path when the copy fails.

The shared backup module chooses names and modes. It does not own the transaction or know whether a caller renamed, copied, linked, or moved the destination. Rollback therefore belongs with the utility operation that performed the rename.

## Codebase conventions that govern the fix

- GNU executable behavior and documentation are compatibility oracles; GNU source code is not an acceptable implementation source.
- Paths remain `Path`/`PathBuf`, not UTF-8 strings.
- A change should be small, focused, and separately testable.
- Rustfmt and clippy are gates, not optional polish.
- Tests should distinguish the intended transition, not merely assert a non-zero exit.
- Platform-specific fixtures use `#[cfg]` and should not weaken cross-platform compilation.
- Comments explain why a transition exists rather than narrating each line.
- No function should panic or exit the process directly.

## Review questions

For any file-replacement patch, ask:

1. Who owns this state: the whole invocation, one operand, or one syscall sequence?
2. What exact event commits the state?
3. Which failures happen before commitment, and which happen after?
4. Does cleanup preserve the last known-good user data?
5. Does a later operand observe a restored, partial, absent, or completed destination?
6. Are backup modes behaviorally different, especially explicit numbered versus existing mode?
7. Does the code compare path spellings, directory entries, or file identity, and is that distinction intentional?
8. Can a race replace the path between the operation and the cleanup check? If so, should the conservative behavior refuse further overwrite?
9. Does an active adjacent PR move the same lifecycle boundary, requiring a narrow rebase-friendly hook instead of duplicate logic?
10. Can every plain-language claim be pointed to a focused test or behavior receipt?

## Evidence boundary

This note records the design model derived from controlled uutils branches and GNU `install` 9.7 black-box probes. It does not claim either candidate is accepted upstream or fully cross-platform until its executable gates and final source-only review are complete.

## Authority

This note authorizes no upstream contact.