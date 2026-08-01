# Unit 23 — util-linux `lscpu` cpuset error-path ownership backport

State: `HOLD`  
Priority-zero issue: #397, unit 23  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-23-util-linux-lscpu-cpuset`  
External contact authorized: `false`

## TL;DR

The canonical carriers concern a caller-visible cpuset pointer left dangling after `lib/path.c:ul_path_cpuparse()` frees it on parse failure. They do not implement the issue/index wording about deriving ownership from an owning cgroup mount.

Upstream commit `4581ede384f22983d6155768635ce43cb5304cb0` clears `*set` after the free. Current util-linux `master`, `stable/v2.40`, `stable/v2.41`, and `stable/v2.42` all contain that correction. Debian testing and unstable carry newer fixed upstream releases, while Debian trixie stable still ships `2.41-5`. The trixie source package uses upstream `2.41`, whose `lib/path.c` lacks the NULL assignment, and its published quilt series contains no cpuset, `lib/path.c`, or `4581ede` patch. The remaining plausible destination is therefore a Debian trixie package backport.

Fresh Linux Fieldwork retained tests passed 5/5 on 2026-08-01. This unit is held on exact Debian `2.41-5` package-level reproduction, patch application, build/test, and clean rerun before any authorization decision.

## Accomplished behavior

The proposed downstream correction preserves the existing parse error and frees the failed allocation, then clears the caller-visible output pointer. Ordinary later `lscpu` cleanup sees `NULL` and cannot free the same cpuset again.

## Why care

Malformed or transient CPU-list input can drive affected `lscpu` builds through a stale-pointer read and later duplicate free. The visible abort occurs in final `lscpu` cleanup, while the first ownership failure occurs in shared `lib/path.c`.

## Scope

### Included

- reconcile unit 23 with PR #387, issue #234, PR #239, util-linux issues #3641/#4401, and commits `4581ede...`/`3cd5f1d...`;
- verify current util-linux branch source;
- identify the remaining maintained downstream package destination;
- retain the canonical patch and a fresh deterministic regression receipt;
- prepare a bounded Debian trixie verification and submission path.

### Excluded

- a competing util-linux implementation;
- cgroup-mount selection logic, which has no support in the linked canonical carriers;
- external Debian, util-linux, Incus, Ubuntu, or other contact;
- claims that Debian trixie binaries were reproduced or rebuilt in this pass.

### Split boundary

The source fix and upstream stable-branch adoption are complete. This unit now owns only Debian trixie package-level verification/backport. Other downstreams still shipping affected 2.40/2.41 sources require separate package identities and evidence.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | util-linux |
| Canonical repository | `util-linux/util-linux` |
| Intended base branch | Debian trixie source package `util-linux 2.41-5` |
| Upstream base commit | upstream tag `v2.41`; `lib/path.c` blob `42a33ffc53752ba5e00aed2396ca9a4fc876c1ef` |
| Current upstream heads | `master` `fd82c4043fab942b889f478800118c66edfbc39f`; `stable/v2.40` `160b7e47d4e6ba0fd15e66b4041bbdc67d2c457f`; `stable/v2.41` `2dacaf3eea391e3bbf48e7d3ecce02cafe045b6d`; `stable/v2.42` `84796d917bcbad37aecfdadf36d71fee5b356efd` |
| Canonical fix | `4581ede384f22983d6155768635ce43cb5304cb0` |
| Stable backport identity | `3cd5f1dd69495864f3046cdbcefa104786fe5a27` |
| Controlled fork | upstream fork `teamleaderleo/util-linux`; Debian packaging fork `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` after exact package verification |
| Candidate head | `NONE` |
| Linux Fieldwork branch | `upstream/unit-23-util-linux-lscpu-cpuset` |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | retained canonical patch from Linux Fieldwork merge `4a2196a705c06f5604879f655d465a4ac6fcb198` |
| Patch or series path | `patches/0001-clear-cpuset-output-after-error.patch` |
| Proposed destination | Debian trixie stable util-linux package backport |
| Delivery method | `Debian BTS patch or follow-up` or Debian Salsa merge request after explicit decision |

## Canonical links

- Priority-zero unit: #397 unit 23
- Owning Linux Fieldwork issue: #234
- Canonical Linux Fieldwork PR: #387, merged as `4a2196a705c06f5604879f655d465a4ac6fcb198`
- Superseded predecessor carrier: draft PR #239
- Upstream reports: util-linux #3641 and #4401
- Upstream correction: util-linux `4581ede384f22983d6155768635ce43cb5304cb0`
- Stable cherry-pick: util-linux `3cd5f1dd69495864f3046cdbcefa104786fe5a27`
- Debian trixie package: `https://packages.debian.org/trixie/util-linux`
- Debian trixie patch series: `https://sources.debian.org/patches/util-linux/2.41-5/`
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- upstream `v2.41` frees `*set` on error and leaves the caller-visible pointer unchanged;
- canonical commit `4581ede...` adds `*set = NULL` immediately after that free;
- the original reporter confirmed the correction;
- current upstream `master` and stable/v2.40, v2.41, and v2.42 source contain free-then-NULL;
- Debian trixie stable remains at `2.41-5`;
- the published Debian `2.41-5` quilt series contains no cpuset, `lib/path.c`, or canonical-commit reference;
- the retained Linux Fieldwork matrix passes 5/5, including a losing fixture-drift control and zero-fuzz patch application.

### Not yet demonstrated

- execution of issue #4401's attached archive;
- exact Debian `2.41-5` source unpack, quilt application, build, package test, or binary reproduction;
- patched Debian package build and clean rerun;
- compatibility against ordinary valid `lscpu` output on the rebuilt package;
- Debian stable-update acceptance policy for this correction.

### Compatibility boundary

The correction changes only caller-visible ownership after an existing error. It preserves successful parsing, the parse failure status, ordinary output, and later NULL-safe cleanup. Package integration and architecture coverage remain unexecuted.

## Candidate organization

One downstream patch is sufficient:

1. `patches/0001-clear-cpuset-output-after-error.patch` — canonical util-linux authorship and one-file free-then-NULL correction.

Package metadata or changelog edits belong in the Debian packaging carrier after the destination and version are selected.

## Current disposition

`HOLD` — exact Debian trixie `util-linux 2.41-5` package-level reproduction, canonical patch application, build/test, and clean rerun have not run. The discriminator is a complete receipt showing the affected package fails or contains the stale-pointer source, the patch applies cleanly, the rebuilt package passes the focused reproducer and ordinary controls, and cleanup/rerun succeeds.

## Next human decision

After package-level verification, choose whether to authorize a Debian BTS follow-up, a Salsa merge request, or continued hold. No send decision is requested yet.

## Authority

Internal repository reads, branch creation, packet edits, retained-patch tests, package-source inspection, local builds, and issue checkpoints are authorized. No external contact has been authorized or made.
