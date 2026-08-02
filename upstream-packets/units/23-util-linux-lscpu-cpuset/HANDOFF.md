# Handoff — unit 23 util-linux `lscpu` cpuset ownership

Handoff date: `2026-08-03`  
Worker or variant: `GPT-5.6 Thinking`  
State: `HOLD — exact stable-update composition run queued`  
External contact authorized: `false`  
External contact made: `none`

## Exact current identities

| Item | Identity |
| --- | --- |
| Linux Fieldwork repository | `teamleaderleo/linux-fieldwork` |
| Linux Fieldwork branch | `upstream/unit-23-util-linux-lscpu-cpuset` |
| Internal PR | #404 |
| Branch base / merge base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Parent before this handoff update | `d14a35d7353241f373e5af3da774aa75d1d52f93` |
| Final technical execution head | `ec46b09595a6769ccacdd26fe48ac9b50e619b0b` |
| Current workflow run | `30759405485` |
| Current workflow job | `91527130309` |
| Current hosted state | `queued` when this handoff was written |
| Workflow after queueing | manual-only at parent `9354a69019dfdadf702538103d49928da7d3ad1e` |
| Stable base source | Debian trixie `util-linux 2.41-5` |
| Proposed internal stable-update version | `2.41-5+deb13u1` |
| Canonical correction | util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` |
| Retained patch | `patches/0001-clear-cpuset-output-after-error.patch` |
| Composition runner | `scripts/build-trixie-stable-update.sh` |
| Preflight receipt | `artifacts/2026-08-03-stable-update-preflight.md` |

The final branch head containing this handoff is recorded in the issue #397 unit checkpoint.

## Executive result

Debian trixie `util-linux 2.41-5` remains the affected stable package. A deterministic 16-CPU sysroot makes its installed `lscpu` abort in text and JSON modes on malformed `cpu/online` content `5,12-%`; valid controls exit 0.

Exact Debian source retains the stale caller-visible cpuset pointer. Canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` clears the pointer after freeing it. The retained patch applies to Debian `2.41-5` with zero fuzz, and a prior patched binary-package build completed.

The prior exact-head package matrix proved:

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

Baseline malformed stderr contained:

```text
free(): double free detected in tcache 2
```

Valid text and JSON were byte-identical between baseline and candidate.

The controlled util-linux fork also passed its native build, focused `lscpu` test suite, and deterministic malformed-cpuset gate. The remaining unit boundary is Debian stable-update source composition and exact package evidence.

## Prior completed execution

### Exact Debian package matrix

```text
requested head: 7a82f99ceac6801536c78ba1c2d261bd6f0f3dc8
workflow run:   30692256031
job:            91348929951
conclusion:     success
artifact:       8817069887
artifact digest: sha256:2b544b399e779bbf577ade1e99249436879fa928b639c5026f116044b461ac25
```

Valid compatibility digests:

```text
text: a8fc5c5ebc663afec6c11259ac5804aa808325208215ce08844131fd8e0274c7
JSON: bc46275fd166aa84e37a80bcb26af0207b04551d6167696dda18dccc3e5dc1ed
```

Full receipt:

```text
artifacts/2026-08-02-exact-head-package-matrix.txt
```

### Controlled util-linux native gate

```text
repository: teamleaderleo/util-linux
stable fix: 3cd5f1dd69495864f3046cdbcefa104786fe5a27
CI base: linux-fieldwork/unit-23-lscpu-cpuset-native-base
CI base head: 7669d148543822d56ffffa31d2f399f078f8e117
CI gate: linux-fieldwork/unit-23-lscpu-cpuset-native-gate
CI gate head: 95ebc67e521195741040ffebb58756b259fb69b2
internal PR: teamleaderleo/util-linux#1
workflow run: 30691835019
job: 91347815601
conclusion: success
artifact: 8816802119
artifact digest: sha256:d36f713357713593430fca369e4871e5ce3ff8f4c8455e07a67e8d83b95493c4
```

