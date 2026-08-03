# uutils `install`: just-created destination ownership

## TL;DR

uutils `install -t` needs per-invocation destination ownership so a later source cannot overwrite a file completed earlier in the same command. GNU `install` 9.7 shows that the boundary is successful completion of the data-copy operation: compare no-ops, stat failures, and source read failures do not claim the destination; completed copies do claim it before chown/chmod/SELinux/verbose finalization; failed strip releases it only when the destination was removed. Only explicit numbered-backup mode permits repeated use.

The controlled fork candidate is staged and under two hosted gates. Self-review repaired the patch carrier, replaced a duplicated lifecycle with one creation callback in the existing copy pipeline, and added a copy-error negative control.

## Explain like I'm five

Two source files can both be named `file`. Running `install -t dest source1/file source2/file` sends both to `dest/file`. Once the first file has been copied completely, the command should remember that it made `dest/file` and refuse to silently replace it with the second source. If the first copy never finishes, the second source may still try.

## Why care

Without this guard, the second source silently wins. With simple or existing backups, the command can also replace the backup of the pre-command destination with the first source, losing the original destination contents.

## Current state

- State: `REVIEW`
- Exact controlled-fork head: `teamleaderleo/coreutils@8b41c8e08dcb7db59da348279ed4cfb58efc4282`
- Controlled source base: `uutils/coreutils@b13ee7a8319f439cb9a1ba550e98de665f9c4bb1`
- Controlled source branch: `fieldwork/install-refuse-just-created-overwrite-12926`
- Controlled source draft: `teamleaderleo/coreutils#1`
- Exact Linux Fieldwork head at this update: `teamleaderleo/linux-fieldwork@23388b617c6e90755bc233968ea547d06e94a741`
- Linux Fieldwork draft: `teamleaderleo/linux-fieldwork#430`
- Fork gate: run `30798087273`, queued at this checkpoint
- Independent read-only gate: run `30798287125`, queued at this checkpoint
- First incomplete step: execute formatting, eight focused ownership tests, the complete install test module, and focused clippy
- Cleanup state: source branch temporarily contains `.fieldwork/refine-install-12926.patch` and `.github/workflows/fieldwork-refine-install-12926.yml`; promotion must remove both
- Next safe action: inspect the first completed gate, classify its first distinguishing failure owner, and change product code only if the failure reaches the candidate behavior
- External-contact state: no canonical-upstream issue comment, PR, review, or other contact authorized or made

## Intent and precedent

`cp`, `mv`, and `ln` maintain per-invocation destination state and generally refuse overwriting a file created earlier by the same command. The exception is explicit numbered-backup mode. A GNU negative control showed that `--backup=existing` still refuses the second source even when a preexisting numbered backup causes the first backup name to be numbered.

`install` has a distinct post-copy phase: strip, ownership, permissions, timestamps, SELinux handling, and verbose output can fail after destination data already exists. Generic `Result::Ok` is therefore not the ownership boundary.

Upstream PR `uutils/coreutils#12063` separately attempts to keep post-copy finalization bound to the created file descriptor. Its review history requested idiomatic platform APIs, formatting, and clippy. The current candidate keeps one copy lifecycle so it can be restacked onto that work without duplicating compare, backup, copy, and finalization behavior.

## Question

At what exact point should multi-source `install` treat a destination as created by the current invocation, and when should that ownership be released?

## Source

- Project: uutils/coreutils
- Resolved candidate base: `b13ee7a8319f439cb9a1ba550e98de665f9c4bb1`
- Current staged head: `8b41c8e08dcb7db59da348279ed4cfb58efc4282`
- Candidate source commit: pending verifier promotion
- Controlled repository: `teamleaderleo/coreutils`
- Imported tree: none; exact Git identities are the source boundary
- Canonical-main drift check: canonical `main` was four commits ahead, with no changed `install` source or test files in that range

## Environment

- Hosted execution: GitHub Actions `ubuntu-latest`
- Observed refinement runner: Ubuntu 24.04.4, x86_64
- Observed Rust toolchain: Rust 1.97.1
- Shell: GitHub Actions bash
- Privileges: ordinary hosted runner user; chown test skips if effective UID is 0
- Reference behavior: GNU `install` 9.7 in disposable local Linux fixtures

