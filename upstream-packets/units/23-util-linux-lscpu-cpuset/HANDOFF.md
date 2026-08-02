# Handoff — unit 23 util-linux `lscpu` cpuset ownership

Handoff date: 2026-08-02  
State: `HOLD`  
External contact authorized: `false`  
External contact made: `none`

## Exact Linux Fieldwork state

```text
repository: teamleaderleo/linux-fieldwork
branch: upstream/unit-23-util-linux-lscpu-cpuset
internal PR: #404
branch base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
last exact execution head: 7a82f99ceac6801536c78ba1c2d261bd6f0f3dc8
```

The final branch head containing this handoff is recorded in the issue #397 unit checkpoint.

## Executive result

Debian trixie `util-linux 2.41-5` is proven affected. A deterministic 16-CPU sysroot makes the installed `lscpu` abort in text and JSON modes on malformed `cpu/online` content `5,12-%`; valid controls exit 0.

Exact Debian source retains the stale caller-visible cpuset pointer. Canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` clears the pointer after freeing it. The patch applies to Debian `2.41-5` with zero fuzz and the patched binary package builds.

The exact-head package matrix has completed successfully. The baseline aborts with status 134 for malformed text and JSON. The candidate exits 0 for both malformed modes. Valid baseline and candidate text and JSON outputs are byte-identical.

The controlled util-linux fork's focused native build and regression gate also succeeds. Candidate execution and focused native regression are no longer incomplete steps.

The unit remains `HOLD` for Debian stable-update source composition, relevant complete native/package testing, source-package build, and source debdiff.

## Completed exact-head package matrix

```text
requested Linux Fieldwork head:
  7a82f99ceac6801536c78ba1c2d261bd6f0f3dc8
workflow run:
  30692256031
job:
  91348929951
conclusion:
  success
artifact:
  8817069887
  unit-23-util-linux-30692256031-1
artifact digest:
  sha256:2b544b399e779bbf577ade1e99249436879fa928b639c5026f116044b461ac25
```

Result:

```text
baseline valid text:       0
baseline valid JSON:       0
baseline malformed text:   134
baseline malformed JSON:   134
candidate valid text:      0
candidate valid JSON:      0
candidate malformed text:  0
candidate malformed JSON:  0
```

Baseline malformed stderr:

```text
free(): double free detected in tcache 2
```

Valid compatibility:

```text
text baseline/candidate SHA-256:
  a8fc5c5ebc663afec6c11259ac5804aa808325208215ce08844131fd8e0274c7
JSON baseline/candidate SHA-256:
  bc46275fd166aa84e37a80bcb26af0207b04551d6167696dda18dccc3e5dc1ed
