# Unit 23 — util-linux `lscpu` cpuset error-path ownership backport

State: `HOLD`  
Priority-zero issue: #397, unit 23  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-23-util-linux-lscpu-cpuset`  
Internal review carrier: PR #404  
External contact authorized: `false`

## TL;DR

Debian trixie `util-linux 2.41-5` is proven affected. A deterministic 16-CPU sysroot with malformed `cpu/online` text `5,12-%` makes the installed `lscpu` abort in text and JSON modes with `free(): double free detected in tcache 2`; valid controls exit 0 and the full baseline matrix repeats from clean state.

Canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` clears the caller-visible cpuset slot after freeing it. The stable cherry-pick `3cd5f1dd69495864f3046cdbcefa104786fe5a27` exists in the controlled fork `teamleaderleo/util-linux` and is now the exact source anchor for a fork-only native gate.

```text
controlled repository: teamleaderleo/util-linux
stable fix: 3cd5f1dd69495864f3046cdbcefa104786fe5a27
CI base branch: linux-fieldwork/unit-23-lscpu-cpuset-native-base
CI base head: 7669d148543822d56ffffa31d2f399f078f8e117
CI gate branch: linux-fieldwork/unit-23-lscpu-cpuset-native-gate
CI gate head: 95ebc67e521195741040ffebb58756b259fb69b2
internal draft PR: teamleaderleo/util-linux#1
focused native run: 30691835019 — queued
repository build run: 30691835043 — queued
```

The earlier exact Debian package runs `30690810870` and `30690831292` are also queued. The current blocker is hosted execution capacity, rather than source, patch, or fixture design.

## Explain like I'm five

The parser allocates a box, discovers bad text, throws the box away, but forgets to erase the address written on a note. Later cleanup follows the stale address and throws away the same box again.

The stable fix erases the note after the first free. The remaining job is to execute the fixed binary through the real project tests and the exact malformed-input cases.

## Why care

Malformed or transient CPU-list input can make an essential package utility abort during ordinary cleanup. The allocator message appears late, while the shared `lib/path.c` helper creates the stale ownership earlier. Clearing the output slot preserves the original parse failure and prevents caller cleanup from freeing the same allocation twice.

## Scope

### Included

- canonical util-linux cause and fix mapping;
- exact Debian trixie package reproduction;
- exact Debian `2.41-5` source and zero-fuzz patch application;
- patched binary-package build;
- deterministic text/JSON matrix and clean rerun;
- controlled util-linux fork branches and internal execution PR;
- project-native `lscpu` test path;
- Debian stable-update destination and send-gate drafting.

### Excluded

- a competing util-linux product implementation;
- cgroup-mount selection logic;
- public Debian, util-linux, Incus, Ubuntu, or other contact;
- claims for queued runs before their jobs start;
- architecture-wide or sanitizer coverage.

### Split boundary

Upstream source ownership and stable-branch adoption are complete. This unit owns only the Debian trixie package backport decision. Other distributions require separate package identities and receipts.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | util-linux |
| Canonical repository | `util-linux/util-linux` |
| Affected upstream base | tag `v2.41`; `lib/path.c` blob `42a33ffc53752ba5e00aed2396ca9a4fc876c1ef` |
| Canonical fix | `4581ede384f22983d6155768635ce43cb5304cb0` |
| Stable cherry-pick | `3cd5f1dd69495864f3046cdbcefa104786fe5a27` |
| Controlled fork | `teamleaderleo/util-linux` |
| Fork CI base | `linux-fieldwork/unit-23-lscpu-cpuset-native-base` at `7669d148543822d56ffffa31d2f399f078f8e117` |
| Fork CI head | `linux-fieldwork/unit-23-lscpu-cpuset-native-gate` at `95ebc67e521195741040ffebb58756b259fb69b2` |
| Fork internal PR | `teamleaderleo/util-linux#1` |
| Fork native run | `30691835019`, queued |
| Fork repository run | `30691835043`, queued |
| Debian package base | `util-linux 2.41-5` |
| Debian `.dsc` SHA-256 | `9e84dcc64170262f850aa5fd65902846a1ebf054d556ab5c4ec17fa16b00e628` |
| Debian upstream tar SHA-256 | `81ee93b3cfdfeb7d7c4090cedeba1d7bbce9141fd0b501b686b3fe475ddca4c6` |
| Debian delta tar SHA-256 | `20ad832160d5ed8de4759ce00652f620ce642ab583c3c1c431b68a15cdba1d07` |
| Effective Debian `lib/path.c` SHA-256 | `f934339cf7aba38ae6197e5b5ad3b6a9e7e5fb483ed3f807d45971968d3c7cda` |
| Candidate `lib/path.c` SHA-256 | `d0460b4fa3a32b7bdd3cf8b95fa5780bf830fa24bc9e64559408c3ddd1abbb8d` |
| Built candidate package SHA-256 | `92f3aa6fa87a30b9d030263dbbb0446f7679c2ee0456760271ea530268f6b971` |
| Built candidate `lscpu` SHA-256 | `883912245c15612a224b761d01b838ecd23470eccf467369ec5c4a560a7946e1` |
| Installed baseline `lscpu` SHA-256 | `e3c6e0c09d617cb9e77a3655f79a7a83d2dd865e49eabeccfbaa0335c9ff722e` |
| Linux Fieldwork branch | `upstream/unit-23-util-linux-lscpu-cpuset` |
| Internal Fieldwork PR | #404 |
| Retained patch | `patches/0001-clear-cpuset-output-after-error.patch` |
| Fork receipt | `artifacts/2026-08-01-controlled-util-linux-fork.txt` |
| Candidate delivery | Debian trixie stable update, after explicit authorization |