## Baseline behavior

With two sources sharing a basename, current uutils copies both into the same destination and the second replaces the first. Under simple/existing backup modes, the second operation can also rotate the first source into the backup name, replacing the original destination backup.

## Candidate

Maintain a `HashSet<PathBuf>` of destinations completed by the current multi-source invocation.

Before each copy, reject a destination already in that set unless backup mode is explicitly numbered. The existing copy pipeline invokes an `on_created` callback immediately after `copy_file()` completes and before finalization. The multi-source caller inserts the destination in that callback. If finalization fails and `symlink_metadata()` reports no directory entry, remove it from the set.

This deliberately leaves fd-bound finalization, special-file target handling, recursive traversal, and unrelated `install` defects to their own carriers.

## Reproduction

See [`GNU_BEHAVIOR_RECEIPT.md`](GNU_BEHAVIOR_RECEIPT.md) for the complete reference matrix and compact output.

```sh
# completed copy owns the name
install -t dest source1/file source2/file

# simple backup preserves original and refuses second
install --backup=simple -t dest source1/file source2/file

# explicit numbered mode permits repeated use
install --backup=numbered -t dest source1/file source2/file

# compare no-op does not claim the name
install --compare -t dest source1/file source2/file

# missing source does not claim the name
install -t dest missing/file source2/file

# read failure after destination open/create still does not claim the name
install -t dest source1/mem source2/mem  # source1/mem -> /proc/self/mem

# completed copy followed by chown failure keeps ownership
install --owner=root -t dest source1/file source2/file

# strip failure removes the destination and releases the name
install --strip --strip-program ./strip-fails -t dest source1/file source2/file
```

## Results

Original focused verifier run `30752473403`, job `91508843610`, passed clean patch application, formatting, ordinary refusal, original simple-backup preservation, and the explicit numbered-backup exception.

Refinement run `30759417796`, job `91527159381`, failed before compilation because the staged unified diff had incorrect hunk counts (`corrupt patch ...:67`). This was a fieldwork packaging failure, not a product result.

Patch metadata was repaired at `918868219a994fcc5fc267e8527a1fa3754aba82`. Self-review then found lifecycle duplication and replaced it with a callback at the single copy pipeline. GNU read-error probing added another discriminator, resulting in current staged head `8b41c8e08dcb7db59da348279ed4cfb58efc4282`.

Reference matrix results are retained in `GNU_BEHAVIOR_RECEIPT.md`. Notable findings:

- `/proc/self/mem` read failure leaves the later source able to install;
- non-root `--owner=root` produces an ownership error followed by just-created refusal;
- failing strip helper is invoked twice and leaves no destination;
- `--backup=existing` remains a refusal mode even when an older numbered backup exists.

Review activity at this checkpoint:

- controlled source PR comments: none;
- controlled source submitted reviews: none;
- requested reviewers: none;
- overlapping upstream PR feedback: use idiomatic platform APIs and require both formatting and clippy.

## Interpretation

Ownership is tied to completed data copy, not generic destination existence and not generic function success:

- compare no-op: no ownership;
- stat failure: no ownership;
- copy/read failure: no ownership;
- `copy_file()` completes: ownership begins;
- later failure leaving entry: ownership remains;
- later failure removing entry: ownership ends;
- explicit numbered backups: collision refusal disabled.

The callback design preserves one owner for compare, backup, copy, and finalization transitions.

## Evidence boundary

The full refined candidate has not yet received a green receipt. Windows, macOS, BSD, Android, SELinux-enabled execution, privileged-root behavior, and write-side ENOSPC failure are not independently demonstrated. The cleanup check remains path-based until fd-bound finalization is resolved. No claim is made that the fork's inherited full CI fan-out is green.

## Next step

Inspect runs `30798087273` and `30798287125`. After a green result, confirm push-side promotion produced a source/test-only head, compare it against current canonical `main`, review every final changed file, update this record and a handoff with exact blobs and receipts, and keep both drafts unsubmitted to canonical upstream unless explicit authorization is given.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other interaction has been authorized or made. The controlled drafts are `teamleaderleo/coreutils#1` and `teamleaderleo/linux-fieldwork#430`.
