# Handoff: coreutils install backup rollback

## State

`REPAIR DESIGN — HELD SEMANTIC MODEL GREEN / SOURCE PROMOTION DISABLED`

## Exact identities

- Historical canonical base: `uutils/coreutils@a73055191b6d8f144c96bd487c90ae270f30c7a3`
- Active fd-bound source reference: `uutils/coreutils#12063@eb0d2a0d7627cb563bc24dd4982cb45207810105`
- Controlled repository: `teamleaderleo/coreutils`
- Clean comparison base branch: `base/canonical-main-20260803`
- Held branch: `fieldwork/install-restore-backup-on-copy-error`
- Held head: `9779591587e4e476d303a3d94f9aa80f86d81195`
- Controlled draft PR: `teamleaderleo/coreutils#3`
- Linux Fieldwork branch: `investigate/coreutils-install-backup-rollback`
- Linux Fieldwork PR: `teamleaderleo/linux-fieldwork#431`

## Executed held-model gate

Coreutils workflow run `30852946251`, job `91817127160`: success.

Passed:

- fail-closed path-based candidate transformation;
- repository rustfmt;
- simple, existing, numbered, seeded, and multi-source rollback controls;
- complete `install` test module;
- focused clippy;
- full held-candidate diff recording;
- explicit source-promotion hold.

This is target-executed evidence for the single-actor behavior model. It is not a promotable source receipt.

## Review blocker

The held candidate removes `destination` by pathname after copy failure and then renames the backup into that pathname.

A concurrent actor can replace the path between failure and cleanup. The candidate could delete that replacement and overwrite a name it no longer owns.

A metadata identity check followed by pathname unlink remains vulnerable to change between the check and unlink. Do not repair this by adding another check-then-act sequence.

## Selected transaction

See `RACE_SAFE_DESIGN.md`.

For a distinct backup transaction:

1. move original final entry to backup;
2. create an exclusive operation-owned named staging file in the destination directory;
3. copy into staging and retain its open handle;
4. publish staging to final with atomic no-clobber semantics only after complete data copy;
5. on copy failure, delete only staging and restore backup to final with atomic no-clobber semantics;
6. retain the published staging handle for fd-bound finalization;
7. never unlink an occupied final pathname as rollback cleanup.

Same-directory hard-link publication followed by private-name unlink is the portable model for regular files. `renameat_with(NOREPLACE)` may be used only where its support is explicit.

## Conflict policy

When another entry owns the final pathname:

- leave that entry untouched;
- leave the original at the backup path;
- remove only the operation-owned staging name;
- return a publication or restoration conflict.

Preserving both independently owned entries takes precedence over silently reproducing single-actor GNU output during a race.

## Executable model

`tests/test_coreutils_install_backup_rollback_model.py` retains five controls:

- successful no-clobber restoration;
- restoration conflict preserves concurrent replacement and original backup;
- successful staged publication preserves open-handle inode identity;
- publication conflict preserves concurrent replacement;
- low-level no-clobber conflict preserves both names.

Linux Fieldwork CI is the execution gate for this model. It remains model evidence only.

## Relationship to fd-bound install work

The active upstream proposal returns the created `File`, finalizes through that handle, and checks final-path identity before reporting success.

The next candidate must be applied on top of one exact fd-bound source head. It should alter only the backup-mode data-copy transaction and pass the published file handle into the existing finalizer.

Do not duplicate or supersede the broader fd-bound finalization work in this lane.

## Required next carrier

A read-only carrier should:

1. check out exact fd-bound source `eb0d2a0d...` or its reviewed successor;
2. apply a fail-closed staging transaction;
3. add `tempfile` to `uu_install` only if the selected implementation uses it;
4. add deterministic concurrent replacement controls;
5. run the existing rollback matrix;
6. run relevant fd-bound swap controls from PR #12063;
7. run complete `install` tests, formatting, clippy, and locale checks;
8. retain the full patched diff and exact source identity;
9. perform no source promotion.

## Durable files

- `README.md` — current result and evidence boundary
- `GNU_BEHAVIOR_RECEIPT.md` — GNU 9.7 single-actor matrix
- `RACE_SAFE_DESIGN.md` — selected no-clobber transaction
- `tests/test_coreutils_install_backup_rollback_model.py` — filesystem reversal model
- controlled PR #3 — held target-executed semantic candidate

## First incomplete step

Inspect Linux Fieldwork CI for the new filesystem model and design record.

Then prepare the guarded fd-bound carrier. If an implementation cannot provide deterministic no-clobber conflict behavior, keep the lane held rather than reverting to path-based deletion.

## Authority

Canonical-upstream contact: `false`.

No upstream issue, pull request, comment, review, reaction, email, release, deployment, or patch submission was authorized or made.
