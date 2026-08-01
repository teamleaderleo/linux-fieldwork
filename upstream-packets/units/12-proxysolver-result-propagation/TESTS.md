# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | public main `77ec9be5417ee44c96343d2347145585da1b1f94`; checkout not materialized |
| Imported source | blob `5cd51fab89104d30b8b12bff18a49d38d9be0003` |
| Candidate | composed patch SHA-256 `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48` |
| Linux Fieldwork branch base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Platform/distribution | isolated Linux container |
| Architecture | x86_64 |
| Kernel | `6.12.13 #1 SMP Thu Jul 23 17:57:28 UTC 2026` |
| Runtime | Python `3.13.5` |
| Privilege boundary | unprivileged disposable files and subprocesses |
| Important tool versions | GNU patch `2.8` |

## Baseline reproducer

### Command

```text
python3 upstream-packets/units/12-proxysolver-result-propagation/scripts/test_proxysolver_result_propagation.py
```

The script copies the exact imported source into `TemporaryDirectory`, replaces only the two real-solver path literals in disposable copies, and drives a fake solver.

### Expected distinguishing result

The test requires imported baseline child exit 7 to become wrapper 0.

### Observed result

- status: baseline wrapper `0` for child exit `7`;
- stdout: `Install: 1\nPackage: example\n`;
- stderr: `solver diagnostic\n` inherited unchanged;
- dump: identical to stdout;
- surviving process: none;
- result: negative control passed in all successful matrix runs.

## Candidate reproducer

### Command

```text
python3 upstream-packets/units/12-proxysolver-result-propagation/scripts/test_proxysolver_result_propagation.py
```

### Expected result

Success remains 0, positive failures propagate exactly, SIGTERM and SIGINT are replayed exactly, inherited blocked SIGTERM is unblocked, output/dump/stderr behavior remains intact, and child processes disappear.

### Observed result

```text
Ran 5 tests in 14.097s
OK

Ran 5 tests in 14.112s
OK

Simulated final repository layout:
Ran 5 tests in 13.536s
OK
```

Script SHA-256 after final path-discovery edit: `4c9aa8b0bd5563efaebf670640ace899f55a331d99b6f6f6951f6d551932eba1`.

## Matrix

| Case | Baseline or ordinary-only | Composed candidate | Exact test | Result |
| --- | --- | --- | --- | --- |
| Positive failure | imported wrapper 0 for child 7 | wrapper 7 | `test_baseline_false_success_and_candidate_exit_status` | PASS twice plus final-layout pass |
| Ordinary success | 0 | 0 | `test_success_remains_zero` | PASS |
| SIGTERM | ordinary-only 241 | `-SIGTERM` | `test_sigterm_and_sigint_are_reraised_exactly` | PASS |
| SIGINT | ordinary-only 254 | `-SIGINT` | same | PASS |
| Blocked mask | signal could remain pending without unblock | `-SIGTERM` | `test_inherited_blocked_sigterm_is_unblocked_before_reraise` | PASS |
| Stdout/dump | expected fixture bytes | same exact bytes | all dynamic cases | PASS |
| Stderr passthrough | inherited diagnostic | inherited diagnostic | all dynamic cases | PASS |
| Child cleanup | PID must disappear | PID disappears | all dynamic cases | PASS |
| Source composition | n/a | one wait, one negative branch, one nonzero branch | `test_composed_source_contains_one_result_decision` | PASS |
| Immediate rerun | n/a | full matrix | same command | PASS |

## Prior carrier receipts

| Carrier | Command/run | Result |
| --- | --- | --- |
| PR #134 | Linux Fieldwork CI `30547040121` | ordinary 0/7 matrix passed |
| PR #166 | focused local `python3 -m unittest -v tests/test_mmdebstrap_proxysolver_signal_status.py` | 4 tests in 9.206s, OK |
| PR #166 | CI `30577241772`, `30577348662` | success |
| PR #201 | run/job `30579465025` / `90995804005`, Ubuntu 24.04.4 | exact Packet G matrices ran twice; 24 successful test executions |
| PR #207 | exact-head CI `30579889333` | success |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Exact upstream patch application | `patch --batch --forward -p1 -i ...` in commit `77ec9be...` checkout | NOT RUN: checkout unavailable in execution environment | NEEDS BRANCH |
| Packet focused regression in upstream checkout | packet script command | NOT RUN in exact upstream checkout | NEEDS BRANCH |
| Relevant upstream coverage test | project-specific placement/command unresolved | NOT RUN | NEEDS BRANCH |
| Formatting/lint | `python3 -m py_compile proxysolver` | local composed source PASS; upstream checkout gate pending | local patch only |
| Build/package test | Debian package or full `coverage.sh` gate | NOT RUN | NEEDS BRANCH |

## Patch application and composition

- imported base identity: blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`;
- historical status patch blob: `0c29e916fa33f41bb5bea0b4ee863d7a0eee5519`;
- historical signal patch blob: `b4c9975f39c37a7857f644855ee81befaa760795`;
- composed patch SHA-256: `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48`;
- both historical patches applied sequentially without fuzz or offset in the disposable composition tree;
- composed patch applied with `patch --batch --forward -p1` in the simulated upstream-root layout;
- complete 17-line source addition reviewed;
- public overlap search performed 2026-07-31; no surfaced equivalent issue or pull request.

## Red or neutral run classification

The first packet-script run failed before test execution because the disposable ordinary-only tree placed `proxysolver` at repository root while the historical status patch addresses `upstream/mmdebstrap/proxysolver`. `patch` reported “can't find file to patch”; 0 tests ran. Classification: **fixture path packaging**. The disposable layout was corrected without changing either product patch. All subsequent runs passed.

Historical PR #166 also recorded an initial malformed retained follow-up patch at head `f57b43b32d78ad5dcd58039c816907fe7abe27de`. Classification: patch packaging; corrected heads later passed.

## Cleanup and rerun

Every dynamic run used `TemporaryDirectory`. Fake solver processes were checked by PID and disappeared within the bounded assertion. Temporary dump, PID, solver, wrapper, and bytecode files were removed when the test process exited. No sockets, mounts, containers, package state, or imported source changed. The full matrix passed immediately a second time and passed again from a simulated final repository path.

## Tests not run

- current upstream checkout hash comparison;
- exact upstream patch application;
- real `/usr/lib/apt/solvers/apt` execution;
- mmdebstrap full `coverage.sh` suite;
- Debian package build or autopkgtest;
- fatal-signal matrix beyond SIGTERM and SIGINT;
- wrapper-receives-signal-while-child-runs lifecycle case;
- broken stdout sink during explicit flush.

## Final evidence statement

The executed matrix establishes that the composed source logic fixes the imported wrapper's false success and the ordinary-only repair's signal wrapping while preserving output, dump, stderr, success, and child cleanup for exit 0, exit 7, SIGTERM, SIGINT, and inherited blocked SIGTERM. The conclusion ends at the exact imported blob and local Linux/Python environment; current-upstream and native-suite gates remain open.
