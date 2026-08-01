# Unit 23 — util-linux `lscpu` cpuset error-path ownership backport

State: `HOLD`  
Priority-zero issue: #397, unit 23  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-23-util-linux-lscpu-cpuset`  
Internal review carrier: PR #404  
External contact authorized: `false`

## TL;DR

The linked carriers concern a caller-visible cpuset pointer left dangling after `lib/path.c:ul_path_cpuparse()` frees it on parse failure. They do not contain a cgroup-mount ownership implementation.

The exact Debian trixie package is affected. Debian 13 `util-linux 2.41-5` aborts with `free(): double free detected in tcache 2` when a deterministic 16-CPU sysroot supplies malformed `cpu/online` content `5,12-%`. Valid text and JSON controls exit 0. The complete malformed matrix reproduced twice from clean state.

Canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` clears `*set` after the error-path free. Exact Debian `2.41-5` source retains the stale output, the patch applies with zero fuzz, and a patched binary package builds successfully. Candidate binary execution remains queued in internal Actions runs `30690810870` and `30690831292`.

## Accomplished behavior

The proposed trixie correction preserves the parse failure, frees the failed allocation, and clears the caller-visible output pointer. Later `lscpu` cleanup sees `NULL` and cannot free the same allocation again.

## Why care

Malformed or transient CPU-list input can make an essential package utility abort during ordinary cleanup. The visible allocator failure occurs late; shared `lib/path.c` creates the stale ownership earlier.

## Scope

### Included

- canonical util-linux cause and fix mapping;
- exact Debian trixie package reproduction;
- exact Debian `2.41-5` source unpack and effective-source verification;
- zero-fuzz application of the canonical patch;
- patched binary-package build;
- deterministic actual-binary text and JSON matrix;
- Debian stable-update destination and send-gate drafting.

### Excluded

- a competing util-linux implementation;
- cgroup-mount selection logic;
- public Debian, util-linux, Incus, Ubuntu, or other contact;
- claims for candidate execution before the queued run completes;
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
| Branch base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Internal PR | #404 |
| Retained patch | `patches/0001-clear-cpuset-output-after-error.patch` |
| Candidate delivery | Debian trixie stable update, after explicit authorization |

## Canonical links

- Priority-zero unit: #397 unit 23
- Owning Linux Fieldwork issue: #234
- Canonical Linux Fieldwork evidence PR: #387, merge `4a2196a705c06f5604879f655d465a4ac6fcb198`
- Historical draft: PR #239
- Internal unit carrier: PR #404
- Upstream reports: util-linux #3641 and #4401
- Source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Handoff: [`HANDOFF.md`](HANDOFF.md)

## Current result

### Demonstrated

- affected upstream and effective Debian source free the failed cpuset without clearing the caller's slot;
- the installed trixie binary aborts on the bounded malformed fixture in text and JSON modes;
- valid text and JSON controls exit 0;
- the complete baseline matrix repeats from clean state;
- allocator reuse is a required dimension: a larger `kernel_max` losing control exits 0;
- the canonical patch applies to effective Debian source with `--fuzz=0`;
- a patched Debian binary package builds successfully;
- upstream master and stable/v2.40, v2.41, and v2.42 carry free-then-NULL;
- no util-linux upload appears in the current trixie proposed-updates queue.

### Pending

- actual execution of the built candidate binary from a retained package-build run;
- exact valid-output comparison between baseline and candidate;
- util-linux native `lscpu` test suite on the package tree;
- a proper `2.41-5+deb13u1` source delta and debdiff;
- architecture coverage and the exact public attachment archive.

## Candidate organization

1. canonical upstream patch in `debian/patches/upstream-stable/`;
2. one `debian/patches/series` entry;
3. one trixie changelog stanza using the stable-update version selected by Debian policy;
4. source debdiff and focused execution receipts.

## Current disposition

`HOLD` — exact source and package build are complete, while candidate actual-binary execution is queued. The clearing discriminator is a retained run in which the built candidate preserves valid text/JSON behavior and exits cleanly for malformed text/JSON, followed by native package tests and a minimal source debdiff.

## Next human decision

None yet. After the candidate and package-native gates pass, choose whether to authorize a Debian BTS report and stable-update request, a maintainer-directed packaging contribution, or continued hold.

## Authority

Internal source retrieval, builds, tests, packet updates, branches, commits, PR #404, and issue checkpoints are authorized. No external contact has been authorized or made.
