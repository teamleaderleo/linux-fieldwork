# Tests and receipts — unit 05

## Controlled mirror candidate

Date: 2026-08-01  
Repository: `teamleaderleo/mmdebstrap`  
Base branch: `master`  
Candidate branch: `linux-fieldwork/unit-05-run-qemu-result-precedence`

### Exact identities

| Check | Result |
| --- | --- |
| Base commit | `574048f2a720057b75e56622003932f344dc700a` |
| Base `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Base byte count | 2,029 |
| Base SHA-256 | `da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300` |
| Candidate head | `457095c6f89655ab12b7055307f519e71bb0dbca` |
| Candidate `run_qemu.sh` blob | `3e8d4dc07f91d246a372749eb49ff9489c21c7b7` |
| Candidate byte count | 2,924 |
| Candidate SHA-256 | `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f` |

The base blob is exactly the imported Linux Fieldwork source blob. The candidate blob is exactly the previously validated composed source blob.

### Candidate commits

```text
614fb26a4f0724618a5eecd3ce1bee12454ff7de
cb6ef6d6c2b1368b3603b2ec06635c3815f31e11
13cf34fd87d44b4d37c6767fdbd153b2ef535a57
457095c6f89655ab12b7055307f519e71bb0dbca
```

### Compare gate

The GitHub compare API reports:

```text
status: ahead
ahead_by: 4
behind_by: 0
base_commit: 574048f2a720057b75e56622003932f344dc700a
merge_base: 574048f2a720057b75e56622003932f344dc700a
changed files: 1
run_qemu.sh: modified, 61 additions, 10 deletions
```

Result: pass. The candidate is a clean four-commit, one-file series on the controlled mirror base.

### Syntax and byte gate

The exact candidate bytes were reconstructed from the exact base and four retained patches in a disposable local Git repository.

```sh
git apply --check 0001-preserve-primary-result.patch
git apply 0001-preserve-primary-result.patch
git apply --check 0002-retain-first-signal-through-cleanup.patch
git apply 0002-retain-first-signal-through-cleanup.patch
git apply --check 0003-retain-signal-during-exit-cleanup.patch
git apply 0003-retain-signal-during-exit-cleanup.patch
git apply --check 0004-preserve-completed-guest-before-cleanup-signal.patch
git apply 0004-preserve-completed-guest-before-cleanup-signal.patch
/bin/sh -n run_qemu.sh
```

| Gate | Result |
| --- | --- |
| patch 1 check/apply | pass |
| patch 2 check/apply | pass |
| patch 3 check/apply | pass |
| patch 4 check/apply | pass |
| `/bin/sh -n` | pass |
| final Git blob | `3e8d4dc07f91d246a372749eb49ff9489c21c7b7` |
| final SHA-256 | `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f` |

The blob returned by GitHub after the final source commit equals the locally calculated final blob.

## Canonical historical execution

Canonical PR #319 exact head:

```text
2fe3f99364df29de217536dc35a4d03b10f49640
```

Linux Fieldwork CI:

```text
run 30628645668
job 889
result success
repository tests 276 passed
```

The run included all five focused modules, zero-fuzz four-patch composition, complete shell syntax, cleanup completion, immediate reruns, and repository discovery.

## Focused behavior matrix

| Earlier result | Later event | Selected final result |
| --- | --- | --- |
| host timeout 124 | guest failure | 124 |
| host failure 42 | malformed or missing guest status | 42 |
| explicit INT | guest outcome | 130 |
| explicit TERM | guest outcome | 143 |
| TERM starts cleanup | later INT | 143; cleanup completes |
| INT starts cleanup | later TERM | 130; cleanup completes |
| ordinary success | INT during cleanup | 130 |
| ordinary success | TERM during cleanup | 143 |
| completed guest failure | later cleanup-time TERM | 1 |
| guest success | cleanup-time signal and cleanup failure | signal result |
| host and guest success | cleanup failure | first cleanup failure |
| all success | none | 0 |

## Remaining gates

1. Search current canonical Salsa issues, branches, and merge requests for equivalent work.
2. Resolve current canonical Salsa `master` and file blob before submission.
3. Run current upstream ordinary checks on candidate head `457095c6…`.
4. Run a bounded real QEMU/`debvm-run` smoke test only in an authorized disposable environment.
5. Clean and rerun the focused gate after any canonical rebase.

The user has no fetch or setup command to run. The controlled mirror candidate is already present.
