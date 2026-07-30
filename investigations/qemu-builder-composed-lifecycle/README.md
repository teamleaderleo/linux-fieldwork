# QEMU builder composed image lifecycle

## In simple words

The QEMU image builder had two overlapping lifecycle candidates: one made signal traps terminate with signal-derived status, and one kept image construction private until a final rename. This investigation composes both mechanisms against current `main` and tests the combined ownership, cleanup, publication, signal, rerun, and path-interpretation contract.

The integration candidate is the final-check unit. The focused records in PR #172 and PR #192 remain useful mechanism histories.

## Canonical records

- Integration issue: #193
- Signal issue and focused candidate: #170 / PR #172
- Atomic-publication issue and focused candidate: #191 / PR #192
- Candidate branch: `integrate/qemu-builder-composed-lifecycle`
- Initial current-main base: `d344c942af4b55b5b0c71c8a66a8870fbf0db7bf`
- Imported source: `upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu`
- Composed patch: `0001-compose-image-publication-and-signal-lifecycle.patch`
- Core regression: `tests/test_qemu_builder_composed_lifecycle.py`
- Path regression: `tests/test_qemu_builder_composed_lifecycle_paths.py`

## Composed source contract

The candidate:

1. rejects a trailing-slash image argument before path reinterpretation or private-image creation;
2. resolves the final image parent and creates a private sibling directory on the same filesystem;
3. refuses a literal root parent or a parent symlink resolving to `/` before private-image creation or image mutation;
4. sends `mke2fs`, `truncate`, `sfdisk`, and `dd` to the private image path;
5. publishes with exactly one `mv --no-target-directory` after all image mutations;
6. clears private-image ownership after publication so later cleanup cannot delete the final image;
7. gives HUP, INT, QUIT, and TERM terminating actions with statuses 129, 130, 131, and 143;
8. clears all traps before signal cleanup so EXIT cannot run cleanup a second time;
9. aggregates cleanup failures while attempting both `WORKDIR` and private-image cleanup;
10. preserves a primary ordinary failure or signal status over cleanup failure;
11. reports cleanup failure when an otherwise successful exit has no stronger status.

## Review repair: trailing-slash image paths

The first composed head validated the basename only after GNU `dirname` and `basename` processed the argument. For an existing directory supplied as `path/to/output/`, those utilities produced parent `path/to/output` and basename `output`, silently changing the requested destination into `path/to/output/output`.

The repaired candidate checks the original argument for a trailing slash first. The focused negative control supplies an existing directory with a trailing slash and requires status 1, a focused diagnostic, zero `mktemp` calls, and no nested output path.

## Regression matrix

The regressions apply the composed patch to exact temporary copies of the imported source and check the complete candidate with `sh -n`. They extract the exact candidate functions into reduced real `/bin/sh` harnesses and prove:

- existing final image plus ordinary failure: status 42, sentinel bytes and mode preserved, private state removed, cleanup called once;
- absent final image plus ordinary failure: output remains absent and private state is removed;
- wrapper-only HUP, INT, and TERM before publication: status 129, 130, and 143, later marker absent, existing final preserved, cleanup called once;
- immediate successful rerun after each signal: complete bytes published and temporary state removed;
- successful publication: complete bytes replace the sentinel through one rename, mode is 0644 under umask 022, status 0;
- TERM after publication: status 143 while the published final image remains intact;
- cleanup failure precedence: cleanup failure becomes status 74 after otherwise successful exit, while ordinary failure 42 and TERM 143 remain authoritative;
- literal root and symlink-to-root parents: refusal before private-image creation;
- existing directory with trailing slash: refusal before `mktemp`, with no nested destination created;
- source assertions: every image mutator uses `IMAGE_TMP`, one publication precedes the success message, and EXIT/HUP/INT/QUIT/TERM actions are distinct.

The lifecycle test instruments the exact cleanup body with a thin call counter. The body itself remains unchanged in the harness.

## Executed gate history

The initial construction command was:

```text
python -m unittest -v tests/test_qemu_builder_composed_lifecycle.py
```

It passed seven tests. Linux Fieldwork CI run `30577530343` also passed on initial head `dec8133d1e90de51dae603bc2b195ed1ae32b0ac`.

That green head preceded the trailing-slash review repair. Exact-head CI after the repair is the authoritative final gate.

## Cleanup and rerun result

Ordinary failure and every signal case remove the work directory and active private image state once. The same final image pathname succeeds on the immediate next run. Post-publication signals leave the completed final image intact.

Injected cleanup failure intentionally leaves disposable harness residue. The test records one cleanup call and then lets its enclosing temporary directory remove the fixture. The trailing-slash negative control creates no private image state.

## Composition and overlap decision

PR #172 and PR #192 overlap mechanically in the `WORKDIR`/cleanup/trap block. Neither focused patch is the final landing unit by itself. This generated patch is the explicit composition order and carries the combined gate.

The integration adds HUP handling and explicit ordinary-exit cleanup precedence. It also follows issue #193's stricter root-parent refusal, superseding PR #192's earlier root-parent compatibility choice for the integrated candidate.

## Evidence boundary

This work establishes pathname publication, input-path interpretation, wrapper status, cleanup ownership, and immediate rerun behavior with small files and real shell signal delivery. It does not run `mmdebstrap`, `mke2fs`, partition tools, QEMU, mounts, root operations, or a multi-gigabyte image.

The candidate still leaves these boundaries:

- parent-only signals may be deferred while the shell waits for a foreground child;
- signals are not forwarded to foreground tools;
- publication has rename atomicity without file or directory `fsync` durability;
- concurrent publishers are not locked;
- final image contents are not validated;
- replacement does not preserve metadata from an existing inode;
- unexpected post-publication residue is retained with a warning.

## Authority

Internal Linux Fieldwork work only. No Debian or other external issue, email, patch, merge request, comment, or review is authorized or included.

## Disposition

Run exact-head CI and complete-diff review after the trailing-slash repair. If green, merge the integration carrier locally and retain PR #172 and PR #192 as focused mechanism records.