## Canonical links

- Priority-zero unit: #397 unit 23
- Owning Linux Fieldwork issue: #234
- Canonical Linux Fieldwork evidence PR: #387, merge `4a2196a705c06f5604879f655d465a4ac6fcb198`
- Historical draft: PR #239
- Internal unit carrier: PR #404
- Controlled execution carrier: `teamleaderleo/util-linux#1`
- Upstream reports: util-linux #3641 and #4401
- Source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Handoff: [`HANDOFF.md`](HANDOFF.md)

## Demonstrated

- affected upstream and effective Debian source free the failed cpuset without clearing the caller's slot;
- the installed trixie binary aborts on the bounded malformed fixture in text and JSON modes;
- valid text and JSON controls exit 0;
- the complete baseline matrix repeats from clean state;
- allocator reuse is a required dimension: a larger `kernel_max` losing control exits 0;
- the canonical patch applies to effective Debian source with `--fuzz=0`;
- a patched Debian binary package builds successfully;
- upstream master and stable/v2.40, v2.41, and v2.42 carry free-then-NULL;
- the controlled fork contains the exact stable cherry-pick;
- the fork-only native carrier uses util-linux's own setup/build scripts and documented `make check` path;
- no util-linux upload appears in the retained trixie proposed-updates observation.

## Fork-native gate

The controlled PR changes execution files only. It performs:

```sh
.github/workflows/cibuild-setup-ubuntu.sh
.github/workflows/cibuild.sh CONFIGUREFAST MAKE
make check-programs
sudo -E make check TS_OPTS="--parallel=1 lscpu"
```

It then runs valid and malformed text/JSON sysroot cases twice against the built `./lscpu`, requiring status 0, valid JSON, no allocator-abort diagnostics, retained source/binary identities, cleanup, and rerun evidence.

## Pending

- first completed exact Debian package run;
- first completed fork-native run;
- exact valid-output comparison between Debian baseline and package candidate;
- util-linux native `lscpu` results and retained artifacts;
- a proper `2.41-5+deb13u1` source delta and debdiff;
- architecture coverage and the exact public attachment archive.

## Current disposition

`HOLD` — exact source, Debian reproduction, patch application, package build, controlled fork, and native-gate design are complete. Four hosted runs remain queued.

The clearing discriminator is a retained exact-head run in which the fixed candidate preserves valid behavior, exits cleanly for malformed text/JSON, passes the native `lscpu` suite, completes cleanup, and reruns cleanly. A minimal source debdiff remains required after execution evidence is retained.

## Next human decision

None yet. After the candidate and package-native gates pass, choose whether to authorize a Debian BTS report and stable-update request, a maintainer-directed packaging contribution, or continued hold.

## Authority

Internal source retrieval, builds, tests, packet updates, controlled branches, controlled-fork PR #1, Linux Fieldwork PR #404, and issue checkpoints are authorized. No external contact has been authorized or made.
