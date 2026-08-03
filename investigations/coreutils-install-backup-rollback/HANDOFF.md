# Handoff: coreutils install backup rollback

## State

`EXECUTING` — separate candidate staged on canonical `a730551…`; hosted gate queued; no candidate execution result yet.

## Exact identities

- Canonical source base: `uutils/coreutils@a73055191b6d8f144c96bd487c90ae270f30c7a3`
- Controlled repository: `teamleaderleo/coreutils`
- Clean comparison base branch: `base/canonical-main-20260803`
- Candidate branch: `fieldwork/install-restore-backup-on-copy-error`
- Candidate staged head: `41c7b608f715e8ac4552fd825dd569d4c15f6e33`
- Candidate draft PR: `teamleaderleo/coreutils#3`
- Linux Fieldwork branch: `investigate/coreutils-install-backup-rollback`
- Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#431`

The controlled fork's default `main` is older. PR #3 was deliberately retargeted to `base/canonical-main-20260803` so its comparison excludes unrelated canonical commits.

## Current gate

- Coreutils workflow: `Fieldwork install backup rollback`
- Run: `30799467577`
- Job: `91640455224`
- Last observed state: `queued`

Do not claim the candidate transformation, tests, formatting, full install module, or clippy passed until this job completes.

## Candidate files before promotion

- `.fieldwork/apply-install-backup-rollback.py`
- `.github/workflows/fieldwork-install-backup-rollback.yml`

The transformer performs exact single-occurrence replacements and exits if source layout differs. A green push gate should apply it, commit source/test/locale changes, remove both temporary files, and push a source-only head.

## Intended source change

- Add `InstallError::RestoreBackupFailed` and English/French messages.
- Add `restore_backup_after_copy_failure()`.
- After `perform_backup()`, catch `copy_file()` failure.
- When a distinct backup path exists, remove any partial destination and rename the backup to the original path.
- Return the original copy error after successful restoration.
- If restoration fails, print the original copy error and return the restoration error.
- Do not restore after strip or other finalization failures.
- Do not handle the empty-suffix same-path case; that remains with the shared backup-suffix fix.

## Focused tests staged

1. restore destination and remove transient backup under simple mode
2. same under existing mode
3. same under numbered mode
4. multi-source simple mode preserves the original backup for the later successful source
5. seeded existing mode preserves the old numbered backup and removes the transient new backup
6. complete install integration module
7. formatting and focused clippy

## GNU 9.7 reference boundary

Using `source/file -> /proc/self/mem`:

- no backup: partial destination remains
- simple/existing/numbered: original destination restored; transient backup removed
- seeded existing: original restored; older numbered backup preserved; transient next backup removed
- preexisting simple backup: current destination restored; older backup entry removed
- multi-source simple: later source installs; backup contains original destination
- failing strip: no rollback; original remains at backup name and destination is removed

See `GNU_BEHAVIOR_RECEIPT.md` for the exact matrix and limits.

## Review state

At last refresh:

- `teamleaderleo/coreutils#3`: no comments, no submitted reviews, no requested reviewers
- `teamleaderleo/linux-fieldwork#431`: no comments, no submitted reviews

No matching open issue or PR was found with the searched rollback wording. This is not authority to contact upstream.

## First incomplete step

Inspect run `30799467577` when it leaves queued state.

If failure occurs:

1. fetch exact steps/logs;
2. classify transformer-anchor failure separately from Rust compile/test/lint failure;
3. repair only the first owner;
4. preserve the GNU behavior matrix unchanged.

If green promotion occurs:

1. refresh candidate head;
2. confirm temporary transformer/workflow were deleted;
3. list and inspect every final changed file;
4. verify PR #3 remains clean against the canonical-base branch;
5. compare with current canonical main and restack if required;
6. update README/HANDOFF with exact run, job, source commit, blobs, and final evidence boundary;
7. keep drafts and make no canonical-upstream contact without explicit authorization.

## Authority

Canonical-upstream contact: `false`.

No upstream issue, PR, comment, review, email, or patch submission was authorized or made.
