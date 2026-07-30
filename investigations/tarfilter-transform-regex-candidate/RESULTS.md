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
