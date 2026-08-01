# Current handoff

Updated: `2026-08-01 07:53 +08`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-06-chrootless-maintainer-boundary` |
| Linux Fieldwork head | this `HANDOFF.md` creation commit is the branch tip; parent before handoff: `3e026596f53c21273b72d922f31d38d5c73eb572`; exact creation SHA is recorded in the #397 UNIT CHECKPOINT |
| Upstream base repository/branch | `https://salsa.debian.org/debian/mmdebstrap`, `master` |
| Upstream base commit | current master unresolved; released/imported base `6fde999741f4fe1e7bf38079acf29432ef87a35e` (`debian/1.5.7-3`) |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `UNBUILT CURRENT-UPSTREAM CANDIDATE` |
| Patch or series | `patches/series`, four ordered patches |
| Owning issue/PR | #397 unit 06; #40, #69, #107, #337; PR #57, #74, #368 |
| Latest workflow/run/artifact | PR #368 run `30650100748`; artifact `8801028296`; digest `sha256:d8cad7c419c8982ce75bc5e7e6fb47ee6c246a283092a61defc9e4d41c225676` |

## Current bounded claim

Linux Fieldwork has exact component evidence for launch refusal and dpkg environment scrubbing, target-contained package temporaries, apt-configured inner command lookup, and absolute outer sanitizer lookup. The source corrections form one coherent four-patch series because every incomplete intermediate state has a demonstrated losing fixture. This pass retained that ordered series against the released/imported `1.5.7-3` topology. Current Salsa master application and complete final-state runtime evidence remain open.

## Work completed in this pass

- read issue #397, packet README/index, unit definition, and direct carrier chain;
- read LF-02 PR #22 and detailed comments that changed the unit decision;
- created and claimed branch `upstream/unit-06-chrootless-maintainer-boundary`;
- created the complete required unit packet;
- mapped exact source symbols, carrier heads/merges, runs, artifacts, and digests;
- reviewed the source hunks from PR #57 and PR #74 plus the retained PR #368 patches;
- decided one submission unit with four ordered commits;
- normalized patch paths for the canonical upstream repository root (`mmdebstrap`);
- retained four product patches and `patches/series`;
- drafted upstream issue and merge-request text without sending either;
- queried canonical Salsa and Debian Sources; confirmed released `1.5.7-3` and recorded current master as unresolved after access failures.

## Changed paths

- `upstream-packets/units/06-chrootless-maintainer-boundary/README.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/SOURCE_MAP.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/DEEP_DIVE.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/TESTS.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/DECISIONS.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/UPSTREAM_ISSUE.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/UPSTREAM_PR.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/HANDOFF.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/patches/series`
- `upstream-packets/units/06-chrootless-maintainer-boundary/patches/0001-sanitize-chrootless-maintainer-environment.patch`
- `upstream-packets/units/06-chrootless-maintainer-boundary/patches/0002-use-target-contained-tmpdir.patch`
- `upstream-packets/units/06-chrootless-maintainer-boundary/patches/0003-use-configured-dpkg-path.patch`
- `upstream-packets/units/06-chrootless-maintainer-boundary/patches/0004-use-absolute-env-wrapper.patch`

## Distinguishing observations

- PR #57's scrub correctly left apt ambient state outside the dpkg boundary, yet its first form omitted package TMPDIR and copied caller-prefixed PATH.
- PR #74's derived-path helper is stronger than PR #73's allowlist-only repair because the helper validates the path it emits and owns both call sites.
- PR #368 closes two separate executable-authority layers: configured inner PATH and absolute outer sanitizer.
- The imported source blob `41aa46f989a2660cebdb0138e0847cde25b269a3` already contains the environment and target-TMPDIR components. PR #368 reports its two retained patches apply to that source with zero fuzz.
- A complete upstream series must start from released/current source before all four corrections, so the packet retains PR #57, PR #74, and PR #368 changes in order.
- Debian Sources still exposes `1.5.7-3` for sid/forky and the matching tag commit. The exact Salsa master head could not be fetched here; no equality assumption was made.

## Gates completed

- direct carrier and source-hunk review;
- exact identity extraction for principal runs/artifacts/digests;
- operation ownership and compatibility review;
- patch ordering and overlap review;
- required packet completeness review;
- internal claim on #397.

## Red or neutral runs classified

- Salsa branch API/raw master fetch: failed in the web retrieval path;
- direct DNS-backed clone/download: failed with temporary name-resolution error;
- classification: environment/tooling access, with no product conclusion;
- product tests in this pass: neutral because none were executed.

## Cleanup state

No local product process, socket, mount, container, package transaction, or disposable target was started. No local source checkout was modified. Intentional retained state consists of the Linux Fieldwork branch, packet files, patch series, and internal #397 comments.

## First incomplete step

Resolve exact canonical Salsa `master` commit and blob, then run ordered patch application checks on a clean checkout.

## Next safe action

From an environment with working Salsa access and a Linux Fieldwork checkout at this branch:

```sh
set -eu
lf_root=$(git -C /path/to/linux-fieldwork rev-parse --show-toplevel)
work=$(mktemp -d)
git clone https://salsa.debian.org/debian/mmdebstrap.git "$work/mmdebstrap"
cd "$work/mmdebstrap"
base=$(git rev-parse HEAD)
printf 'upstream_base=%s\n' "$base"
series="$lf_root/upstream-packets/units/06-chrootless-maintainer-boundary/patches/series"
patchdir=${series%/series}
while IFS= read -r patch; do
    git apply --check "$patchdir/$patch"
    git apply "$patchdir/$patch"
done < "$series"
perl -c mmdebstrap
git diff --check
git diff -- mmdebstrap
```

Immediately record the exact base, any offset/conflict, final diff, and candidate commit in `README.md`, `SOURCE_MAP.md`, `TESTS.md`, and this handoff. If application succeeds, commit the four changes separately in series order, then adapt and run the landed PR #368 direct/APT transactions plus the PR #57/#74 detector and TMPDIR controls on the exact final head.

## Unresolved blockers

- technical: exact current master and full-series application are absent;
- compatibility: current native chrootless/fakeroot and complete owned-environment matrix are unrun;
- overlap: current Salsa issues/MRs and Debian BTS search are incomplete;
- environment or tooling: this session lacked reliable Salsa raw/API and DNS-backed clone access;
- authority: external contact remains unauthorized; controlled fork absent.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. issue #397 unit 06 and PRs #22, #57, #74, #368

## External-contact state

`false; none occurred`. The only public-system writes were internal Linux Fieldwork comments on issue #397 and commits to the authorized Linux Fieldwork branch.

## Do not repeat

- do not revive arbitrary caller PATH preservation;
- do not filter PATH components by writability/ownership probes;
- do not use bare `env` in either chrootless path;
- do not restore arbitrary caller TMPDIR;
- do not treat PR #73 as the final target-TMPDIR design;
- do not describe the scrub as a sandbox;
- do not claim broad caller locale or `DEBCONF_*` preservation;
- do not claim current master equals released `1.5.7-3` without exact identity;
- do not contact Salsa, Debian BTS, maintainers, or any external channel without explicit authorization.