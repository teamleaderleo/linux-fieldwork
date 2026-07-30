# Tarfilter regex candidate results

## Run 30548851623 — failed before candidate execution

- Reviewed branch head: `ac6d5eaa3900dc4b86348c4497e8d5e0ba684f12`.
- Pull-request merge checkout: `e510023980545709417c696945530a9daed2af6b`.
- Runner: Ubuntu 24.04.4, Python from the hosted image, GNU tar 1.35.
- Repository tests reached all predecessor tarfilter controls successfully.
- Four candidate test methods failed while applying `tarfilter-transform-regex-dialects.patch`.
- GNU patch diagnostic:

```text
patch: **** malformed patch at line 123:
@@ -150,7 +272,7 @@ class TransformAction(argparse.Action):
```

### Cause

The first hunk header declared 128 new lines while the hunk contained 118. Every later new-file line number was consequently ten lines too high.

### Correction

Commit `e7498db21e1499fd46540f6571e3a3268067a1a6` changes only retained patch metadata:

```text
@@ -120,6 +120,118
@@ -150,7 +262,7
@@ -174,7 +286,10
```

No translator or regression semantics changed. The next run owns the first actual GNU differential result.

## Current execution state

A new exact-head run must apply the corrected patch, then execute:

```sh
python3 -m unittest tests.test_tarfilter_transform_regex_candidate -v
python3 -m unittest discover -s tests -v
```

Retain every subsequent run below this entry, including parser or harness failures. No imported source or external system was changed by the failed run.

## Local Packet H review — live head repair

- Reviewed predecessor head: `beb4ff0c33722f78123da4d3c33d016bd7e9e83d`.
- Environment: Python 3.12.13, GNU tar 1.35, `LC_ALL=C`.
- Linux Fieldwork CI run `30562745367`, job `90939637733`, failed 100 of 103 discovered tests at the same generated-source `SyntaxError`; the failure was patch packaging, before candidate semantics.
- The retained regex tail hunk applied with fuzz to the occurrence-selector loop and inserted `_translate_pattern()` before an indented `number_text = ""`. Every candidate comparison then stopped at `IndentationError`.
- The retained edge patch also used one-line hunks that applied with fuzz inside incomplete statements, producing `SyntaxError`.
- After regenerating both patch boundaries around their exact predecessor source, the original matrix exposed a second product gap: extended middle-position `^` and `$` were translated as literals even though GNU tar keeps them active.
- A final differential control found that GNU tar rejects consecutive basic intervals while accepting the tested extended nested intervals. The candidate now rejects the proven basic form and retains broader malformed interval grammar as a separate boundary.

Focused repair gate:

```text
python3 -m unittest discover -s tests -p 'test_tarfilter_transform_regex*.py' -v
Ran 20 tests in 3.552s
OK
```

The focused run used only `TemporaryDirectory` state. The explicit cleanup and rerun receipt follows below.

Repository discovery in the local sandbox ran 78 tests. All tarfilter regex candidate and adjacent transform tests passed. Three environment controls failed outside this diff:

- two LF-14 archive tests expected effective UID 0 to preserve numeric archive ownership, while this restricted root sandbox could not apply that ownership;
- the chrootless TMPDIR negative control requires a host `/tmp`, which this sandbox does not provide.

Setting `TMPDIR` to a writable disposable directory removed the other temporary-path safety failure. The exact pushed head still requires hosted CI on its ordinary non-root runner.

After deleting the disposable roots, the focused 20-test gate passed again in 3.695 seconds and the caller-selected temporary directory was empty after explicit cleanup.
