# Native gate selection — 2026-08-01

## Scope

Select and validate the smallest project-shaped regression for the composed `proxysolver` result-propagation change without widening into package builds, mirror setup, or unrelated mmdebstrap behavior.

## Current upstream harness observations

Public current-source views show that mmdebstrap's `coverage.py`:

- copies the source-tree `./proxysolver` into `shared/proxysolver` when the source copy is present;
- reads test definitions from `coverage.txt`;
- requires the names in `coverage.txt` and `tests/` to agree;
- accepts one or more test names for focused execution.

The project README documents focused execution through `coverage.py` after the normal coverage environment is prepared. These observations make a standalone `tests/proxysolver-result-propagation` shell file plus one `coverage.txt` stanza the smallest native placement.

## Draft native files

- `native-tests/proxysolver-result-propagation`
- `native-tests/coverage.txt.stanza`

The shell test consumes `shared/proxysolver`, matching the harness copy boundary. It creates only disposable files and a fake solver. The embedded Python rewrites the two fixed `/usr/lib/apt/solvers/apt` literals in a temporary copy, compiles that copy, and exercises:

1. solver exit 0 -> wrapper exit 0;
2. solver exit 7 -> wrapper exit 7;
3. solver SIGTERM -> wrapper SIGTERM;
4. solver SIGINT -> wrapper SIGINT;
5. inherited blocked SIGTERM -> wrapper SIGTERM after unblock;
6. exact stdout and dump equality;
7. inherited stderr equality;
8. bounded solver PID disappearance.

Draft test SHA-256: `3505be52c6feec272c3fc177fb49e7c19bb326167f2013944f0494b685b20dd5`.

## Candidate identity

- imported source git blob: `5cd51fab89104d30b8b12bff18a49d38d9be0003`;
- composed candidate source git blob: `13aef7109250a21bc7a23af6eaa7b235aef9c92c`;
- composed source patch SHA-256: `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48`.

## Disposable direct-gate layout

The local validation used this effective source-tree boundary:

```text
/tmp/unit12-native-gate/
├── proxysolver
├── shared/
│   └── proxysolver
└── tests/
    └── proxysolver-result-propagation
```

For each run, `shared/proxysolver` was replaced with either the exact composed candidate or the exact imported baseline. The test itself made a new `mktemp -d` root and removed it through its shell trap.

## Exact direct-gate commands

Candidate:

```text
cp candidate/proxysolver /tmp/unit12-native-gate/shared/proxysolver
cd /tmp/unit12-native-gate
sh tests/proxysolver-result-propagation
```

Baseline negative control:

```text
cp baseline/proxysolver /tmp/unit12-native-gate/shared/proxysolver
cd /tmp/unit12-native-gate
sh tests/proxysolver-result-propagation
```

Static checks:

```text
/bin/sh -n tests/proxysolver-result-propagation
python3 -m py_compile proxysolver
```

## Results

| Run | Source | Result |
| --- | --- | --- |
| Candidate first run | blob `13aef7109250a21bc7a23af6eaa7b235aef9c92c` | PASS, status 0 |
| Candidate immediate rerun | same | PASS, status 0 |
| Baseline negative control | blob `5cd51fab89104d30b8b12bff18a49d38d9be0003` | expected FAIL, status 1 |
| Candidate restored after negative control | candidate | PASS, status 0 |
| Shell syntax | native test | PASS |
| Candidate Python compilation | composed source | PASS |

The baseline failure stopped at the positive-status discriminator:

```text
Traceback (most recent call last):
  File "<stdin>", line 126, in <module>
  File "<stdin>", line 118, in run_case
AssertionError: ('exit-7', 0, 7)
```

This is the intended negative control: the imported wrapper converts solver exit 7 into wrapper success 0.

`shellcheck` and `shfmt` were absent from the execution environment, so those optional checks did not run. This is a tooling gap, not a test or product failure.

## Intended exact-upstream execution

After materializing the exact upstream checkout and applying the source patch, the smallest direct gate is:

```text
mkdir -p shared
cp proxysolver shared/proxysolver
sh /absolute/path/linux-fieldwork/upstream-packets/units/12-proxysolver-result-propagation/native-tests/proxysolver-result-propagation
```

After adding the native file under `tests/` and its stanza to `coverage.txt`, the project-shaped focused gate is:

```text
CMD=./mmdebstrap ./coverage.py proxysolver-result-propagation
```

The normal project mirror/coverage prerequisites still apply to the second command.

## Integration decision

Retain the test and coverage stanza as separate packet drafts. Do not emit a `0002` source-tree integration patch until the exact canonical `coverage.txt` bytes and preferred insertion neighborhood are materialized. This prevents a stale or invented context hunk while preserving the complete proposed test body and registration.

## Remaining discriminator

In a network-enabled environment:

1. checkout canonical commit `77ec9be5417ee44c96343d2347145585da1b1f94`;
2. verify `git hash-object proxysolver` equals `5cd51fab89104d30b8b12bff18a49d38d9be0003`;
3. apply the composed source patch;
4. run the direct native gate above;
5. copy the draft into `tests/`, place the stanza in exact `coverage.txt` context, and run the focused `coverage.py` gate.

## Cleanup and contact

The direct runs used disposable files only. Fake solver PID disappearance is asserted in every case. The retained `/tmp/unit12-native-gate` fixture was a local test root and contains no credential or upstream checkout. No fork, upstream branch, issue, pull request, comment, email, or other upstream contact occurred.
