# Unit 23 — util-linux `lscpu` cpuset error-path ownership backport

State: `HOLD`  
Priority-zero issue: #397, unit 23  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-23-util-linux-lscpu-cpuset`  
Internal review carrier: PR #404  
External contact authorized: `false`

## TL;DR

Debian trixie `util-linux 2.41-5` is proven affected. A deterministic 16-CPU sysroot with malformed `cpu/online` text `5,12-%` makes the installed `lscpu` abort in text and JSON modes with `free(): double free detected in tcache 2`.

Canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` clears the caller-visible cpuset slot after freeing it. It applies to the exact Debian source with `--fuzz=0`, and the patched binary package builds.

The exact-head Debian package matrix has now completed successfully. The baseline aborts on malformed text and JSON; the candidate exits 0 in both modes. Valid baseline and candidate text and JSON outputs are byte-identical. A controlled util-linux fork also passes its focused native build and regression test.

The unit remains `HOLD` only because a minimal Debian stable-update source delta, relevant native/package tests, source package, and source debdiff are still incomplete.

## Explain like I'm five

The parser allocates a box, discovers bad text, throws the box away, but forgets to erase the address written on a note. Later cleanup follows the stale address and throws away the same box again.

The stable fix erases the note after the first free. Debian trixie's package still has the stale note; the package rebuilt with the fix no longer crashes on the same input.

## Why care

Malformed or transient CPU-list input can make an essential package utility abort during ordinary cleanup. Containers and package-build environments can expose inconsistent topology snapshots, so the error path must preserve correct ownership even when the producer of malformed data is separate.

## Scope correction

Issue #397 names this unit as deriving cpuset ownership from an owning cgroup mount. Every canonical linked carrier instead identifies a caller-visible pointer ownership defect after parse failure in `lib/path.c:ul_path_cpuparse()`.

This packet follows the exact carriers and does not invent a second mount-selection defect. A distinct cgroup-mount issue requires its own source owner, reproducer, and carrier.

## Exact completed package matrix

- requested Linux Fieldwork head: `7a82f99ceac6801536c78ba1c2d261bd6f0f3dc8`;
- workflow run: `30692256031`;
- job: `91348929951`;
- conclusion: `success`;
- artifact: `8817069887`, `unit-23-util-linux-30692256031-1`;
- artifact digest: `sha256:2b544b399e779bbf577ade1e99249436879fa928b639c5026f116044b461ac25`.

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

Valid-output compatibility:

- text SHA-256, baseline and candidate: `a8fc5c5ebc663afec6c11259ac5804aa808325208215ce08844131fd8e0274c7`;
- JSON SHA-256, baseline and candidate: `bc46275fd166aa84e37a80bcb26af0207b04551d6167696dda18dccc3e5dc1ed`.

Full receipt: [`artifacts/2026-08-02-exact-head-package-matrix.txt`](artifacts/2026-08-02-exact-head-package-matrix.txt).

## Exact identities

| Identity | Value |
| --- | --- |
| Debian package base | `util-linux 2.41-5 amd64` |
| Installed baseline `lscpu` SHA-256 | `e3c6e0c09d617cb9e77a3655f79a7a83d2dd865e49eabeccfbaa0335c9ff722e` |
| Debian `.dsc` SHA-256 | `9e84dcc64170262f850aa5fd65902846a1ebf054d556ab5c4ec17fa16b00e628` |
| Debian upstream tar SHA-256 | `81ee93b3cfdfeb7d7c4090cedeba1d7bbce9141fd0b501b686b3fe475ddca4c6` |
| Debian delta tar SHA-256 | `20ad832160d5ed8de4759ce00652f620ce642ab583c3c1c431b68a15cdba1d07` |
| Effective Debian `lib/path.c` SHA-256 | `f934339cf7aba38ae6197e5b5ad3b6a9e7e5fb483ed3f807d45971968d3c7cda` |
| Canonical fix | `4581ede384f22983d6155768635ce43cb5304cb0` |
| Stable cherry-pick | `3cd5f1dd69495864f3046cdbcefa104786fe5a27` |
| Candidate `lib/path.c` SHA-256 | `d0460b4fa3a32b7bdd3cf8b95fa5780bf830fa24bc9e64559408c3ddd1abbb8d` |
| Candidate package SHA-256 | `92f3aa6fa87a30b9d030263dbbb0446f7679c2ee0456760271ea530268f6b971` |
| Candidate `lscpu` SHA-256 | `883912245c15612a224b761d01b838ecd23470eccf467369ec5c4a560a7946e1` |
| Retained patch | `patches/0001-clear-cpuset-output-after-error.patch` |
| Candidate delivery | Debian trixie stable update, after explicit authorization |

## Controlled util-linux fork

```text
repository: teamleaderleo/util-linux
CI base branch: linux-fieldwork/unit-23-lscpu-cpuset-native-base
CI base head: 7669d148543822d56ffffa31d2f399f078f8e117
CI gate branch: linux-fieldwork/unit-23-lscpu-cpuset-native-gate
CI gate head: 95ebc67e521195741040ffebb58756b259fb69b2
internal draft PR: teamleaderleo/util-linux#1
native regression run: 30691835019 — success
native regression job: 91347815601 — success
artifact: 8816802119
artifact digest: sha256:d36f713357713593430fca369e4871e5ce3ff8f4c8455e07a67e8d83b95493c4
```

The focused job completed autogen, configured and built `lscpu`, and passed `tests/ts/lscpu/cpuset-parse-failure` against the built executable.

The repository GCC workflow run `30691835043` passed x86_64, x86, coverage, and clang-analyzer jobs. The sampled armv7 qemu job reached and passed source build/test work, then failed while pulling `multiarch/qemu-user-static` because Docker Hub returned HTTP 429 unauthenticated pull-rate limiting. Other red qemu jobs require the same log-level confirmation before being described identically.

## Demonstrated

- affected upstream and effective Debian source free the failed cpuset without clearing the caller's slot;
- the installed trixie binary aborts on the bounded malformed fixture in text and JSON modes;
- valid controls exit 0;
- allocator reuse is a required dimension: a larger `kernel_max` losing control exits 0;
- the canonical patch applies to effective Debian source with `--fuzz=0`;
- the patched Debian binary package builds successfully;
- the candidate exits cleanly for malformed text and JSON;
- valid baseline and candidate outputs are byte-identical;
- the controlled fork's focused native regression passes;
- upstream master and stable/v2.40, v2.41, and v2.42 carry free-then-NULL;
- no external contact was made.

## Current hold

The technical send gate is not complete. Remaining work:

1. add the canonical patch to a disposable Debian quilt series and create a stable-update changelog version;
2. run the relevant native util-linux `lscpu` suite against the patched tree, not only the focused regression;
3. build source and binary packages without treating `DEB_BUILD_OPTIONS=nocheck` as test evidence;
4. retain a source debdiff against `2.41-5` and rerun the exact actual-binary matrix;
5. finish architecture/infrastructure classification where useful;
6. request a deliberate send/hold decision only after those records are complete.

## Evidence limits

The successful package execution is amd64-only. The binary-package build used `DEB_BUILD_OPTIONS=nocheck`. The complete native `lscpu` suite, source package, source debdiff, public attachment, ASan, and Valgrind package runs remain unexecuted.

## Authority

Internal source retrieval, builds, tests, packet updates, controlled branches, controlled-fork PR #1, Linux Fieldwork PR #404, and issue checkpoints are authorized. No external issue, comment, email, pull request, merge request, review, or package upload was authorized or made.