```

Full receipt:

```text
artifacts/2026-08-02-exact-head-package-matrix.txt
```

## Exact source and candidate identities

| Item | Identity |
| --- | --- |
| Installed baseline | `util-linux 2.41-5 amd64` |
| Baseline binary SHA-256 | `e3c6e0c09d617cb9e77a3655f79a7a83d2dd865e49eabeccfbaa0335c9ff722e` |
| Debian `.dsc` SHA-256 | `9e84dcc64170262f850aa5fd65902846a1ebf054d556ab5c4ec17fa16b00e628` |
| Debian upstream tar SHA-256 | `81ee93b3cfdfeb7d7c4090cedeba1d7bbce9141fd0b501b686b3fe475ddca4c6` |
| Debian delta tar SHA-256 | `20ad832160d5ed8de4759ce00652f620ce642ab583c3c1c431b68a15cdba1d07` |
| Effective baseline `lib/path.c` SHA-256 | `f934339cf7aba38ae6197e5b5ad3b6a9e7e5fb483ed3f807d45971968d3c7cda` |
| Canonical correction | `4581ede384f22983d6155768635ce43cb5304cb0` |
| Candidate `lib/path.c` SHA-256 | `d0460b4fa3a32b7bdd3cf8b95fa5780bf830fa24bc9e64559408c3ddd1abbb8d` |
| Candidate package SHA-256 | `92f3aa6fa87a30b9d030263dbbb0446f7679c2ee0456760271ea530268f6b971` |
| Candidate binary SHA-256 | `883912245c15612a224b761d01b838ecd23470eccf467369ec5c4a560a7946e1` |
| Retained patch | `patches/0001-clear-cpuset-output-after-error.patch` |

## Controlled util-linux fork

```text
repository: teamleaderleo/util-linux
canonical stable fix: 3cd5f1dd69495864f3046cdbcefa104786fe5a27
CI base branch: linux-fieldwork/unit-23-lscpu-cpuset-native-base
CI base head: 7669d148543822d56ffffa31d2f399f078f8e117
CI gate branch: linux-fieldwork/unit-23-lscpu-cpuset-native-gate
CI gate head: 95ebc67e521195741040ffebb58756b259fb69b2
internal draft PR: teamleaderleo/util-linux#1
native workflow run: 30691835019
native job: 91347815601
conclusion: success
artifact: 8816802119
artifact digest: sha256:d36f713357713593430fca369e4871e5ce3ff8f4c8455e07a67e8d83b95493c4
```

The focused job completed autogen, configured and built `lscpu`, and passed `tests/ts/lscpu/cpuset-parse-failure` against the built executable.

The controlled fork remains an internal execution and regression carrier. It does not propose a competing product implementation.

## Adjacent repository workflow

The controlled fork GCC workflow run `30691835043` passed x86_64, x86, coverage, and clang-analyzer jobs.

The sampled armv7 qemu job `91347815797` reached and passed source build/test work, then failed pulling `multiarch/qemu-user-static` because Docker Hub returned HTTP 429 unauthenticated pull-rate limiting. This sampled red is infrastructure-owned. Other red qemu jobs require their own log-level confirmation before the same classification is applied.

## Current-master regression candidate

```text
repository: teamleaderleo/util-linux
branch: linux-fieldwork/unit-23-cpuset-error-regression
base: fd82c4043fab942b889f478800118c66edfbc39f
head: cf8aadf90786200c8cb7006fa78db428d0229985
commit: tests: exercise malformed lscpu cpuset cleanup
changed file: tests/ts/lscpu/lscpu
product files changed: none
external PR: none
```

This test-only candidate remains internal. It has not been selected as the Debian package delivery mechanism and requires separate exact execution before any upstream-test proposal.

## First incomplete step

Create the final Debian stable-update source composition in a disposable tree:

1. unpack exact `util-linux 2.41-5` source;
2. add the canonical patch to `debian/patches/series` with original authorship retained;
3. add a minimal stable-update changelog version following current Debian guidance;
4. run the relevant native util-linux `lscpu` suite on the patched tree;
5. build source and binary packages;
6. retain a source debdiff against `2.41-5`;
7. rerun the exact valid/malformed text and JSON actual-binary matrix from that final package composition;
8. record cleanup and an immediate rerun.

Do not describe `DEB_BUILD_OPTIONS=nocheck` as native test evidence.

## Next safe technical actions

1. compose the disposable Debian quilt/changelog delta;
2. run relevant native/package tests;
3. build source and binary packages;
4. retain source debdiff and exact package identities;
5. rerun the package matrix cleanly;
6. finish useful architecture/infrastructure classification;
7. move to `READY FOR AUTHORIZATION` only when the complete technical send gate passes;
8. request an explicit send/hold decision before any Debian or util-linux interaction.

## Evidence limits

- successful package execution is amd64-only;
- the completed binary-package build used `DEB_BUILD_OPTIONS=nocheck`;
- the complete native `lscpu` suite on the patched Debian tree is not retained;
- the final source package and source debdiff are absent;
- the public issue #4401 attachment has not been executed against the final package pair;
- ASan and Valgrind actual-package runs remain unexecuted.

## Cleanup state

Hosted package work ran in a disposable Debian trixie container. Local fixture trees were removed. No process, mount, sysroot, package installation, credential, or external state remains under this unit's control.

GitHub-side state is limited to the retained Linux Fieldwork branch and PR, controlled fork branches and internal PR, workflow logs, and artifacts.

## Stop and reassess when

- Debian publishes an equivalent trixie correction;
- final package composition still aborts or changes valid output;
- native tests identify an adjacent required patch;
- current public attachment behavior contradicts the deterministic fixture;
- external-contact authority changes.

## Authority reminder

Internal repository work, controlled branches, controlled-fork PR #1, Linux Fieldwork PR #404, builds, tests, packet updates, and issue checkpoints are authorized. No external issue, comment, email, pull request, merge request, review, or package upload is authorized. None occurred.
