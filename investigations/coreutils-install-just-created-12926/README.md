# uutils `install`: just-created destination ownership

## TL;DR

uutils `install -t` needs per-invocation destination ownership so a later source cannot overwrite a file completed earlier in the same command. GNU `install` 9.7 shows that the boundary is successful completion of the data-copy operation: compare no-ops, source metadata failures, and incomplete copies do not claim the destination; completed copies claim it before later finalization; failed strip releases it only when the destination was removed. Only explicit numbered-backup mode permits repeated use.

The controlled source candidate is complete and source-only at `teamleaderleo/coreutils@b6f6e76138b27fd7a221a551aa6261752d513f19`. The exact ownership matrix, complete `install` test module, formatting, and focused clippy passed. Canonical upstream contact remains unauthorized.

## Explain like I'm five

Two source files can both be named `file`. Running `install -t dest source1/file source2/file` sends both to `dest/file`. Once the first file has been copied completely, the command should remember that it made `dest/file` and refuse to silently replace it with the second source. If the first copy never finishes, the second source may still try.

## Why care

Without this guard, the second source silently wins. With simple or existing backups, the second operation can also replace the backup of the pre-command destination with the first source, losing the original destination contents.

## State and exact identities

- State: `ACCEPT SOURCE / PUBLIC CONTACT UNAUTHORIZED`
- Controlled repository: `teamleaderleo/coreutils`
- Controlled branch: `fieldwork/install-refuse-just-created-overwrite-12926`
- Controlled source PR: `teamleaderleo/coreutils#1`
- Historical candidate base: `uutils/coreutils@b13ee7a8319f439cb9a1ba550e98de665f9c4bb1`
- Accepted source-only head: `teamleaderleo/coreutils@b6f6e76138b27fd7a221a551aa6261752d513f19`
- Current canonical main at overlap refresh: `uutils/coreutils@21d4e9635b07a04f262cd8a5386f2987bca6cfef`
- Linux Fieldwork branch: `investigate/coreutils-install-just-created-12926`
- Linux Fieldwork PR: `teamleaderleo/linux-fieldwork#430`
- Canonical upstream interaction: none

The final source candidate changes exactly:

- `src/uu/install/src/install.rs`;
- `src/uu/install/locales/en-US.ftl`;
- `src/uu/install/locales/fr-FR.ftl`;
- `tests/by-util/test_install.rs`.

The temporary refinement patch and controlled promotion workflow were removed by the source-only promotion commit.

## Intent and precedent

`cp`, `mv`, and `ln` maintain per-invocation destination state and generally refuse overwriting a file created earlier by the same command. The exception is explicit numbered-backup mode. A GNU negative control showed that `--backup=existing` still refuses the second source even when a preexisting numbered backup causes the first backup name to be numbered.

`install` has a distinct post-copy phase: strip, ownership, permissions, timestamps, SELinux handling, and verbose output can fail after destination data already exists. Generic function success is therefore not the ownership boundary.

Upstream PR `uutils/coreutils#12063` separately addresses fd-bound post-copy finalization. The selected candidate keeps one copy lifecycle and can be restacked without duplicating compare, backup, copy, and finalization behavior.

## Accepted candidate

Maintain a `HashSet<PathBuf>` of destinations completed by the current multi-source invocation.

Before each copy, reject a destination already in that set unless backup mode is explicitly numbered. The existing copy pipeline invokes an `on_created` callback immediately after `copy_file()` completes and before finalization. The multi-source caller inserts the destination in that callback.

If later finalization fails and `symlink_metadata()` reports no directory entry, remove the destination from the set. This releases the name after failed strip cleanup while retaining ownership after failures that leave the completed file present.

The candidate deliberately leaves fd-bound finalization, recursive traversal, special-file behavior, backup rollback, and unrelated `install` defects to separate owners.

## GNU 9.7 reference matrix

See [`GNU_BEHAVIOR_RECEIPT.md`](GNU_BEHAVIOR_RECEIPT.md) for commands and compact output.

Established behavior:

- ordinary repeated basename: first completed copy owns the destination and the second is refused;
- simple backup: the original destination remains under the backup name and the second is refused;
- numbered backup: both source copies are permitted and backups advance;
- true `--compare` no-op: no ownership is acquired;
- missing source: no ownership is acquired;
- source read error after destination creation: no ownership is acquired;
- successful data copy followed by chown failure: ownership remains;
- strip failure removes the destination and releases the name.

## Exact execution

### Independent final candidate gate

Linux Fieldwork workflow `30849357346`, job `91805346376`, passed against controlled staged head `2b1d87f06c0cff40a9002c3d2243f8a12248f787`:

- exact controlled checkout;
- retained zero-fuzz patch application;
- repository rustfmt transformation and check;
- all eight ownership boundary tests;
- complete `install` test module;
- focused clippy;
- exact candidate diff recording.

The controlled promotion then committed the tested formatted bytes and removed only the temporary patch and workflow, producing source-only head `b6f6e761...`.

### Direct source-only confirmation

The Linux Fieldwork verifier now checks out `b6f6e761...` directly, proves the exact four-file fence and absence of execution machinery, and reruns formatting, all eight focused tests, the complete module, clippy, identity, hygiene, and clean-tree checks.

That direct confirmation is the final landing gate for this record.

## Complete-diff review

Owned source review `4856820032` accepts the source-only exact head.

The callback placement matches the behavioral boundary: ownership begins after successful data-copy completion, not after destination creation and not after all finalization succeeds. Release is limited to failure paths where the destination entry is absent.

## Current-main overlap

Canonical main `21d4e963...` is 32 commits ahead of the historical base. The changed-file range contains no `install` source, locale, or `test_install.rs` path.

The candidate therefore has no current source overlap at this refresh. A clean restack and rerun remain mandatory immediately before any authorized canonical filing because the source branch still targets a historical base.

## Adjacent operation owner

Backup rollback after `copy_file()` failure is separate and remains tracked by:

- controlled source PR `teamleaderleo/coreutils#3`;
- Linux Fieldwork PR `teamleaderleo/linux-fieldwork#431`.

This ownership candidate does not restore a pre-copy backup after data-copy failure.

## Evidence limits

- GNU behavior was measured on Linux with GNU coreutils 9.7;
- `/proc/self/mem` provides a source-side read failure, not a destination-side ENOSPC control;
- the chown control skips when the runner is root;
- macOS, BSD, Android, SELinux-enabled finalization, and privileged-root behavior are not independently demonstrated;
- path-based cleanup remains subject to the separate fd-bound finalization work;
- inherited fork workflow fan-out marked `action_required` is not treated as test evidence.

## Next transition

After the direct source-only verifier and Linux Fieldwork CI pass unchanged:

1. mark Linux Fieldwork #430 ready and compose the durable record;
2. keep controlled source PR #1 open for human review;
3. immediately before any authorized canonical filing, restack onto current public main, repeat overlap and contribution-policy checks, and rerun the exact source gates;
4. obtain explicit authorization for the public interaction.

No canonical-upstream issue, pull request, comment, review, reaction, email, release, deployment, or patch submission has been authorized or made.
