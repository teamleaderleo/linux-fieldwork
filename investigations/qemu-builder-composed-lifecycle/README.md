# QEMU builder composed image lifecycle

## In simple words

The QEMU image builder had two overlapping lifecycle candidates: one made signal traps terminate with signal-derived status, and one kept image construction private until a final rename. This investigation composes both mechanisms against current `main` and tests the combined ownership, cleanup, publication, signal, and rerun contract.

The integration candidate is the final-check unit. The focused records in PR #172 and PR #192 remain useful mechanism histories.

## Canonical records

- Integration issue: #193
- Signal issue and focused candidate: #170 / PR #172
- Atomic-publication issue and focused candidate: #191 / PR #192
- Candidate branch: `integrate/qemu-builder-composed-lifecycle`
- Current-main base used to start the branch: `d344c942af4b55b5b0c71c8a66a8870fbf0db7bf`
- Imported source: `upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu`
- Composed patch: `0001-compose-image-publication-and-signal-lifecycle.patch`
- Regression: `tests/test_qemu_builder_composed_lifecycle.py`

## Composed source contract

The candidate:

1. resolves the final image parent and creates a private sibling directory on the same filesystem;
2. refuses a literal root parent or a parent symlink resolving to `/` before `mktemp` or image mutation;
3. sends `mke2fs`, `truncate`, `sfdisk`, and `dd` to the private image path;
4. publishes with exactly one `mv --no-target-directory` after all image mutations;
5. clears private-image ownership after publication so later cleanup cannot delete the final image;
6. gives HUP, INT, QUIT, and TERM terminating actions with statuses 129, 130, 131, and 143;
7. clears all traps before signal cleanup so EXIT cannot run cleanup a second time;
8. aggregates cleanup failures while attempting both `WORKDIR` and private-image cleanup;
9. preserves a primary ordinary failure or signal status over cleanup failure;
10. reports cleanup failure when an otherwise successful exit has no stronger status.

## Regression matrix

The regression applies the composed patch to an exact temporary copy of the imported source and checks the complete candidate with `sh -n`. It extracts the exact candidate functions into reduced real `/bin/sh` harnesses and proves:

- existing final image plus ordinary failure: status 42, sentinel bytes and mode preserved, private state removed, cleanup called once;
- absent final image plus ordinary failure: output remains absent and private state is removed;
- wrapper-only HUP, INT, and TERM before publication: status 129, 130, and 143, later marker absent, existing final preserved, cleanup called once;
- immediate successful rerun after each signal: complete bytes published and temporary state removed;
- successful publication: complete bytes replace the sentinel through one rename, mode is 0644 under umask 022, status 0;
- TERM after publication: status 143 while the published final image remains intact;
- cleanup failure precedence: cleanup failure becomes status 74 after otherwise successful exit, while ordinary failure 42 and TERM 143 remain authoritative;
- literal root and symlink-to-root parents: refusal before `mktemp`;
- source assertions: every image mutator uses `IMAGE_TMP`, one publication precedes the success message, and EXIT/HUP/INT/QUIT/TERM actions are distinct.

The test instruments the exact cleanup body with a thin call counter. The body itself remains unchanged in the harness.

## Executed local gate

Command:

```text
python -m unittest -v tests/test_qemu_builder_composed_lifecycle.py
```

Observed result during construction:

```text
Ran 7 tests in 2.712s

OK
```

This local construction gate used the exact current-main source regions touched by the patch. Repository CI is the authoritative complete-source and complete-suite gate for the branch head.

## Cleanup and rerun result

Ordinary failure and every signal case remove the work directory and active private image state once. The same final image pathname succeeds on the immediate next run. Post-publication signals leave the completed final image intact.

Injected cleanup failure intentionally leaves disposable harness residue. The test records one cleanup call and then lets its enclosing temporary directory remove the fixture.

## Composition and overlap decision

PR #172 and PR #192 overlap mechanically in the `WORKDIR`/cleanup/trap block. Neither focused patch is the final landing unit by itself. This generated patch is the explicit composition order and carries the combined gate.

The integration adds HUP handling and explicit ordinary-exit cleanup precedence. It also follows issue #193's stricter root-parent refusal, superseding PR #192's earlier root-parent compatibility choice for the integrated candidate.

## Evidence boundary

This work establishes pathname publication, wrapper status, cleanup ownership, and immediate rerun behavior with small files and real shell signal delivery. It does not run `mmdebstrap`, `mke2fs`, partition tools, QEMU, mounts, root operations, or a multi-gigabyte image.

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

Promote the integration branch as the final-check candidate after exact-head CI and complete-diff review. Keep PR #172 and PR #192 as focused mechanism records and route any landing decision through issue #193.
