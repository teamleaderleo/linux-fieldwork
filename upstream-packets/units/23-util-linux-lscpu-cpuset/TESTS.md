# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Debian baseline | `util-linux 2.41-5 amd64` |
| Installed binary | `/usr/bin/lscpu`, SHA-256 `e3c6e0c09d617cb9e77a3655f79a7a83d2dd865e49eabeccfbaa0335c9ff722e` |
| Canonical candidate | util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` |
| Candidate package | SHA-256 `92f3aa6fa87a30b9d030263dbbb0446f7679c2ee0456760271ea530268f6b971` |
| Candidate binary | SHA-256 `883912245c15612a224b761d01b838ecd23470eccf467369ec5c4a560a7946e1` |
| Package execution platform | Debian trixie container, amd64 |
| Privilege | unprivileged sysroot execution; package build in disposable container |
| Exact completed Linux Fieldwork head | `7a82f99ceac6801536c78ba1c2d261bd6f0f3dc8` |
| Exact package workflow | run `30692256031`, job `91348929951`, success |
| Package artifact | `8817069887`, digest `sha256:2b544b399e779bbf577ade1e99249436879fa928b639c5026f116044b461ac25` |

## Retained model and patch matrix

Command:

```text
/usr/bin/python3 -m unittest -v tests/test_util_linux_lscpu_cpuset_double_free.py
```

Result:

```text
Ran 5 tests in 0.082s
OK
baseline: duplicate cleanup detected (status 42)
candidate: output cleared, later cleanup is harmless (status 0)
patch dry-run/application: status 0 with --fuzz=0
fixture drift control: pass
```

Receipt: `artifacts/2026-08-01-focused-regression.txt`.

## Installed trixie baseline reproduction

Reusable command:

```text
bash scripts/reproduce-trixie-lscpu-cpuset.sh \
  --baseline /usr/bin/lscpu \
  --output-dir OUTPUT
```

The deterministic sysroot fixes `kernel_max=15`, `possible=0-15`, `present=0-15`, and one NUMA cpumap. The valid online list is `0-15`; the malformed mutation changes only that file to `5,12-%`.

Initial local baseline result:

| Case | Status | Observation |
| --- | ---: | --- |
| valid text | 0 | ordinary output |
| valid JSON | 0 | JSON parser passed |
| malformed text | 134 | `free(): double free detected in tcache 2` |
| malformed JSON | 134 | same allocator diagnostic |

Two fresh local runs produced byte-identical receipts. Receipt: `artifacts/2026-08-01-trixie-minimal-sysroot-reproduction.txt`.

## Losing allocation-size control

The same malformed logical input can exit 0 when `kernel_max` changes the allocation size and heap reuse. A bounded sweep produced aborting and clean values non-monotonically.

This is a detector-losing control, not evidence of a safe larger topology. The distinguishing regression therefore fixes the exact 16-CPU allocation identity.

## Exact Debian source, patch, and build

The successful exact-head workflow fetched `util-linux=2.41-5` and recorded:

```text
util-linux_2.41-5.dsc
  9e84dcc64170262f850aa5fd65902846a1ebf054d556ab5c4ec17fa16b00e628
util-linux_2.41.orig.tar.xz
  81ee93b3cfdfeb7d7c4090cedeba1d7bbce9141fd0b501b686b3fe475ddca4c6
util-linux_2.41-5.debian.tar.xz
  20ad832160d5ed8de4759ce00652f620ce642ab583c3c1c431b68a15cdba1d07
```

Effective source identities:

```text
baseline lib/path.c
  f934339cf7aba38ae6197e5b5ad3b6a9e7e5fb483ed3f807d45971968d3c7cda
candidate lib/path.c
  d0460b4fa3a32b7bdd3cf8b95fa5780bf830fa24bc9e64559408c3ddd1abbb8d
```

The canonical patch passed dry-run and real application with `--fuzz=0`. `dpkg-buildpackage -b -uc -us -j2` completed with `DEB_BUILD_OPTIONS=nocheck`.

Built identities:

```text
candidate package
  92f3aa6fa87a30b9d030263dbbb0446f7679c2ee0456760271ea530268f6b971
candidate lscpu
  883912245c15612a224b761d01b838ecd23470eccf467369ec5c4a560a7946e1
```

## Completed exact-head package matrix

Workflow:

```text
run: 30692256031
job: 91348929951
requested head: 7a82f99ceac6801536c78ba1c2d261bd6f0f3dc8
conclusion: success
artifact: 8817069887
artifact digest: sha256:2b544b399e779bbf577ade1e99249436879fa928b639c5026f116044b461ac25
```

Result:

| Case | Baseline | Candidate |
| --- | ---: | ---: |
| valid text | 0 | 0 |
| valid JSON | 0 | 0 |
| malformed text | 134 | 0 |
| malformed JSON | 134 | 0 |

Baseline malformed stderr contains:

```text
free(): double free detected in tcache 2
```

Candidate malformed stderr is empty.

Exact valid-output compatibility:

```text
text baseline SHA-256
  a8fc5c5ebc663afec6c11259ac5804aa808325208215ce08844131fd8e0274c7
text candidate SHA-256
  a8fc5c5ebc663afec6c11259ac5804aa808325208215ce08844131fd8e0274c7
JSON baseline SHA-256
  bc46275fd166aa84e37a80bcb26af0207b04551d6167696dda18dccc3e5dc1ed
JSON candidate SHA-256
  bc46275fd166aa84e37a80bcb26af0207b04551d6167696dda18dccc3e5dc1ed
```

Full receipt: `artifacts/2026-08-02-exact-head-package-matrix.txt`.

## Controlled util-linux native regression

Controlled repository: `teamleaderleo/util-linux`  
Gate branch head: `95ebc67e521195741040ffebb58756b259fb69b2`  
Internal draft PR: #1

Focused workflow:

```text
run: 30691835019
job: 91347815601
conclusion: success
artifact: 8816802119
artifact digest: sha256:d36f713357713593430fca369e4871e5ce3ff8f4c8455e07a67e8d83b95493c4
```

The job completed autogen, focused configure, `lscpu` build, and `tests/ts/lscpu/cpuset-parse-failure` against the built executable.

## Adjacent repository workflow

GCC workflow run `30691835043` passed:

- x86_64 build;
- x86 build;
- coverage;
- clang analyzer.

The sampled armv7 qemu job `91347815797` completed source build/test work and then failed during qemu registration because Docker Hub returned HTTP 429 unauthenticated pull-rate limiting for `multiarch/qemu-user-static`.

This sampled red is infrastructure-owned. Other red qemu jobs remain separately unclassified until their logs are read.

## Cleanup

Local fixture trees lived under `/tmp`, core files were disabled, and each tree was removed. No host sysfs write, mount, package change, socket, lock, or surviving process remained.

The hosted package build and execution used a disposable Debian trixie container. The successful workflow uploaded exact source, build, binary, matrix, and cleanup receipts after the container exited.

## Tests still required

- relevant complete util-linux native `lscpu` suite on the patched Debian tree;
- Debian stable-update quilt/changelog source delta;
- source-package build and source debdiff against `2.41-5`;
- exact actual-binary rerun after the source-package composition;
- useful architecture coverage after infrastructure classification;
- actual issue #4401 attachment execution;
- ASan or Valgrind actual-package execution;
- Debian review or submission, only after explicit authorization.

## Final evidence statement

The installed trixie defect, effective source owner, canonical correction, patched package build, and baseline/candidate actual-binary distinction are demonstrated. Candidate execution is no longer pending. The first incomplete gate is Debian stable-update source composition plus the relevant native/package test and source-debdiff record.