The controlled fork remains an internal execution carrier. It proposes no competing product implementation.

## Exact source and prior candidate identities

| Item | Identity |
| --- | --- |
| Installed baseline | `util-linux 2.41-5 amd64` |
| Baseline binary SHA-256 | `e3c6e0c09d617cb9e77a3655f79a7a83d2dd865e49eabeccfbaa0335c9ff722e` |
| Debian `.dsc` SHA-256 | `9e84dcc64170262f850aa5fd65902846a1ebf054d556ab5c4ec17fa16b00e628` |
| Debian upstream tar SHA-256 | `81ee93b3cfdfeb7d7c4090cedeba1d7bbce9141fd0b501b686b3fe475ddca4c6` |
| Debian delta tar SHA-256 | `20ad832160d5ed8de4759ce00652f620ce642ab583c3c1c431b68a15cdba1d07` |
| Effective baseline `lib/path.c` SHA-256 | `f934339cf7aba38ae6197e5b5ad3b6a9e7e5fb483ed3f807d45971968d3c7cda` |
| Prior candidate `lib/path.c` SHA-256 | `d0460b4fa3a32b7bdd3cf8b95fa5780bf830fa24bc9e64559408c3ddd1abbb8d` |
| Prior candidate package SHA-256 | `92f3aa6fa87a30b9d030263dbbb0446f7679c2ee0456760271ea530268f6b971` |
| Prior candidate binary SHA-256 | `883912245c15612a224b761d01b838ecd23470eccf467369ec5c4a560a7946e1` |

## Work completed in this pass

- honored the repository-owner stop on mmdebstrap and moved to the non-mmdebstrap util-linux unit;
- refreshed issue #397, unit 23, PR #387, PR #404, controlled util-linux PR #1, the packet, and the retained source identities;
- confirmed Debian stable remains trixie and stable `util-linux` remains `2.41-5`;
- reviewed current Debian stable-update requirements and selected internal version `2.41-5+deb13u1` for the disposable composition;
- added `scripts/build-trixie-stable-update.sh`;
- made the runner preserve the existing quilt series and append one canonical patch;
- made the runner reject patch fuzz and offsets;
- added source-package build, source debdiff, binary build without `nocheck`, focused native `lscpu` suite twice, actual-binary matrix twice, cleanup, and rerun assertions;
- found and repaired the expected-`debdiff` exit-status trap before execution;
- pinned Actions checkout to the exact PR head instead of the synthetic merge ref;
- added full-history checkout so the complete base-to-head diff is available;
- queued the final technical execution at `ec46b09595a6769ccacdd26fe48ac9b50e619b0b`;
- changed the workflow to manual-only after queueing so packet documentation commits do not start more expensive builds;
- retained the preflight and environment classification in `artifacts/2026-08-03-stable-update-preflight.md`;
- maintained the live checkpoint on PR #404 comment `5159543666`.

## Hosted execution state

Current exact run:

```text
technical head: ec46b09595a6769ccacdd26fe48ac9b50e619b0b
workflow run:   30759405485
job:            91527130309
state:          queued when this handoff was written
```

Obsolete queued predecessors:

```text
30759234226 — predates expected-debdiff status handling
30759300129 — predates exact PR-head checkout
30759383187 — predates full-history diff availability
```

No conclusion may be taken from those predecessor runs.

## Composition gate contract

The exact runner must:

1. acquire Debian source `util-linux 2.41-5` in a disposable trixie tree;
2. verify the known source artifact identities;
3. preserve the existing Debian quilt series;
4. append the canonical patch with original authorship retained;
5. reject quilt fuzz or offsets;
6. create internal changelog version `2.41-5+deb13u1` for `trixie`;
7. build the source package;
8. retain a non-empty source debdiff and require `debdiff` status 1;
9. build binary packages without setting `DEB_BUILD_OPTIONS=nocheck`;
10. run the focused native `lscpu` suite twice;
11. extract the final candidate package;
12. run the valid/malformed text and JSON matrix twice;
13. require identical matrix receipts;
14. remove only the validated `/tmp/unit23-stable-update.*` disposable root.

