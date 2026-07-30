# LF-23 temporary output-root guard

## In simple words

The LF-23 cancellation harness recursively replaces its selected output directory. It used Python's dynamic temporary directory as an allowed cleanup root. When `TMPDIR` points into the checkout, or the runtime has no system temporary directory and Python falls back to the checkout, a repository child becomes eligible for recursive deletion.

This repair limits disposable output roots to the harness artifact directory, `/tmp`, and `/var/tmp`. Composed symlink regressions prove neither the final output component nor an ancestor below an allowed root can grant cleanup authority over a target elsewhere.

## Source boundary

- Candidate current-main parent: `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145`.
- Reviewed safety predecessor: `b1e8aa4e9376e41962e456467c2f3fdcb38cae17`.
- Predecessor hosted gate: Linux Fieldwork CI run `30578704079` / run 564.
- First independently green symlink proof: `556c15c67b2978a1eae635a27f4b69986b4dc0e2`, run `30579993408` / run 596.
- Concurrent expanded proof source: `65ddf0fce71d46b7851c599a358a52a8cc3c279b`.
- Harness: `programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/scouts/LF-SCOUT-PROC-01/artifacts/cancellation_harness.py`.
- Direct regression: `tests/test_lf23_cancellation_harness_safety.py`.
- Symlink regression: `tests/test_lf23_cancellation_harness_symlink_safety.py`.
- Symlink review record: `../lf-23-cancellation-harness-symlink-safety/README.md`.
- Initial worker: Helper I; composed cross-review: H.

The exact composed head and its rerun belong in PR #199's current receipt because updating this record itself advances the branch.

## Reproduction

The full repository test run executed in a runtime where `/tmp` was absent between sandbox commands. `tempfile.gettempdir()` resolved to the checkout. The existing preservation test then passed a repository child to the harness; the guard accepted it, recursively deleted the directory and sentinel, and continued into the cancellation matrix.

The direct focused regression explicitly sets `TMPDIR` to the repository root in the harness subprocess. The selected repository child must be rejected with `output must be a child`, and its sentinel must remain byte-identical.

The composed symlink regression creates sentinel-bearing checkout targets and exercises two requests below writable `/tmp` or `/var/tmp`:

1. the requested output itself is a symlink to the outside target;
2. an ancestor of the requested output is a symlink to the outside target.

Resolution must expose the outside target before authorization, reject both requests, preserve both sentinels and links, and create no output directory in the outside target.

## Validation

Pre-composition receipts:

```text
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_lf23_cancellation_harness_safety
Ran 2 tests
OK

env PYTHONDONTWRITEBYTECODE=1 python3 -O -m unittest tests.test_lf23_cancellation_harness_safety
Ran 2 tests
OK

Linux Fieldwork CI run 30578704079 / run 564
SUCCESS at b1e8aa4e9376e41962e456467c2f3fdcb38cae17

Linux Fieldwork CI run 30579993408 / run 596
SUCCESS for the first two-file symlink proof at 556c15c67b2978a1eae635a27f4b69986b4dc0e2
```

The canonical composed head must rerun Linux Fieldwork CI after the final and ancestor-symlink transfer.

## Complete-diff review

The product repair removes the dynamic `tempfile.gettempdir()` cleanup authority, removes the now-unused import, adds explicit `/tmp` and `/var/tmp` roots, and makes the repository-temp regression stable by setting `TMPDIR` in the child process. The imported mmdebstrap source and cancellation mechanism are unchanged.

The added cross-review changes proof surfaces only. It exercises final and ancestor symlink resolution without widening the cleanup allowlist.

## Cleanup and rerun

Rejected direct and symlink outputs retain their sentinels. Final and ancestor links remain present, and the outside targets gain no output directory. Test-created roots are disposable, and Python caches are excluded from the exact gate.

## Disposition

`RERUN COMPOSED HEAD, THEN MERGE LOCALLY`

This is a bounded harness-safety correction with both symlink escape proofs composed into one canonical carrier.

## Evidence limits

- The output path is resolved before the descendant check.
- The harness artifact directory remains an intentional repository-local output authority.
- Custom temporary roots outside `/tmp` and `/var/tmp` must use the harness artifact directory or receive a separately reviewed allowlist.
- Same-UID mutation after validation remains outside the focused regression.

## External-contact state

No upstream contact was made or authorized.
