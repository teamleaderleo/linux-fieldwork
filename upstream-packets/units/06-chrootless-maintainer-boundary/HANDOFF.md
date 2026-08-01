# Current handoff

Updated: `2026-08-01 15:25 +08`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-06-chrootless-maintainer-boundary` |
| Linux Fieldwork head | this handoff update is the branch tip; parent before handoff `ad29aaf7b566077f767579b26189a5cff44a88de` |
| Canonical upstream repository/branch | `https://salsa.debian.org/debian/mmdebstrap`, `master` |
| Canonical upstream commit | unresolved in this runtime |
| Released/imported upstream identity | `6fde999741f4fe1e7bf38079acf29432ef87a35e`, `debian/1.5.7-3` |
| Controlled mirror/base | `teamleaderleo/mmdebstrap`, `master` at `574048f2a720057b75e56622003932f344dc700a` |
| Controlled mirror source blob | `075582e1ca9cf50a1be497105ba77c82345c2bf3` for `mmdebstrap` |
| Candidate mirror branch | `linux-fieldwork/unit-06-chrootless-maintainer-boundary` |
| Candidate head | currently `574048f2a720057b75e56622003932f344dc700a`; no product commit yet |
| Patch or series | `patches/series`, four ordered patches |
| Owning issue/PR | #397 unit 06; #40, #69, #107, #337; PR #57, #74, #368 |
| Latest inherited workflow/run/artifact | PR #368 run `30650100748`; artifact `8801028296`; digest `sha256:d8cad7c419c8982ce75bc5e7e6fb47ee6c246a283092a61defc9e4d41c225676` |

## Current bounded claim

Linux Fieldwork has exact component evidence for launch refusal and dpkg environment scrubbing, target-contained package temporaries, apt-configured inner command lookup, and absolute outer sanitizer lookup. The corrections form one coherent four-patch series because every incomplete intermediate state has a demonstrated losing fixture.

A writable controlled mirror now exists and exposes an exact pre-hardening `1.5.7-3` source base. The mirror resolves candidate hosting and source retrieval. It does not establish current Salsa `master` identity and cannot serve directly as the head of a Salsa merge request.

## Work completed in this pass

- discovered the user-created controlled mirror `teamleaderleo/mmdebstrap` through the connected GitHub installation;
- verified repository write access and default branch `master`;
- resolved mirror base commit `574048f2a720057b75e56622003932f344dc700a`;
- resolved `mmdebstrap` source blob `075582e1ca9cf50a1be497105ba77c82345c2bf3`;
- inspected source lines 3890–3935 and confirmed the mirror base is pre-hardening at the chrootless boundary;
- created candidate branch `linux-fieldwork/unit-06-chrootless-maintainer-boundary` from exact mirror `master`;
- updated `README.md` and `SOURCE_MAP.md` with exact mirror, branch, base, blob, role, and delivery limitations;
- classified shell clone failure as this runtime's DNS limitation rather than user setup failure;
- confirmed no further setup action is required from the repository owner.

## Changed paths

Linux Fieldwork:

- `upstream-packets/units/06-chrootless-maintainer-boundary/README.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/SOURCE_MAP.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/HANDOFF.md`

Controlled mirror:

- created branch `linux-fieldwork/unit-06-chrootless-maintainer-boundary` from `master`;
- no source file changed yet.

## Distinguishing observations

- The controlled repository is a writable GitHub mirror with downstream history, not a direct fork whose commit IDs match canonical Salsa.
- Mirror `master` carries mmdebstrap `1.5.7-3` at commit `574048f2a720057b75e56622003932f344dc700a`.
- The mirror's `mmdebstrap` blob is `075582e1ca9cf50a1be497105ba77c82345c2bf3`.
- The inspected source range has no `chrootless_dpkg_environment`; `run_prepare()` flows directly into `run_essential()`. This is the expected pre-series topology.
- The earlier “NEEDS FORK” blocker is cleared for candidate development.
- Current Salsa identity remains a later provenance/delivery gate, not a user setup task.

