# Current handoff

Updated: `2026-08-01 07:27 UTC / 2026-08-01 15:27 UTC+08`  
Worker or variant: `ChatGPT`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-13-make-mirror-top-level-lifecycle` |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Canonical upstream repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Canonical upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Canonical upstream `make_mirror.sh` blob | `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Controlled fork | `teamleaderleo/mmdebstrap` |
| Fork provenance | fork of `deepin-community/mmdebstrap`; downstream packaging history |
| Fork default branch/head | `master` at `574048f2a720057b75e56622003932f344dc700a` |
| Fork `make_mirror.sh` blob | `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Candidate fork branch | `linux-fieldwork/unit-13-make-mirror-top-level-lifecycle` |
| Candidate branch head | `9c55456bb39290345b9f10934ddf3dd2a94a220b` |
| Candidate source status | source remains baseline; head adds temporary read-only verifier workflow only |
| Candidate source identity | PR #224 head `13b3c529e983b3ad967725f99f4e31d867fa4742` |
| Canonical patch blob | `25f9474945a6eb0efa52415f1fcd18e784655d59` |
| Packet patch | `patches/0001-make-mirror-top-level-signal-proxy-ownership.patch` |
| Verifier workflow | `.github/workflows/unit13-verify.yml` in controlled fork branch |
| Latest workflow state | no run/check surfaced for `9c55456b…`; likely Actions disabled or first-run approval required |
| Latest historical top-level run | Linux Fieldwork CI `30586490855` on PR #224 exact head |
| Latest complete review | PR #224 review `4823717630` |

The issue #397 checkpoint after this update records the exact Linux Fieldwork packet head.

## Current bounded claim

The canonical top-level patch converts cleanup-only signal traps into terminating owner cleanup, explicitly stops and waits for each proxy, closes both proxy launch-to-PID registration intervals while preserving the first signal, limits cache and QEMU cleanup to actual ownership, protects a published cache, suppresses later work after cancellation, and permits immediate unsignaled reruns.

Historical exact-head CI and complete review support that claim. Canonical upstream, Debian dgit, Linux Fieldwork import, and the controlled GitHub fork all carry the exact same `make_mirror.sh` blob. The controlled fork is therefore valid for unit 13 source application even though its repository history is a downstream packaging lineage.

## Work completed in this pass

- verified connector admin/push access to `teamleaderleo/mmdebstrap`;
- identified fork default branch `master` and exact head `574048f2a720057b75e56622003932f344dc700a`;
- confirmed the fork's latest history is Deepin packaging history rather than canonical upstream Forgejo history;
- confirmed fork `make_mirror.sh` blob `6c4be092…` exactly matches canonical upstream and the retained patch base;
- created controlled branch `linux-fieldwork/unit-13-make-mirror-top-level-lifecycle` from fork `master`;
- verified the new branch was initially identical to `master`;
- added a temporary, read-only push verifier at commit `9c55456bb39290345b9f10934ddf3dd2a94a220b`;
- verifier checks the exact base blob, applies the packet patch with `--fuzz=0` to a disposable tree, runs `/bin/sh -n`, and executes both retained focused regressions from the Linux Fieldwork packet branch;
- checked commit statuses and workflow-run lookup twice; no run or check surfaced;
- updated the packet README with exact controlled-fork identities and provenance;
- retried local `git clone`; the runner still failed DNS resolution before retrieval;
- made no canonical-upstream contact.

## Changed paths

Linux Fieldwork packet:

- `upstream-packets/units/13-make-mirror-top-level-lifecycle/README.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/HANDOFF.md`

Controlled fork branch:

- `.github/workflows/unit13-verify.yml`

The controlled fork source file remains unchanged at this stopping point.

## Distinguishing observations

- A full clone is unnecessary for branch and commit operations; the GitHub connector has sufficient write authority on the controlled fork.
- The local runner's blocker is DNS resolution, not missing repository permission.
- The user's fork is not a faithful canonical-history mirror, but exact changed-file identity makes it usable for this bounded unit.
- The candidate branch must be described as controlled execution transport, not as proof that the entire fork is current with upstream.
- The temporary verifier can supply fresh patch, syntax, and focused-test evidence through GitHub-hosted execution once Actions runs are enabled or approved.
- PR #224 remains the selected top-level patch. PRs #305/#324 remain unit 14.

## Gates completed

- fork permission check: admin/push available;
- fork branch creation: success;
- candidate branch initial relation to `master`: identical at `574048f2…`;
- fork source identity: exact match `6c4be092…`;
- verifier workflow commit: success at `9c55456b…`;
- historical baseline/candidate signal matrix: PASS;
- historical proxy reaping and immediate rerun: PASS;
- historical active-cache preservation: PASS;
- historical two-launch registration matrix: PASS twice consecutively;
- historical first-signal precedence: PASS;
- historical ownership-accurate launch-one and launch-two cleanup: PASS;
- PR #224 exact-head CI `30586490855`: PASS;
- PR #224 complete five-file review `4823717630`: PASS.

## Red or neutral runs classified

- current local clone retry: environment DNS failure before retrieval;
- GitHub verifier run lookup: neutral/no run surfaced; likely repository Actions state or first-run approval, not candidate evidence;
- #159 malformed hunk counts: patch packaging;
- #159 source/runtime path collision: fixture;
- #159 post-publication cleanup gap: product lifecycle, repaired;
- intermediate #224 pending-signal handoff race: product lifecycle, repaired;
- intermediate #224 launch-one cleanup overclaim: fixture/source fidelity, repaired.

## Cleanup state

The failed local clone created no usable checkout or test state. No proxy, socket, mount, container, mirror cache, or generated source tree remains. The controlled fork intentionally retains one candidate branch and its temporary read-only verifier workflow. Linux Fieldwork retains the exact patch and packet records.

## First incomplete step

Get the temporary verifier to execute on controlled-fork commit `9c55456bb39290345b9f10934ddf3dd2a94a220b`, then inspect its exact logs.

## Next safe action

Enable or approve GitHub Actions for `teamleaderleo/mmdebstrap` if its Actions page requests that one-time step. Then retrigger the branch push with a harmless workflow-only commit or use GitHub's rerun control. The expected verifier steps are:

```text
1. checkout controlled fork candidate branch;
2. checkout Linux Fieldwork packet branch;
3. require fork make_mirror.sh blob 6c4be092...;
4. apply packet patch with --fuzz=0 to a disposable tree;
5. run /bin/sh -n on the patched source;
6. run tests/test_make_mirror_signal_exit.py;
7. run tests/test_make_mirror_proxy_launch_ownership.py.
```

After a green verifier receipt, apply the source patch to `make_mirror.sh` on the controlled candidate branch as one source commit, remove the temporary workflow from the final source diff, and review the complete source change.

## Unresolved blockers

- technical: temporary verifier has no surfaced run; source patch remains unapplied on the candidate branch;
- compatibility: full mirror/APT/QEMU execution, escalation, HUP, process-group delivery, hostile descendants, and permanently blocking cleanup remain outside current evidence;
- overlap: no visible public equivalent was found; recheck immediately before any authorized submission;
- environment or tooling: local runner cannot resolve `github.com`; fork Actions may need one-time enablement/approval;
- provenance: fork history is downstream packaging history and must never be presented as canonical upstream ancestry;
- authority: canonical-upstream issue, PR, comment, email, review, and Forgejo fork activity remain unauthorized.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. this handoff
7. Linux Fieldwork #397 unit 13, issue #157, and PR #224
8. controlled fork branch and verifier workflow

## External-contact state

`false for canonical upstream; none occurred`.

The user supplied a personal GitHub fork. This pass created a branch and temporary verifier inside that controlled fork. No interaction occurred with canonical `josch/mmdebstrap`, its maintainers, its issue tracker, or its pull-request surface.

## Do not repeat

- do not treat the local DNS failure as a permission failure;
- do not require a custom MCP for ordinary GitHub branch/file operations;
- do not claim `teamleaderleo/mmdebstrap` mirrors canonical upstream history;
- do not select #159 or #205 as the complete top-level candidate;
- do not restore ordinary signal handlers before pending launch-signal dispatch;
- do not grant first-launch private-cache deletion ownership before readiness;
- do not combine PR #324's `update_cache()` finalizer into unit 13 without new upstream direction;
- do not contact canonical upstream without explicit authorization.