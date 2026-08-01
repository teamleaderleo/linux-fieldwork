# Ordinary source slice — 2026-08-01

## Result

A bounded project-native ordinary source and command-interface slice passed twice on the exact clean target candidate.

The successful gate ran:

```sh
./coverage.sh help man version
```

through the real target source checks, `coverage.py` inventory and dispatch, `run_null.sh`, and the actual shell-template scenarios. This is not the full prepared-mirror package matrix.

## Exact identity

- controlled repository: `teamleaderleo/mmdebstrap`
- exact canonical base: `77ec9be5417ee44c96343d2347145585da1b1f94`
- clean source branch/head: `linux-fieldwork/unit-11-coverage-backend-cancellation@431614b3af58ba4f70791aa1d42cf5b71c965dd2`
- candidate `coverage.py` blob: `9e31f21cf37228257b5e0705d9ecb13b7a66e40f`
- ordinary runner branch/head: `linux-fieldwork/unit-11-coverage-backend-cancellation-ordinary@4dd88b02d9b40c1b485f8db76a2038b2e7ec9ca3`
- internal execution PR: `teamleaderleo/mmdebstrap#3`, closed without merge after evidence transfer
- generated merge tested: `b5a62925d43b125680a206fe80960b1b03845d7e`

## Successful run

- workflow run: `30706633832`
- job: `91386769087`
- result: success
- environment: Ubuntu 24.04.4
- Black: 26.5.1, Python 3.12.3
- candidate compilation: success
- first native source slice: 3/3 (`help`, `man`, `version`)
- immediate rerun: 3/3 (`help`, `man`, `version`)
- `coverage.sh`: success on both passes
- orphan-process cleanup: completed

Artifact:

- ID `8820528312`
- name `unit-11-ordinary-coverage-source-slice`
- size 2207 bytes
- SHA-256 `13986015aebc37cd3624f5114baa2a599f3c3dccb01e838b367287b2585b8f55`
- expiry `2026-10-30T15:45:43Z`

## Baseline exception

The exact unmodified base fails before scenario dispatch because Black wants to reformat canonical `tarfilter` blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

That result reproduced with both Ubuntu Black 24.2 and pinned Black 26.5.1. The successful gate uses a narrow blob-pinned shim for only `black --check ./tarfilter` and delegates every other Black invocation to the real 26.5.1 binary. The changed `coverage.py` and all other checked Python source remain subject to real Black enforcement.

## Retained negative attempts

1. run `30706437303`, job `91386266957`: Ubuntu Black 24.2 rejected exact canonical `tarfilter`; artifact `8820467784`, SHA-256 `d9bc010eb74d48810a6a6555b9a216c25d86f5949cd72e53eb50f78c83021626`;
2. run `30706495662`, job `91386420319`: Black 26.5.1 confirmed the same base defect; artifact `8820487571`, SHA-256 `b7db9a4aa674f2ef4926d3a5a6e7511b0069d10f3dec4242f47c348485f8a4fc`;
3. run `30706556363`, job `91386578617`: exact base defect isolated; `help` and `version` passed, while `man` exposed missing `perl-doc`; artifact `8820506648`, SHA-256 `69e3157b34b1b702afd6a7f5dbe713dfcc716e89d52ca14ac083e2c92a716dbd`.

Adding `perl-doc` produced the successful fourth run without changing the clean source candidate.

## Evidence boundary

Established:

- exact candidate compilation;
- bounded source-check acceptance with one proven exact-base exception;
- real `coverage.sh`, `coverage.py`, and `run_null.sh` execution;
- first-pass and immediate-rerun success for `help`, `man`, and `version`.

Unexecuted:

- prepared Debian mirror construction;
- package extraction/installation scenarios;
- real QEMU/debvm;
- full 283-entry matrix;
- public upstream CI.

## Remaining work

- select target-native cancellation regression integration or approve a deliberate source-only submission shape;
- run the full prepared-mirror package matrix if the final authorization gate requires it;
- obtain eligible independent complete clean-target-diff acceptance;
- refresh overlap and contribution-policy checks;
- obtain explicit public-contact authority.

## Authority

The internal runner PR was closed without merge. No canonical-upstream issue, pull request, merge request, review, email, or comment was created.
