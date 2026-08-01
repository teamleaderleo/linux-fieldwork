# Current handoff

Updated: `2026-08-01 16:14 +08`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE — four-patch candidate; system dpkg-config isolation split to HOLD`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-06-chrootless-maintainer-boundary` |
| Linux Fieldwork head | this handoff update is the branch tip; parent before handoff `148cc9034042f80e688952e2b266c9fd5424599f` |
| Canonical upstream repository/branch | `https://salsa.debian.org/debian/mmdebstrap`, `master` |
| Canonical upstream commit | unresolved in this runtime |
| Released/imported upstream identity | `6fde999741f4fe1e7bf38079acf29432ef87a35e`, `debian/1.5.7-3` |
| Controlled mirror/base | `teamleaderleo/mmdebstrap`, `master` at `574048f2a720057b75e56622003932f344dc700a` |
| Controlled mirror source blob | `075582e1ca9cf50a1be497105ba77c82345c2bf3` for `mmdebstrap` |
| Candidate mirror branch | `linux-fieldwork/unit-06-chrootless-maintainer-boundary` |
| Candidate head | `574048f2a720057b75e56622003932f344dc700a`; no product commit yet |
| Four-patch series | `patches/series` |
| Separate held evidence | `DPKG_CONFIG_DEEP_DIVE.md`, `scripts/run-dpkg-config-probe.sh`, `artifacts/dpkg-config-probe.txt` |
| Owning issue/PR | #397 unit 06; #40, #69, #107, #337; PR #22, #57, #74, #368 |
| Latest inherited workflow/run/artifact | PR #368 run `30650100748`; artifact `8801028296`; digest `sha256:d8cad7c419c8982ce75bc5e7e6fb47ee6c246a283092a61defc9e4d41c225676` |

## Current bounded claim

The four-patch product candidate addresses one operation boundary: construction of the host-side dpkg and maintainer-script launch environment in chrootless mode. Exact carrier evidence covers credential-rich launch refusal, dpkg environment scrubbing, target-contained package temporaries, configured inner command lookup, and absolute outer sanitizer lookup.

A deeper executable probe confirmed a second boundary. Removing `HOME` through `env -i` suppresses user `~/.dpkg.cfg`, but dpkg continues to read `/etc/dpkg/dpkg.cfg.d/*` and `/etc/dpkg/dpkg.cfg`. Controlled system `pre-invoke`, `post-invoke`, and `status-logger` commands executed under the scrubbed environment. Appending replacement command hooks did not remove the originals and produced deliberate losing results with status `141` after configured commands had already run.

Final `--path-include=*` and target-local `--log=...` neutralized the tested path-filter and log-destination classes. They do not isolate command hooks or unknown configuration options. System dpkg-config isolation is therefore a separate `HOLD`, not a fifth patch in the four-patch candidate.

## Work completed in this pass

- reread LF-02, issue #40, PR #368, and the unit packet around the user’s clarification about the chroot boundary;
- confirmed that LF-02 dynamically proved both caller credential/agent inheritance and host dpkg-config execution/mutation;
- reviewed current dpkg configuration semantics and separated user configuration from system configuration;
- wrote and executed a disposable synthetic-package probe against dpkg `1.22.22`;
- tested user `.dpkg.cfg` under inherited and scrubbed environments;
- tested a uniquely named temporary system fragment under scrubbed `env -i`;
- tested command-bearing `pre-invoke`, `post-invoke`, and `status-logger` options;
- tested final path-include and target-log controls;
- classified both status-141 runs as expected losing controls;
- verified removal of the temporary system configuration fragment;
- retained the exact runner and receipt with SHA-256 identities;
- wrote `DPKG_CONFIG_DEEP_DIVE.md` with correction directions and compatibility limits;
- updated README, TESTS, DECISIONS, and the upstream draft so the held boundary cannot be mistaken for a completed fix.

## Changed paths in this pass

- `upstream-packets/units/06-chrootless-maintainer-boundary/scripts/run-dpkg-config-probe.sh`
- `upstream-packets/units/06-chrootless-maintainer-boundary/artifacts/dpkg-config-probe.txt`
- `upstream-packets/units/06-chrootless-maintainer-boundary/DPKG_CONFIG_DEEP_DIVE.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/README.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/TESTS.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/DECISIONS.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/UPSTREAM_PR.md`
- `upstream-packets/units/06-chrootless-maintainer-boundary/HANDOFF.md`

Controlled mirror:

- candidate branch remains unchanged at `574048f2a720057b75e56622003932f344dc700a`;
- no source file or product branch commit was created in this pass.

## New probe identities

| Item | Value |
| --- | --- |
| Runner | `scripts/run-dpkg-config-probe.sh` |
| Receipt | `artifacts/dpkg-config-probe.txt` |
| Runner SHA-256 | `f5c73af6112006f79eb738438143deb4776a741aefac17d5850c0b6da0337edc` |
| Receipt SHA-256 | `ebc5df68f37350ea973fb5dbec39875cf1578a27dad88fa6dca2f1a2b72ebf76` |
| Dpkg version | `1.22.22` |
| Synthetic package | `lf-dpkg-config-probe` `1.0` |
| Cleanup receipt | `cleanup=system-config-absent` |