## Gates completed

- connected-repository discovery;
- repository permission check;
- exact mirror commit resolution;
- exact source blob resolution;
- relevant pre-hardening source-range inspection;
- controlled candidate branch creation;
- packet identity and handoff update.

## Red or neutral runs classified

- shell `git clone` from GitHub failed with `Could not resolve host: github.com`;
- GitHub connector reads and writes succeeded;
- classification: local runtime DNS limitation;
- product conclusion: none;
- user action required: none.

## Cleanup state

No product process, socket, mount, container, package transaction, or disposable target was started. The failed shell clone created no retained checkout. Intentional retained state consists of the Linux Fieldwork packet commits and the controlled mirror candidate branch.

## First incomplete step

Apply the four retained patches in order to mirror branch `linux-fieldwork/unit-06-chrootless-maintainer-boundary`, preserving one reviewed commit per patch, then run syntax and diff checks.

## Next safe action

In any environment with a checkout of both repositories and ordinary GitHub access:

```sh
set -eu
lf_root=$(git -C /path/to/linux-fieldwork rev-parse --show-toplevel)
mm_root=$(git -C /path/to/mmdebstrap rev-parse --show-toplevel)

git -C "$mm_root" fetch origin
git -C "$mm_root" checkout linux-fieldwork/unit-06-chrootless-maintainer-boundary
test "$(git -C "$mm_root" rev-parse HEAD)" = 574048f2a720057b75e56622003932f344dc700a

series="$lf_root/upstream-packets/units/06-chrootless-maintainer-boundary/patches/series"
patchdir=${series%/series}
while IFS= read -r patch; do
    git -C "$mm_root" apply --check "$patchdir/$patch"
    git -C "$mm_root" apply "$patchdir/$patch"
    git -C "$mm_root" add mmdebstrap
    git -C "$mm_root" commit -m "${patch%.patch}"
done < "$series"

perl -c "$mm_root/mmdebstrap"
git -C "$mm_root" diff --check master...HEAD
git -C "$mm_root" log --oneline --decorate master..HEAD
git -C "$mm_root" diff --stat master...HEAD
```

Record each resulting commit SHA, patch application result, syntax result, and complete diff review in `README.md`, `SOURCE_MAP.md`, `TESTS.md`, and this handoff. Then adapt the landed PR #368 direct/APT transactions plus the PR #57/#74 detector and TMPDIR controls to the exact candidate head.

## Unresolved blockers

- technical: four-patch application and candidate commits are absent;
- compatibility: native chrootless/fakeroot and complete owned-environment matrix are unrun on the mirror candidate;
- overlap: current Salsa issues/MRs and Debian BTS search remain incomplete;
- provenance: exact relation between mirror base and current Salsa `master` is unresolved;
- environment or tooling: this runtime cannot shell-clone because DNS is blocked, though GitHub connector operations work;
- authority: external contact remains unauthorized; final destination remains undecided.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. issue #397 unit 06 and PRs #22, #57, #74, #368

## External-contact state

`false; none occurred`. GitHub writes were confined to the authorized Linux Fieldwork repository and the user's controlled mmdebstrap mirror. No issue, pull request, merge request, comment, review, email, or maintainer contact was created outside Linux Fieldwork coordination.

## Do not repeat

- do not ask the repository owner to fetch Salsa;
- do not ask for another fork while `teamleaderleo/mmdebstrap` remains writable;
- do not present mirror commit `574048f2a720057b75e56622003932f344dc700a` as a canonical Salsa commit;
- do not revive arbitrary caller PATH preservation;
- do not filter PATH components by writability/ownership probes;
- do not use bare `env` in either chrootless path;
- do not restore arbitrary caller TMPDIR;
- do not treat PR #73 as the final target-TMPDIR design;
- do not describe the scrub as a sandbox;
- do not claim broad caller locale or `DEBCONF_*` preservation;
- do not contact Salsa, Debian BTS, maintainers, or any external channel without explicit authorization.