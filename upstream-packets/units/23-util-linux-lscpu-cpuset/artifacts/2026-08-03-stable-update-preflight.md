# Unit 23 Debian stable-update preflight

Date: `2026-08-03`  
State: `execution queued; no package conclusion from this pass`  
External contact: `unauthorized; none occurred`

## Question

Can Debian trixie source `util-linux 2.41-5` carry canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` as a minimal `2.41-5+deb13u1` quilt/changelog delta, then pass source build, binary build without `DEB_BUILD_OPTIONS=nocheck`, the focused native `lscpu` suite twice, source debdiff review, and the actual valid/malformed text and JSON matrix twice?

## Current Debian adoption recheck

Official Debian pages inspected during this pass show:

- Debian 13 `trixie` is the current stable release; Debian 13.6 was released on 2026-07-11.
- The stable `util-linux` binary and source package remain version `2.41-5`.
- Debian Sources still lists `util-linux 2.41-5` for trixie.
- Newer `2.42.2-*` source exists in testing/unstable, so the correction is represented by a newer upstream line outside stable.

Sources:

- `https://www.debian.org/releases/`
- `https://www.debian.org/News/2026/20260711.en.html`
- `https://packages.debian.org/stable/utils/util-linux`
- `https://packages.debian.org/source/stable/util-linux`
- `https://sources.debian.org/src/util-linux/`

No equivalent trixie package version displaced this lane during the recheck.

## Stable-update composition rules used

Debian Developer's Reference section 5 requires stable-update proposals to keep the fix minimal, use a correct stable version such as `+deb13u1`, include a detailed changelog entry, include the source debdiff, and explain testing. The composed runner therefore selects:

```text
base version:   2.41-5
update version: 2.41-5+deb13u1
distribution:   trixie
```

Reference:

- `https://www.debian.org/doc/manuals/developers-reference/ch05.en.html`

This internal composition does not create the required Debian tracking bug or request stable-release-manager approval. Those are external actions and remain unauthorized.

## Patch-series observation

The Debian Sources patch index has inconsistent summary text: its package index says `2.41-5` has no patches, while individual `2.41-5` patch pages exist, including Debian and upstream-stable patches. The runner does not rely on the summary. It preserves the existing `debian/patches/series`, appends one uniquely named canonical patch, and asks quilt to apply only the pending entry.

Examples inspected:

- `https://sources.debian.org/patches/util-linux/2.41-5/debian/login-turn-off-btmp-utmp-lastlog-writing.patch/`
- `https://sources.debian.org/patches/util-linux/2.41-5/upstream-stable/libmount-avoid-strcasecmp-for-ASCII-only-strings.patch/`

## New executable gate

Added:

```text
upstream-packets/units/23-util-linux-lscpu-cpuset/scripts/build-trixie-stable-update.sh
```

The runner:

1. acquires exact source `2.41-5` in a disposable trixie tree;
2. verifies the retained source artifact identities;
3. adds the canonical patch to the existing quilt series;
4. rejects quilt fuzz or offsets;
5. adds internal changelog version `2.41-5+deb13u1` for `trixie`;
6. builds a source package;
7. retains a source debdiff;
8. builds binary packages without setting `DEB_BUILD_OPTIONS=nocheck`;
9. runs the project-native focused `lscpu` suite twice;
10. extracts the candidate package and runs the existing baseline/candidate actual-binary matrix twice;
11. requires both matrix result receipts to be identical;
12. removes the disposable source and extracted-package roots through a validated `/tmp/unit23-stable-update.*` cleanup target.

## Pre-execution review corrections

### Expected `debdiff` status

`debdiff` returns status 1 when differences are reported. Since a stable-update source package must differ from the base, status 1 is the expected evidence result. The runner now:

- accepts exactly status 1;
- rejects status 0 as an empty delta;
- treats every other status as an error.

Reference:

- `https://manpages.debian.org/trixie/devscripts/debdiff.1.en.html`

### Exact pull-request head

`actions/checkout` on a pull-request event normally selects a synthetic merge ref. The workflow now pins the checkout to the pull-request head SHA, records the expected and checked-out identities, and requires equality.

### Complete diff availability

An exact-SHA checkout with the default shallow depth can omit the pull-request base commit. The workflow now uses `fetch-depth: 0` before running the complete diff check.

## Exact hosted execution state

Final technical execution head:

```text
ec46b09595a6769ccacdd26fe48ac9b50e619b0b
```

Current run:

```text
workflow run: 30759405485
job:          91527130309
state:        queued when this artifact was written
```

Obsolete queued predecessors:

```text
30759234226 — predates expected-debdiff status handling
30759300129 — predates exact PR-head checkout
30759383187 — predates full-history diff availability
```

No conclusion may be taken from those predecessor runs.

After queueing the exact technical head, the workflow trigger was changed to manual-only to prevent packet documentation updates from starting additional expensive package builds. The queued run remains anchored to `ec46b095...`.

## Local runtime classification

The current local runtime is Debian 13 trixie and has `dpkg-buildpackage`, `patch`, `make`, and a C compiler. It has no Docker or Podman executable and DNS resolution for `deb.debian.org` is unavailable. It cannot reproduce the disposable package gate locally.

Classification:

```text
owner: environment/tooling
product conclusion: none
```

## Security-adjacent boundary

The inherited defect is a malformed-input double free in `lscpu`. This pass uses public source, synthetic sysroots, owned repositories, and disposable package trees. It uses no live target, credential, authorization bypass, persistence, privilege gain, or external mutation. Ordinary Linux Fieldwork handling remains appropriate.

## First incomplete step

Obtain and inspect the exact-head result for workflow run `30759405485`, retain its artifacts, and classify the first distinguishing step. If green, review the source debdiff and exact package identities, update the packet, and decide whether the technical gate supports `READY FOR AUTHORIZATION`. If red, repair the first owning layer without changing downstream assertions.
