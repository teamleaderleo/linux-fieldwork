# Handoff

## Current state

State: `HOLD`  
Unit: issue #397, unit 23  
Branch: `upstream/unit-23-util-linux-lscpu-cpuset`  
Internal PR: #404  
Exact branch head before this packet-update commit: `8ba7537bda1f7fd15a659dfb918bbc8df110419d`  
Branch base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`  
External contact: unauthorized; none made

The final commit containing this handoff is recorded in the issue #397 unit checkpoint.

## Executive result

Debian trixie `util-linux 2.41-5` is proven affected. A deterministic 16-CPU sysroot makes the installed `lscpu` abort in both text and JSON modes with `free(): double free detected in tcache 2`; valid controls exit 0, and the matrix repeats from clean state.

Exact Debian source is also proven affected after its quilt series. Canonical util-linux commit `4581ede...` applies with zero fuzz and a patched binary package builds. The first Actions package run stopped only because its original fixture copied unreadable live sysfs power files. The script now creates a minimal deterministic sysroot.

## Completed in this continuation

- reproduced the defect against the exact installed trixie package;
- reduced the fixture to deterministic CPU/NUMA files;
- ran valid text and JSON controls;
- ran malformed text and JSON cases twice from clean state;
- retained a losing allocation-size control and a broader size sweep;
- added `scripts/reproduce-trixie-lscpu-cpuset.sh`;
- added `.github/workflows/unit-23-util-linux-lscpu.yml`;
- opened internal draft PR #404;
- unpacked exact Debian `2.41-5` source in Actions;
- recorded all source archive checksums;
- proved effective Debian `lib/path.c` retains the stale output;
- applied the canonical patch with `--fuzz=0`;
- completed a patched binary-package build;
- classified the first CI red as fixture copying rather than source, patch, or build failure;
- replaced the broad live-sysfs copy with a deterministic fixture;
- reviewed Debian stable-update requirements and current proposed-updates overlap;
- refreshed the complete packet and withheld drafts;
- made no external contact.

## Exact evidence

| Item | Identity |
| --- | --- |
| Installed baseline | `util-linux 2.41-5 amd64` |
| Baseline binary SHA-256 | `e3c6e0c09d617cb9e77a3655f79a7a83d2dd865e49eabeccfbaa0335c9ff722e` |
| Minimal matrix receipt | `artifacts/2026-08-01-trixie-minimal-sysroot-reproduction.txt` |
| Baseline result-file SHA-256 | `f842fa0f827a5ce72b96dd2d219177776ac6382e038dae122baf832ca132de00` |
| Source/build run | `30690487287`, job `91344214299` |
| Source/build artifact | `8815555088`; ZIP SHA-256 `ec7e883d7d0716123342c9dfcc01db8e4a8af97461d635467feddcbd51a41399` |
| Effective baseline path SHA-256 | `f934339cf7aba38ae6197e5b5ad3b6a9e7e5fb483ed3f807d45971968d3c7cda` |
| Candidate path SHA-256 | `d0460b4fa3a32b7bdd3cf8b95fa5780bf830fa24bc9e64559408c3ddd1abbb8d` |
| Candidate package SHA-256 | `92f3aa6fa87a30b9d030263dbbb0446f7679c2ee0456760271ea530268f6b971` |
| Candidate binary SHA-256 | `883912245c15612a224b761d01b838ecd23470eccf467369ec5c4a560a7946e1` |
| Retained upstream patch | `patches/0001-clear-cpuset-output-after-error.patch` |

## Latest distinguishing result

```text
baseline valid text: 0
baseline valid JSON: 0
baseline malformed text: 134
baseline malformed JSON: 134
stderr: free(): double free detected in tcache 2
clean rerun: byte-identical receipt

exact Debian source: stale output retained
canonical patch dry-run: pass, --fuzz=0
canonical patch application: pass, --fuzz=0
patched dpkg-buildpackage: pass
candidate execution: queued
```

## First incomplete step

Read the first completed deterministic-fixture package run:

- `30690810870` at head `187ab0c3c72eb4f733e5c9eebaeb7b748f687fbb`;
- `30690831292` at head `8ba7537bda1f7fd15a659dfb918bbc8df110419d`.

Fetch its job log and artifact. Require the built candidate to exit 0 for valid and malformed text/JSON cases and retain exact valid-output compatibility evidence.

## Next safe technical actions

1. classify the first completed queued run;
2. if green, retain artifact IDs, digests, binary outputs, cleanup, and rerun;
3. run the relevant native util-linux `lscpu` tests on the patched package tree;
4. add the canonical patch to a disposable Debian quilt series;
5. create an internal stable-update changelog version following current Debian guidance;
6. build source and binary packages;
7. retain a source debdiff against `2.41-5`;
8. rerun focused actual-binary and native tests cleanly;
9. update packet state to `READY FOR AUTHORIZATION` only when the technical send gate is complete;
10. seek an explicit human send/hold decision before any Debian interaction.

## Stop and reassess when

- Debian publishes an equivalent trixie correction;
- candidate execution still aborts or changes valid output;
- native tests identify an adjacent required patch;
- the exact public attachment contradicts the synthetic fixture;
- external-contact authority changes.

## Unexecuted gates

- built candidate actual-binary result;
- valid baseline/candidate byte comparison;
- native `lscpu` test suite;
- source package and debdiff;
- architecture matrix;
- public attachment execution;
- ASan/Valgrind actual-package run;
- Debian review or submission.

## Authority reminder

Internal work is authorized. No external issue, comment, email, pull request, merge request, review, or package upload is authorized. None occurred.
