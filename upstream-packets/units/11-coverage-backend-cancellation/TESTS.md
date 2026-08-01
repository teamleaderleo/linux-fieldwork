# Tests and receipts — unit 11

## Current result

The exact clean target candidate has passed focused target execution and a bounded project-native ordinary source slice.

Focused evidence:

- zero-fuzz patch equivalence and candidate compilation;
- six-control baseline/status/group matrix twice;
- fourteen-control null/QEMU-wrapper/passwordless-sudo matrix twice, no skips;
- cleanup and immediate rerun.

Ordinary source evidence:

- native `coverage.sh help man version` path twice;
- real source checks, `coverage.py` inventory, `run_null.sh`, and shell-template scenarios;
- 3/3 first pass and 3/3 immediate rerun.

The full prepared-mirror package matrix, real QEMU/debvm, and public upstream CI remain unexecuted.

## Exact identities

| Field | Value |
| --- | --- |
| Canonical base | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Base `coverage.py` blob | `9a522484aef05deae514a98e4b6adf5feb6c886d` |
| Canonical `run_null.sh` blob | `e0a8c106f9d3d636baea286d2ab33834748dffc9` |
| Canonical `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Packet patch blob | `f1a2c75adfa009b6f1ac29e5a31bef526400444f` |
| Controlled repository | `teamleaderleo/mmdebstrap` |
| Clean source head | `431614b3af58ba4f70791aa1d42cf5b71c965dd2` |
| Candidate `coverage.py` blob | `9e31f21cf37228257b5e0705d9ecb13b7a66e40f` |
| Clean diff | `coverage.py` only; 8 additions, 3 deletions |
| Clean review surface | `teamleaderleo/mmdebstrap#4` |

## Focused target gate

Closed internal execution PR: `teamleaderleo/mmdebstrap#2`.

- runner head: `f0319d53f515174c3794237f34f76699182ac509`
- generated merge: `bf1f0cfde0ec6e0691c0dfb7d4656aafe3deab48`
- workflow run: `30706007117`
- result: success

### Candidate equivalence and null

- job `91385135488`: success
- exact source, packet, patch, and blob identities: verified
- zero-fuzz patch application: success
- patch-materialized candidate byte-equal to clean target `coverage.py`
- candidate compilation: success
- first six-control pass: 6/6 in 1.421 seconds
- immediate rerun: 6/6 in 1.420 seconds
- artifact `8820336271`
- SHA-256 `97eba28273b50dfcf51c32a2fe4cf49aa50da5634a3aaba6b052ad3728ae1ce8`

### Refined topology

- job `91385135449`: success
- exact PR #339 carrier and four test blobs: verified
- first null/QEMU-wrapper/passwordless-sudo pass: 14/14 in 4.246 seconds
- immediate rerun: 14/14 in 4.367 seconds
- skips: none
- actual passwordless-sudo controls: executed
- artifact `8820337503`
- SHA-256 `8d72b079fa9e30ee92bdf28cf217e9df3e4ae7a5ffeb7374b76950313bf24614`

Both jobs uploaded receipts and completed orphan-process cleanup.

Receipt: [`artifacts/2026-08-01-controlled-target-run.md`](artifacts/2026-08-01-controlled-target-run.md).

## Ordinary project-native source slice

Closed internal execution PR: `teamleaderleo/mmdebstrap#3`.

- ordinary runner head: `4dd88b02d9b40c1b485f8db76a2038b2e7ec9ca3`
- generated merge: `b5a62925d43b125680a206fe80960b1b03845d7e`
- workflow run: `30706633832`
- job: `91386769087`
- result: success
- runner: Ubuntu 24.04.4
- Black: 26.5.1, Python 3.12.3

Native command path:

```sh
./coverage.sh help man version
```

Results:

- candidate compilation: success;
- first pass: 3/3;
- immediate rerun: 3/3;
- `coverage.sh`: success twice;
- orphan-process cleanup: completed.

Artifact:

- ID `8820528312`
- size 2207 bytes
- SHA-256 `13986015aebc37cd3624f5114baa2a599f3c3dccb01e838b367287b2585b8f55`
- expiry `2026-10-30T15:45:43Z`

### Proven exact-base source-check defect

The unmodified exact base fails before scenario dispatch because Black wants to reformat unchanged canonical `tarfilter` blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

The successful gate accepts only `black --check ./tarfilter` after asserting that exact blob. Every other Black invocation is delegated to real pinned Black 26.5.1, including the changed `coverage.py`.

### Retained setup negatives

- run `30706437303`, job `91386266957`: Ubuntu Black 24.2 rejected exact canonical `tarfilter`; artifact `8820467784`, SHA-256 `d9bc010eb74d48810a6a6555b9a216c25d86f5949cd72e53eb50f78c83021626`;
- run `30706495662`, job `91386420319`: Black 26.5.1 confirmed the same base defect; artifact `8820487571`, SHA-256 `b7db9a4aa674f2ef4926d3a5a6e7511b0069d10f3dec4242f47c348485f8a4fc`;
- run `30706556363`, job `91386578617`: base defect isolated; `help` and `version` passed; `man` exposed missing `perl-doc`; artifact `8820506648`, SHA-256 `69e3157b34b1b702afd6a7f5dbe713dfcc716e89d52ca14ac083e2c92a716dbd`.

Adding `perl-doc` produced the successful fourth run without changing the candidate source.

Receipt: [`artifacts/2026-08-01-ordinary-source-slice.md`](artifacts/2026-08-01-ordinary-source-slice.md).

## Canonical packet execution

Run `30689911760` against exact canonical source:

- job `91342674259`: zero-fuzz application, compilation, 6/6 twice;
- job `91342674164`: 14/14 twice, no skips;
- cleanup and immediate rerun: success;
- artifacts `8815289674` and `8815290820` with retained digests.

Packet head `d232e4fdd67cf0592e129a60534e984dcbec6bfe` passed run `30690101504`. Later exact packet heads and runs are recorded on PR #401.

## Distinguishing result

| Variant | Parent-only SIGINT status | Responsive backend state | Later work |
| --- | ---: | --- | --- |
| imported baseline | 0 after deliberate release | alive before release | yes |
| status-only predecessor | 130 after deliberate release | alive before release | yes |
| group candidate | 130 | no live in-group process | no |

## Historical gates

- mechanism head `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`: run `30632491641`, job `91161937871`, 359 tests passed;
- evidence head `dfc6d0503fb844f4c428ce16a567a9fdcd35280a`: run `30633602052`, job `91165600654`, 340 unique tests passed;
- refined QEMU head `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7`: run `30633578396`, job `91165522248`, 269 tests passed.

## Submission-shape decision

The clean target diff is source-only.

The native suite treats every non-dot `tests/` entry as a shell-template package scenario indexed by `coverage.txt`. A native test of this outer orchestrator would require a recursive mini-coverage fixture substantially larger than the product fix. The deterministic reproducer and exact target receipts remain in this packet. A recursive native regression can be added if an eligible reviewer or upstream maintainer requests it.

## Evidence limits

- full prepared-mirror 283-entry package matrix;
- real QEMU/debvm and package operations;
- non-Linux behavior;
- eligible independent complete clean-diff acceptance;
- public upstream CI and maintainer review.

No public upstream interaction is authorized or performed.
