# uutils `install`: just-created destination ownership

## TL;DR

uutils `install -t` needs per-invocation destination ownership so a later source cannot overwrite a file created earlier in the same command, except when numbered backups deliberately make each prior version recoverable. Behavioral comparison against GNU `install` refined the ownership boundary: a compare no-op and a pre-copy failure do not claim the name; successful data creation does claim it before chown/chmod/SELinux/verbose finalization; a failed strip releases it only when the destination was removed.

The controlled fork candidate is under active verification. A self-review replaced a duplicated copy pipeline with a callback at the single existing copy lifecycle boundary.

## Explain like I'm five

Two different source files can both be named `file`. Running `install -t dest source1/file source2/file` sends both to `dest/file`. The first copy creates `dest/file`; the second must not silently replace it. The candidate remembers that `dest/file` was made by this command and refuses the second overwrite unless numbered backups were requested.

## Why care

Without this guard, the second source silently wins. With simple or existing backups, the command can also replace the backup of the pre-command destination with the first source, losing the original destination contents.

## Current state

- State: `REVIEW`
- Exact working head: `teamleaderleo/coreutils@1b10a9d56abd5fdd5298b8e34ad3bc377a53a0fe`
- Source base: `uutils/coreutils@b13ee7a8319f439cb9a1ba550e98de665f9c4bb1`
- Controlled branch: `fieldwork/install-refuse-just-created-overwrite-12926`
- Controlled draft PR: `teamleaderleo/coreutils#1`
- Latest authoritative gate: refinement PR run `30797670965`, queued at this checkpoint
- First incomplete step: complete the refinement verifier and inspect every focused test, full install-module test, formatting, and clippy result
- Cleanup state: branch temporarily contains `.fieldwork/refine-install-12926.patch` and `.github/workflows/fieldwork-refine-install-12926.yml`; the push verifier removes both after a green promotion
- Next safe action: inspect run `30797670965`; if green, confirm the push-side promotion produced a source/test-only head and then re-review the final diff
- External-contact state: no canonical-upstream issue comment, PR, review, or other contact authorized or made

## Intent and precedent

`cp`, `mv`, and `ln` already maintain per-invocation destination state and generally refuse overwriting a file created earlier by the same command. Numbered backups are the exception because every displaced version receives a new backup name.

`install` has a distinct post-copy phase: strip, ownership, permissions, timestamps, SELinux handling, and verbose output can fail after the destination data already exists. Therefore generic `Result::Ok` is not the correct ownership boundary.

An active upstream PR, `uutils/coreutils#12063`, is separately moving post-copy finalization onto the created file descriptor. The current candidate deliberately centralizes its creation callback in the existing copy pipeline so it can rebase onto that work without duplicating the lifecycle.

## Question

At what exact point should multi-source `install` treat a destination as created by the current invocation, and when should that ownership be released?

## Source

- Project: uutils/coreutils
- Requested revision: current controlled fork based on canonical `main`
- Resolved base commit: `b13ee7a8319f439cb9a1ba550e98de665f9c4bb1`
- Current controlled head: `1b10a9d56abd5fdd5298b8e34ad3bc377a53a0fe`
- Candidate source commit: pending verifier promotion
- Local source path: GitHub-controlled fork `teamleaderleo/coreutils`
- Import metadata: not imported into `linux-fieldwork/upstream/`; exact Git identities above are the source boundary

## Environment

- Hosted execution: GitHub Actions `ubuntu-latest`
- Refinement runner observed: Ubuntu 24.04.4, x86_64
- Rust toolchain observed: Rust 1.97.1
- Shell: GitHub Actions bash
- Privileges: ordinary hosted runner user; the chown-failure test skips when effective UID is 0
- Reference behavior: GNU `install` 9.7 behavioral probes

## Baseline behavior

With two sources sharing a basename, uutils copies both into the same destination and the second can replace the first. Under simple/existing backup modes, the second operation can also rotate the first source into the backup name, replacing the original destination backup.

## Hypothesis or candidate

Maintain a `HashSet<PathBuf>` of destinations created by the current multi-source invocation.

Before each copy, reject a destination already in that set unless backup mode is numbered. The single copy pipeline invokes an `on_created` callback immediately after `copy_file()` succeeds and before finalization. The multi-source caller inserts the destination in that callback. If finalization fails and `symlink_metadata()` reports that no directory entry remains, remove it from the set.

The candidate deliberately does not broaden into fd-bound finalization, special-file target handling, directory merging, or recursive traversal work.

## Reproduction

Representative matrix:

```sh
# ordinary collision: reject second source
install -t dest source1/file source2/file

# simple/existing backup: reject second source and preserve original backup
install --backup=simple -t dest source1/file source2/file

# numbered backup: permit both and retain each prior version
install --backup=numbered -t dest source1/file source2/file

# compare no-op: first source does not reserve; second source installs
install --compare -t dest source1/file source2/file

# pre-copy failure: missing first source does not reserve
install -t dest missing/file source2/file

# post-copy chown failure: created file remains reserved
install --owner=root -t dest source1/file source2/file

# strip failure removes each destination, so the second source is attempted
install --strip --strip-program ./strip-fails -t dest source1/file source2/file
```

## Results

Original focused verifier run `30752473403`, job `91508843610`, passed:

- clean application of the original candidate;
- formatting;
- ordinary repeated-destination refusal;
- preservation of the original simple backup;
- numbered-backup exception.

Refinement run `30759417796`, job `91527159381`, failed before compilation because the staged patch had incorrect unified-diff hunk counts (`corrupt patch ...:67`). This was classified as a fieldwork packaging failure, not a product-code result.

The patch metadata was repaired at `918868219a994fcc5fc267e8527a1fa3754aba82`. Self-review then found and removed lifecycle duplication, producing current head `1b10a9d56abd5fdd5298b8e34ad3bc377a53a0fe` and refinement run `30797670965`.

Review activity at this checkpoint:

- draft PR comments: none;
- submitted reviews: none;
- requested reviewers: none.

## Interpretation

Observed GNU behavior establishes that ownership is tied to actual destination creation, not generic function success:

- compare no-op: no ownership;
- pre-copy failure: no ownership;
- data copy succeeds: ownership begins;
- post-copy failure leaving the file: ownership remains;
- strip failure removing the file: ownership ends;
- numbered backups: repeated destinations remain valid.

The callback design keeps this transition in one copy pipeline and avoids creating a second implementation of compare, backup, copy, and finalization semantics.

## Evidence boundary

The full refinement matrix has not yet received a green receipt at this checkpoint. Windows, macOS, BSD, Android, SELinux-enabled execution, and privileged-root behavior are not independently demonstrated here. The candidate is based on path-presence cleanup until the separate fd-finalization work lands. No claim is made that the broader inherited fork CI fan-out is green.

## Next step

Inspect refinement run `30797670965`. On success, confirm the push verifier promoted the source and removed temporary fieldwork files. Then compare the final branch against the exact base, inspect all changed files, update this record with the final source commit and receipts, and leave the fork PR draft unless explicit upstream authorization is given.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other interaction has been authorized or made. The only PR is draft `teamleaderleo/coreutils#1` inside the controlled fork.