## Distinguishing observations

- Inherited user `HOME/.dpkg.cfg`: logger, pre-hook, and post-hook ran; configured path filtering changed target contents; configured log path was used.
- Scrubbed environment without `HOME`: user hooks and user log disappeared.
- Scrubbed environment did not disable ordinary system dpkg fragments already present in the runtime.
- Controlled system fragment under `env -i`: logger, pre-hook, and post-hook all ran.
- Appended replacement command hooks did not erase configured commands. Both losing cases returned `141` after the original logger/pre-hook ran.
- Final path include restored both controlled package paths.
- Final target-local log selected the target log path.
- The host needrestart result from LF-02 is the real-package form of the same system-config boundary.
- APT logind inhibition remains separate because exact APT options already remove that system-bus interaction.

## Gates completed

- exact user/system configuration distinction;
- controlled command-hook execution under inherited and scrubbed environments;
- controlled path-filter and log-destination distinctions;
- deliberate additive-hook losing controls;
- unique system-fragment cleanup and absence check;
- runner/receipt hash retention;
- packet claim and draft bounding review.

## Red or neutral runs classified

- `user/appended-controls`: `rc=141`; expected losing control; original logger and pre-hook had already executed;
- `system/appended-command-controls`: `rc=141`; expected losing control; original logger and pre-hook had already executed;
- shell clone remains unavailable because this runtime cannot resolve GitHub/Salsa hosts directly;
- connector reads/writes continue to work;
- no four-patch product conclusion was inferred from the probe.

## Cleanup state

The probe ran in an isolated task runtime with disposable package roots and one uniquely named system configuration fragment. The fragment was removed by the ordinary path and protected by an EXIT/HUP/INT/TERM trap. The final receipt verified `cleanup=system-config-absent`. No retained product process, socket, mount, target package tree, log, or system configuration file remains.

Intentional retained state consists of Linux Fieldwork packet commits, the probe/receipt/deep dive, the unchanged mirror candidate branch, and internal #397 coordination.

## First incomplete step

Apply the four retained patches in order to mirror branch `linux-fieldwork/unit-06-chrootless-maintainer-boundary`, preserving one reviewed commit per patch, then run syntax, formatting, complete-diff, direct transaction, APT transaction, fakeroot, cleanup, and rerun gates.

## Separate held step

After the four-patch candidate is applied, adapt the system-config probe to both actual mmdebstrap chrootless paths. Keep this as a separate correction decision:

1. prefer an official dpkg pre-parse configuration-selection interface;
2. otherwise prototype a fail-closed mmdebstrap preflight that rejects command-bearing and unknown system options while explicitly neutralizing only proven reversible classes;
3. consider a private namespace only if its authority and dependency cost are acceptable.

Do not mix an incomplete dpkg-config blacklist into the environment submission.

## Next safe action

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

Record all four commit SHAs and adapt the existing PR #57/#74/#368 fixtures to the exact final candidate. Add the retained dpkg-config system-fragment matrix only as an explicit non-goal/control for the four-patch submission.

## Unresolved blockers

- technical: four-patch mirror application and candidate commits are absent;
- compatibility: complete direct/APT/fakeroot matrix is unrun on the mirror candidate;
- dpkg-config policy: official configuration-disable interface versus fail-closed preflight remains unresolved;
- overlap: current Salsa issues/MRs and Debian BTS search remain incomplete;
- provenance: exact relation between mirror base and current Salsa `master` remains unresolved;
- tooling: direct shell clone/download remains blocked by runtime DNS;
- authority: external contact remains unauthorized; final destination remains undecided.

## Files to read first

1. `README.md`
2. `DPKG_CONFIG_DEEP_DIVE.md`
3. `TESTS.md`
4. `DECISIONS.md`
5. `UPSTREAM_PR.md`
6. `SOURCE_MAP.md`
7. PR #22 comments, issue #40, and PR #368

## External-contact state

`false; none occurred`. GitHub writes were confined to the authorized Linux Fieldwork repository. The controlled mmdebstrap mirror candidate was read but not changed in this pass. No Salsa or Debian issue, merge request, email, comment, review, release, or maintainer contact was created.

## Do not repeat

- do not describe the four-patch scrub as system dpkg-config isolation;
- do not add replacement status-loggers or invoke hooks as a reset strategy;
- do not fold APT logind inhibition into the dpkg-config correction;
- do not claim chrootless is sandboxed after environment clearing;
- do not ask the repository owner for another fork while the controlled mirror remains writable;
- do not present mirror commit `574048f2a720057b75e56622003932f344dc700a` as canonical Salsa identity;
- do not revive arbitrary caller PATH or TMPDIR preservation;
- do not use bare `env` in either chrootless path;
- do not contact Salsa, Debian BTS, maintainers, or any external channel without explicit authorization.