# LF-23 temporary output-root guard

## In simple words

The LF-23 cancellation harness recursively replaces its selected output directory. It used Python's dynamic temporary directory as an allowed cleanup root. When `TMPDIR` points into the checkout, or the runtime has no system temporary directory and Python falls back to the checkout, a repository child becomes eligible for recursive deletion.

This repair limits disposable output roots to the harness artifact directory, `/tmp`, and `/var/tmp`.

## Source boundary

- Current-main base: `a254657636ca92302610cd4af4bc294fafa62bbd`.
- Repair content: `83814a727fbd8601fb3915ff2ca40e070d48dbba`.
- Harness: `programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/scouts/LF-SCOUT-PROC-01/artifacts/cancellation_harness.py`.
- Regression: `tests/test_lf23_cancellation_harness_safety.py`.
- Worker: Helper I, during post-Packet-I adjacent review.

## Reproduction

The full repository test run executed in a runtime where `/tmp` was absent between sandbox commands. `tempfile.gettempdir()` resolved to the checkout. The existing preservation test then passed a repository child to the harness; the guard accepted it, recursively deleted the directory and sentinel, and continued into the cancellation matrix.

The focused regression now explicitly sets `TMPDIR` to the repository root in the harness subprocess. The selected repository child must be rejected with `output must be a child`, and its sentinel must remain byte-identical.

## Validation

```text
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_lf23_cancellation_harness_safety
Ran 2 tests
OK

env PYTHONDONTWRITEBYTECODE=1 python3 -O -m unittest tests.test_lf23_cancellation_harness_safety
Ran 2 tests
OK

python3 -m py_compile <harness> <regression>
PASS

git diff --check
PASS
```

## Complete-diff review

The repair removes the dynamic `tempfile.gettempdir()` cleanup authority, removes the now-unused import, adds explicit `/tmp` and `/var/tmp` roots, and makes the repository-temp regression stable by setting `TMPDIR` in the child process. The imported mmdebstrap source and cancellation mechanism are unchanged.

## Cleanup and rerun

The rejected output remains present with its sentinel. Test-created Python caches were removed. Normal and optimized focused suites reran successfully.

## Disposition

`MERGE LOCALLY`

This is a bounded harness-safety correction on current `main`.

## Evidence limits

- The output path is resolved before the descendant check.
- The harness artifact directory remains an intentional repository-local output authority.
- Custom temporary roots outside `/tmp` and `/var/tmp` must use the harness artifact directory or receive a separately reviewed allowlist.

## External-contact state

No upstream contact was made or authorized.
