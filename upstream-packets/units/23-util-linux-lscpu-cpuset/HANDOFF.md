# Handoff — unit 23 util-linux `lscpu` cpuset ownership

Handoff date: 2026-08-01  
State: `HOLD`  
External contact authorized: `false`  
External contact made: `none`

## Exact Linux Fieldwork state

```text
repository: teamleaderleo/linux-fieldwork
branch: upstream/unit-23-util-linux-lscpu-cpuset
internal PR: #404
branch base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
complete packet head immediately before this handoff update: 23849ee8554e233ac2d50c3ad64188c79743458d
```

The final handoff commit is recorded in the issue #397 unit checkpoint.

## Executive result

Debian trixie `util-linux 2.41-5` is proven affected. A deterministic 16-CPU sysroot makes the installed `lscpu` abort in text and JSON modes on malformed `cpu/online` content `5,12-%`; valid controls exit 0 and the full matrix repeats cleanly.

Exact Debian source retains the stale caller-visible cpuset pointer. Canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` clears the pointer after freeing it. The patch applies to Debian `2.41-5` with zero fuzz and the patched binary package builds.

The user's controlled util-linux fork now removes the source and native-test-surface blocker.

## Controlled util-linux fork

```text
repository: teamleaderleo/util-linux
canonical stable fix: 3cd5f1dd69495864f3046cdbcefa104786fe5a27

fork-only CI base branch:
  linux-fieldwork/unit-23-lscpu-cpuset-native-base
  head 7669d148543822d56ffffa31d2f399f078f8e117

fork-only CI gate branch:
  linux-fieldwork/unit-23-lscpu-cpuset-native-gate
  head 95ebc67e521195741040ffebb58756b259fb69b2

internal controlled-fork draft PR:
  teamleaderleo/util-linux#1
```

The fork PR is an execution carrier only. It changes workflow/fixture files and adds no competing product implementation.

## Queued exact-head runs

### Debian package carrier

```text
30690810870 at 187ab0c3c72eb4f733e5c9eebaeb7b748f687fbb — queued
30690831292 at 8ba7537bda1f7fd15a659dfb918bbc8df110419d — queued
```

### Controlled util-linux fork

```text
30691835019 — Linux Fieldwork unit 23 lscpu cpuset gate — queued
30691835043 — util-linux Build test — queued
```

Current first incomplete owner: hosted execution queue. No source, patch, build, native-test, or fixture result can be inferred before a job starts.

## Native gate contract

The controlled fork gate uses util-linux's own documented paths:

```sh
.github/workflows/cibuild-setup-ubuntu.sh
.github/workflows/cibuild.sh CONFIGUREFAST MAKE
make check-programs
sudo -E make check TS_OPTS="--parallel=1 lscpu"
```

It then runs the deterministic valid and malformed text/JSON sysroot cases twice against built `./lscpu` and requires:

- status 0 for every candidate case;
- valid JSON output;
- no double-free, invalid-pointer, or abort diagnostic;
- retained source head and `lib/path.c` blob;
- retained built-binary digest;
- project-native test outputs and diffs;
- cleanup and immediate rerun.

Receipt:

```text
artifacts/2026-08-01-controlled-util-linux-fork.txt
```

## Completed evidence

| Item | Identity |
| --- | --- |
| Installed baseline | `util-linux 2.41-5 amd64` |
| Baseline binary SHA-256 | `e3c6e0c09d617cb9e77a3655f79a7a83d2dd865e49eabeccfbaa0335c9ff722e` |
| Baseline minimal matrix | `artifacts/2026-08-01-trixie-minimal-sysroot-reproduction.txt` |
| Source/build run | `30690487287`, job `91344214299` |
| Source/build artifact | `8815555088`; ZIP SHA-256 `ec7e883d7d0716123342c9dfcc01db8e4a8af97461d635467feddcbd51a41399` |
| Effective baseline `lib/path.c` SHA-256 | `f934339cf7aba38ae6197e5b5ad3b6a9e7e5fb483ed3f807d45971968d3c7cda` |
| Candidate `lib/path.c` SHA-256 | `d0460b4fa3a32b7bdd3cf8b95fa5780bf830fa24bc9e64559408c3ddd1abbb8d` |
| Candidate package SHA-256 | `92f3aa6fa87a30b9d030263dbbb0446f7679c2ee0456760271ea530268f6b971` |
| Candidate binary SHA-256 | `883912245c15612a224b761d01b838ecd23470eccf467369ec5c4a560a7946e1` |
| Retained patch | `patches/0001-clear-cpuset-output-after-error.patch` |

## First incomplete step

Classify the first completed run among the four exact IDs above.

For a completed package run, retain job log, artifact ID/digest, candidate outputs, baseline/candidate valid-output comparison, malformed-case statuses, cleanup, and rerun.

For a completed fork run, retain project-native `lscpu` test result, deterministic matrix result, source/binary identities, artifact ID/digest, cleanup, and rerun.

## Next safe technical actions

1. classify the first completed queued run;
2. repair only the owner of the first failure;
3. retain exact artifacts and logs;
4. create a minimal Debian `2.41-5+deb13u1` source delta and debdiff after execution is green;
5. rebuild source and binary packages;
6. rerun focused package and native gates on the exact final head;
7. move to `READY FOR AUTHORIZATION` only when the complete technical send gate passes;
8. request an explicit send/hold decision before any Debian interaction.

## Cleanup state

The local runtime could not resolve `github.com`, so no local checkout or package build was created in this continuation. No process, mount, sysroot, package installation, credential, or external state remains.

## Stop and reassess when

- Debian publishes an equivalent trixie correction;
- candidate execution still aborts or changes valid output;
- native tests identify an adjacent required patch;
- current public attachment behavior contradicts the deterministic fixture;
- external-contact authority changes.

## Other fork disposition

The recent fork inventory is retained at:

```text
notes/handoffs/2026-08-01-recent-fork-disposition.md
branch: coordination/recent-fork-disposition-2026-08-01
head: be3daff51e98328e1733ddd1e0b8ed68cce461fe
```

It records:

- mmdebstrap: technically saturated at named canonical/QEMU gates;
- libarchive: completed overlap evidence, public PR #3070 still active;
- systemd: formal lanes only, no exact investigation;
- BuildKit: broad ecosystem mention only;
- nixpkgs: broad harvesting/retirement lanes only.

Do not turn those forks into a new broad scan during priority-zero closeout.

## Authority reminder

Internal repository work, controlled branches, controlled-fork PR #1, Linux Fieldwork PR #404, builds, tests, packet updates, and issue checkpoints are authorized. No external issue, comment, email, pull request, merge request, review, or package upload is authorized. None occurred.
