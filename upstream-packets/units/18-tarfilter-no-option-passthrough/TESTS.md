# Tests and receipts

## Environment

- Date: 2026-08-01
- Python: container default Python 3
- Required local commands present: `patch`, GNU `tar`, gzip/bzip2/xz support through Python `tarfile`
- Exact baseline Git blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Current upstream repository base observed: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Current upstream tarfilter commit observed: `87b9b385b38795c58bc13ffb33b8724bed27f7a0`

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
  -i /tmp/u18repo/refreshed.patch
patch --fuzz=0 -p1 -d /tmp/u18apply \
  -i /tmp/u18repo/refreshed.patch
cmp /tmp/u18apply/upstream/mmdebstrap/tarfilter \
  /tmp/u18repo/upstream/mmdebstrap/tarfilter.candidate
python3 -m py_compile /tmp/u18apply/upstream/mmdebstrap/tarfilter
```

Observed:

```text
checking file upstream/mmdebstrap/tarfilter
patching file upstream/mmdebstrap/tarfilter
```

`cmp` and `py_compile` exited 0. No fuzz or offset appeared.

## Retained upstream-shaped patch

Commands:

```text
patch --dry-run --fuzz=0 -p1 -d /tmp/u18-upstream-apply \
  -i /tmp/u18-upstream.patch
patch --fuzz=0 -p1 -d /tmp/u18-upstream-apply \
  -i /tmp/u18-upstream.patch
python3 -m py_compile /tmp/u18-upstream-apply/tarfilter
```

Observed:

```text
checking file tarfilter
patching file tarfilter
```

Compilation exited 0. The retained packet patch is:

```text
patches/0001-tarfilter-restore-no-option-passthrough.patch
```

## Expanded local behavior matrix

A temporary test driver used the exact source blob and refreshed patch. Command:

```text
python3 /tmp/u18repo/enhanced_test.py
```

Observed:

```text
test_baseline_rewrites_gzip ... ok
test_candidate_byte_identity_including_sparse ... ok
test_each_active_operation_bypasses_copy ... ok

Ran 3 tests in 8.119s

OK
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

## Cleanup and rerun state

The temporary source copies contain no processes, mounts, sockets, or containers. Temporary directories were local under `/tmp`; cleanup is completed before handoff. The committed branch regression itself still requires execution from a clean checkout or hosted job.

## Unexecuted gates

1. Clean checkout command:

```text
python3 -m unittest -v tests.test_tarfilter_no_option_passthrough
```

2. Complete branch unit-test suite or equivalent hosted Linux Fieldwork CI.
3. Final overlap refresh in canonical upstream issues and pull requests.
4. Apply packet patch to a controlled upstream fork once one exists.

## Rerun commands

From the Linux Fieldwork branch root:

```text
python3 -m unittest -v tests.test_tarfilter_no_option_passthrough
python3 -m tools.run_fieldwork_unittests --verbosity 2
patch --dry-run --fuzz=0 -p1 -d /path/to/mmdebstrap \
  -i upstream-packets/units/18-tarfilter-no-option-passthrough/patches/0001-tarfilter-restore-no-option-passthrough.patch
```
