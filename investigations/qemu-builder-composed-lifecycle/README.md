# QEMU builder composed image lifecycle

## TL;DR

The QEMU image builder now creates its disk image under a private sibling directory, publishes it with one final rename, and exits with the correct signal-derived status after cleanup. The combined candidate landed on `main` through PR #195 as commit `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145`.

The retained regressions prove existing-output preservation, one-time cleanup, HUP/INT/QUIT/TERM results, post-publication safety, cleanup-error precedence, trailing-slash rejection, and immediate reruns. A heavier builder run with real image tools remains a separate integration step.

## Explain like I'm five

Imagine building a model airplane for someone who already has a finished airplane on the shelf. The old script started cutting up the shelf airplane while the new one was still being assembled. It could also hear “stop,” tidy the table, and then keep building.

The landed version builds the new airplane in a private box. Failure or cancellation throws away only that box. Success moves the finished airplane onto the shelf in one step. A stop signal ends the job with the expected status.

## Why care

A failed or cancelled image build could previously leave a partial file at the trusted output name, damage an older valid image, continue after cleanup, or report success. Automated callers could then mistake an interrupted build for a usable virtual-machine image.

The landed lifecycle gives the output name one clear publication point and gives cancellation one clear terminal result.

## Canonical records

- Integration issue: #193
- Landed integration: PR #195
- Landed commit: `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145`
- Final reviewed source head: `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154`
- Signal mechanism history: issue #170 / PR #172
- Atomic-publication mechanism history: issue #191 / PR #192
- Imported source: `upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu`
- Composed patch: `0001-compose-image-publication-and-signal-lifecycle.patch`
- Core regression: `tests/test_qemu_builder_composed_lifecycle.py`
- Path regression: `tests/test_qemu_builder_composed_lifecycle_paths.py`

## Observed defect

The imported helper used the caller-selected final `IMAGE` throughout construction. `mke2fs` created or replaced that path before EFI assembly, partition-table work, and the final FAT copy completed. A later failure therefore left the trusted output name pointing at partial work.

The same helper installed one cleanup-only action for ordinary exit and for `INT`, `TERM`, and `QUIT`. A parent-only signal delivered while the shell waited for foreground work could be handled after that work returned. Cleanup removed temporary files, returned, and allowed later commands to continue.

A review pass found a third path-interpretation defect in the first combined candidate: an existing directory argument ending in `/` could be reinterpreted by `dirname` and `basename` as a nested output path.

## Source intent and design choice

The source clearly treats the final success message as the point where callers should receive a usable image, yet the old pathname became visible much earlier. No retained upstream statement defines partial-image publication as desired behavior.

The landed design chooses:

1. private same-filesystem construction;
2. one final rename as the publication point;
3. separate ordinary-exit and signal paths;
4. primary failure or signal status ahead of cleanup failure;
5. cleanup failure as the terminal status after an otherwise successful exit;
6. rejection of ambiguous trailing-slash and filesystem-root destinations before private-image creation.

These choices keep the change within output ownership, cancellation, and cleanup. Foreground-child forwarding, crash durability, concurrent-publisher locking, and image validation remain separate questions.

## Landed source contract

The landed patch:

1. rejects an image argument ending in `/` before path reinterpretation;
2. resolves the final parent and creates a private sibling directory on the same filesystem;
3. refuses a parent resolving to `/` before image creation;
4. sends `mke2fs`, `truncate`, `sfdisk`, and `dd` to `IMAGE_TMP`;
5. publishes with one `mv --no-target-directory` after every image mutation;
6. clears temporary-image ownership after publication;
7. handles HUP, INT, QUIT, and TERM as 129, 130, 131, and 143;
8. clears traps before signal cleanup, preventing a second EXIT cleanup;
9. attempts both work-directory and private-image cleanup;
10. preserves ordinary failure and signal status over cleanup errors;
11. returns cleanup failure after an otherwise successful exit.

## Regression matrix

The regressions apply the retained patch to exact temporary copies of the imported source and run `sh -n` on the complete candidate. Reduced real `/bin/sh` harnesses prove:

- existing final image plus ordinary failure: status 42, original bytes and mode preserved, private state removed, cleanup called once;
- absent final image plus ordinary failure: output remains absent and private state is removed;
- wrapper-only HUP, INT, and TERM before publication: status 129, 130, and 143, later work omitted, existing final preserved, cleanup called once;
- immediate successful rerun after each signal: complete bytes published and temporary state removed;
- successful publication: complete bytes replace the sentinel through one rename, mode 0644 under umask 022, status 0;
- TERM after publication: status 143 with the published image intact;
- cleanup failure precedence: status 74 after otherwise successful exit, while failure 42 and TERM 143 remain authoritative;
- literal root and symlink-to-root parents: refusal before private-image creation;
- existing directory with trailing slash: refusal before `mktemp`, with zero nested output;
- source contract: every image mutator uses `IMAGE_TMP`, one publication precedes success, and EXIT/HUP/INT/QUIT/TERM actions are distinct.

The lifecycle harness wraps the exact cleanup body with a call counter. The body itself remains unchanged.

## Executed evidence

Initial lifecycle head `dec8133d1e90de51dae603bc2b195ed1ae32b0ac` passed seven focused tests and Linux Fieldwork CI run `30577530343`.

Complete-diff review then found the trailing-slash reinterpretation. Final source head `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154` added the negative control and repair. Linux Fieldwork CI run `30578489526` passed; job `90992563661` completed Python compilation, the complete repository unit suite, shell syntax, and command-help checks. PR #195 merged as `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145`.

Evidence classification:

- source ownership and command routing: demonstrated by source inspection and exact patch assertions;
- lifecycle, signal, cleanup, publication, mode, path, and rerun behavior: demonstrated by reduced real-shell models;
- repository regression compatibility: demonstrated by the named Linux Fieldwork CI gate;
- full QEMU image construction: open integration boundary.

## Cleanup and rerun result

Ordinary failure and every pre-publication signal remove the work directory and active private image state once. The same output path succeeds on the immediate next run. Signals after publication leave the completed final image intact.

Injected cleanup failure intentionally leaves disposable harness residue for the enclosing temporary directory to remove. The trailing-slash control creates zero private image state.

## Composition decision

PR #172 and PR #192 changed the same `WORKDIR`, cleanup, and trap region. Their separate patches remain useful mechanism histories. PR #195 is the canonical combined source and the landed result.

The combined result adds HUP handling, ordinary-exit cleanup precedence, final-output preservation, path validation, and signal behavior before and after publication. The earlier focused root-parent compatibility choice from PR #192 was superseded by the stricter combined refusal in issue #193.

## Evidence boundary

The retained tests use small files and real shell signals. They skip `mmdebstrap`, `mke2fs`, partition tools, QEMU, mounts, root operations, and multi-gigabyte images.

Open boundaries:

- parent-only signals may wait until a foreground child returns;
- foreground tools receive no forwarded signal from this wrapper;
- rename atomicity includes no file or directory `fsync` guarantee;
- concurrent publishers have no lock;
- final image contents receive no validation step;
- replacement creates a new inode and carries no prior mode, ownership, ACL, or xattr promise;
- unexpected post-publication residue is retained with a warning.

## Authority

Internal Linux Fieldwork work only. External Debian or upstream contact remains unauthorized for this result.

## Disposition

**MERGED LOCALLY.** Use PR #195 and landed commit `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145` as the canonical result. Retain PR #172 and PR #192 as focused mechanism history.