# Tests and receipts

## Environment

- Date: 2026-08-01
- Python: `3.13.5`
- GNU tar: `1.35`
- GNU patch: `2.8`
- Exact baseline Git blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Exact Linux Fieldwork patch blob: `44428ecf8d83a6edf2fca4f4da030129daacb13f`
- Exact committed regression blob: `0b8a0e092a6dd2bf7481e077e7c7ec0f27b461bb`
- Exact upstream-shaped patch blob: `9f856f389c7a991813dbe9d959edaf94c1155dec`
- Current upstream repository base observed: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Current upstream tarfilter commit observed: `87b9b385b38795c58bc13ffb33b8724bed27f7a0`
- Durable receipt: `artifacts/2026-08-01-focused-regression.json`

The shell environment had no network DNS, so the exact branch files were reconstructed from GitHub content blobs. Git blob hashes were recomputed before execution and matched all four identities above.

## Historical exact-head evidence

PR #46 head `8c8f45872e6eb2b4ea770e5753c6dc66347c8f56` passed Linux Fieldwork CI run `30534506273`. That run covered the earlier focused regression: baseline gzip rewrite; candidate identity for plain, gzip, bzip2, xz, GNU sparse, strip zero, and ID-shift zero; active transform and ID shift.

## Patch packaging baseline

Command against the exact imported source:

```text
patch --dry-run -p1 -d /tmp/u18repo \
  -i investigations/tarfilter-no-option-passthrough/tarfilter-no-option-passthrough.patch
```

Observed before refresh:

```text
checking file upstream/mmdebstrap/tarfilter
Hunk #1 succeeded at 201 with fuzz 2 (offset -1 lines).
```

Interpretation: source logic was selected correctly, while the retained patch failed the zero-fuzz application gate.

## Refreshed Linux Fieldwork patch

Commands:

```text
patch --dry-run --fuzz=0 -p1 -d /tmp/u18apply \
  -i investigations/tarfilter-no-option-passthrough/tarfilter-no-option-passthrough.patch
patch --fuzz=0 -p1 -d /tmp/u18apply \
  -i investigations/tarfilter-no-option-passthrough/tarfilter-no-option-passthrough.patch
python3 -m py_compile /tmp/u18apply/upstream/mmdebstrap/tarfilter
```

Observed:

```text
checking file upstream/mmdebstrap/tarfilter
patching file upstream/mmdebstrap/tarfilter
```

Application and compilation exited 0 with zero fuzz and zero offset.

## Exact committed-blob focused regression

Command from the reconstructed branch root:

```text
python3 -m unittest -v tests.test_tarfilter_no_option_passthrough
```

First execution:

```text
test_candidate_does_not_bypass_any_active_operation ... ok
test_candidate_preserves_no_option_archives_byte_for_byte ... ok
test_unmodified_source_proves_no_option_path_is_not_passthrough ... ok

Ran 3 tests in 10.181s

OK
EXIT_STATUS=0
```

Clean rerun after compilation:

```text
python3 -m py_compile \
  upstream/mmdebstrap/tarfilter \
  tests/test_tarfilter_no_option_passthrough.py
python3 -m unittest -v tests.test_tarfilter_no_option_passthrough
```

Observed:

```text
test_candidate_does_not_bypass_any_active_operation ... ok
test_candidate_preserves_no_option_archives_byte_for_byte ... ok
test_unmodified_source_proves_no_option_path_is_not_passthrough ... ok

Ran 3 tests in 8.617s

OK
RERUN_EXIT_STATUS=0
```

### Assertions executed

| Case | Baseline expectation | Candidate expectation | Result |
| --- | --- | --- | --- |
| gzip, no options | bytes differ; gzip signature removed | — | PASS |
| plain tar, no options | — | byte-identical | PASS |
| gzip tar, no options | — | byte-identical | PASS |
| bzip2 tar, no options | — | byte-identical | PASS |
| xz tar, no options | — | byte-identical | PASS |
| GNU PAX sparse, no options | — | byte-identical | PASS |
| `--strip-components=0` | — | byte-identical | PASS |
| `--idshift=0` | — | byte-identical | PASS |
| active path filter | — | target member removed | PASS |
| active PAX filter | — | selected PAX header removed | PASS |
| active type filter | — | regular member removed | PASS |
| active strip | — | nested member renamed | PASS |
| active transform | — | member renamed | PASS |
| active ID shift | — | uid/gid incremented | PASS |

## Retained upstream-shaped patch

Commands against an exact copy of current `tarfilter`:

```text
patch --dry-run --fuzz=0 -p1 -d /tmp/u18-upstream-apply \
  -i patches/0001-tarfilter-restore-no-option-passthrough.patch
patch --fuzz=0 -p1 -d /tmp/u18-upstream-apply \
  -i patches/0001-tarfilter-restore-no-option-passthrough.patch
python3 -m py_compile /tmp/u18-upstream-apply/tarfilter
```

Observed:

```text
checking file tarfilter
patching file tarfilter
UPSTREAM_PATCH_APPLY=PASS
```

The patched source SHA-256 was:

```text
8fec7cf1b1c6e314714e9a0347a7485f41d176e5cbc2769904f10af84a07e4ac
```

## Complete-diff review

`main...upstream/unit-18-tarfilter-no-option-passthrough` was reviewed as 11 commits ahead, zero behind before this receipt update. The product delta is limited to:

- one exact patch-context refresh with unchanged selected source behavior;
- one focused regression expansion enforcing `--fuzz=0` and all six active-operation categories;
- the durable unit packet and upstream-shaped patch.

No imported source, workflow, dependency, generated archive, or unrelated tarfilter semantic change is present.

## Cleanup and rerun state

Both focused executions used `TemporaryDirectory` fixtures. After the rerun, no `/tmp/tarfilter-no-option-*` directory remained. The standalone upstream-apply directory was removed by an EXIT trap. No processes, mounts, sockets, containers, or generated repository files remain.

## Evidence limits

- A complete Linux Fieldwork repository suite was not rerun in this shell because the environment lacked network DNS and a complete checkout was unavailable.
- Historical full CI remains green on the accepted source behavior through PR #46 run `30534506273`.
- The current branch changes after that run are an exact patch-context repair, focused test expansion, and packet records; the exact changed regression passed twice.
- A controlled upstream fork and fork-native commit remain authorization-dependent.

## Rerun commands

From the Linux Fieldwork branch root:

```text
python3 -m unittest -v tests.test_tarfilter_no_option_passthrough
python3 -m tools.run_fieldwork_unittests --verbosity 2
patch --dry-run --fuzz=0 -p1 -d /path/to/mmdebstrap \
  -i upstream-packets/units/18-tarfilter-no-option-passthrough/patches/0001-tarfilter-restore-no-option-passthrough.patch
```