## First incomplete step

Inspect workflow run `30759405485` and job `91527130309` once GitHub assigns a runner. Read the step-level result and logs, retain the artifact identities, and classify the first distinguishing owner.

Do not use an obsolete predecessor run as acceptance evidence.

## Next safe action

If the exact run is green:

1. download and inspect the source debdiff;
2. verify the final `.dsc`, package, binary, patch-series, changelog, native-test, matrix, cleanup, and rerun receipts;
3. update `README.md`, `TESTS.md`, `DECISIONS.md`, PR #404, this handoff, and issue #397;
4. move to `READY FOR AUTHORIZATION` only if the complete technical gate supports it;
5. leave Debian tracking/approval and any send action pending explicit authorization.

If the exact run is red:

1. identify the first failing owner: workflow, fixture, packaging, native test, product, cleanup, or evidence;
2. repair only that owner;
3. re-enable the manual gate for one exact rerun;
4. leave downstream assertions unchanged until the intended observation is reached.

## Current blockers and limits

- hosted execution: exact run `30759405485` remains queued;
- local environment: Debian trixie runtime has no Docker or Podman and cannot resolve `deb.debian.org`;
- product conclusion from local execution: none;
- architecture: successful actual-package evidence remains amd64-only;
- source package: final stable-update `.dsc` and source debdiff are not yet retained;
- native package tree: the new complete focused suite has not yet executed;
- public report attachment: util-linux issue #4401 attachment remains unexecuted against the final package pair;
- dynamic diagnostics: ASan and Valgrind actual-package runs remain unexecuted;
- process: Debian stable-update tracking bug and release-manager approval are external actions and remain unauthorized.

## Cleanup state

No local package build, container, mount, sysroot, package installation, credential, or external state was started in this pass. The local runtime probe created no retained disposable tree.

GitHub-side retained state consists of the Linux Fieldwork branch and draft PR, the manual composition workflow, queued workflow runs, the controlled util-linux branches and draft PR, logs, and artifacts.

## Security-adjacent boundary

The inherited defect is a malformed-input double free in `lscpu`. Current work uses public source, synthetic sysroots, owned repositories, and disposable package trees. It uses no live target, credential, authentication or authorization bypass, privilege gain, persistence, destructive external action, or external contact. Ordinary Linux Fieldwork handling remains appropriate.

## Stop and reassess when

- Debian publishes an equivalent trixie correction;
- the final package composition still aborts or changes valid output;
- native tests identify an adjacent required product patch;
- current public attachment behavior contradicts the deterministic fixture;
- external-contact authority changes;
- the investigation reaches real credentials, a live target, unauthorized authority, persistence, or disclosure-sensitive operational detail.

## Authority reminder

Internal repository work, controlled branches, controlled-fork PR #1, Linux Fieldwork PR #404, builds, tests, packet updates, and issue checkpoints are authorized. No Debian or util-linux issue, comment, email, pull request, merge request, review, package upload, or maintainer contact is authorized. None occurred.

## Do not repeat

- do not resume mmdebstrap unit 06; it is stopped at repository-owner direction;
- do not use `DEB_BUILD_OPTIONS=nocheck` as native-test evidence;
- do not accept a synthetic merge-ref checkout as exact-head evidence;
- do not treat `debdiff` status 1 as a failure when it reports the required source delta;
- do not overwrite the existing Debian patch series;
- do not use obsolete workflow runs `30759234226`, `30759300129`, or `30759383187` as acceptance evidence;
- do not describe a queued job as executed;
- do not contact Debian, util-linux, or any external channel without explicit authorization.
