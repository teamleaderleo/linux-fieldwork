# Current handoff

Updated: `2026-08-01 00:05 UTC / 2026-07-31 17:05 PDT`  
Worker or variant: `ChatGPT`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-13-make-mirror-top-level-lifecycle` |
| Last complete packet head before this handoff commit | `30fcb240e5241e1041a9b734d753b17280273c13` |
| Branch base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Upstream `make_mirror.sh` blob | `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Candidate fork/branch | `NEEDS FORK / NEEDS BRANCH` |
| Candidate source identity | PR #224 head `13b3c529e983b3ad967725f99f4e31d867fa4742` |
| Canonical patch blob | `25f9474945a6eb0efa52415f1fcd18e784655d59` |
| Packet patch | `patches/0001-make-mirror-top-level-signal-proxy-ownership.patch` |
| Owning issue/PR | Linux Fieldwork #157; canonical merged carrier #224; priority unit #397/13 |
| Latest top-level workflow/run | Linux Fieldwork CI `30586490855` on #224 exact head |
| Latest complete review | PR #224 review `4823717630` |

The issue #397 `UNIT CHECKPOINT` posted after this file records the exact branch tip carrying the handoff.

## Current bounded claim

The canonical top-level patch converts cleanup-only signal traps into terminating owner cleanup, explicitly stops and waits for each proxy, closes both proxy launch-to-PID registration intervals while preserving the first signal, limits cache and QEMU cleanup to actual ownership, protects a published cache, suppresses later work after cancellation, and permits immediate unsignaled reruns.

Historical exact-head CI and complete review support that claim. Public-source lookup on 2026-08-01 confirms that upstream and Linux Fieldwork still share the exact `make_mirror.sh` blob. This pass did not produce a fresh executable result because repository checkout failed at DNS resolution before retrieval.

## Work completed in this pass

- read issue #397, its durable packet protocol, and unit index;
- claimed unit 13 internally and created the canonical unit branch from current `main`;
- read issue #157 and every carrier listed for unit 13: PRs #159, #205, #224, #305, and #324, including comments, reviews, and patches;
- reconstructed the top-level parent repair, launch-registration follow-up, first-signal repair, ownership-model repair, and worker-subshell split;
- selected PR #224 as the canonical top-level patch;
- verified public Forgejo `main` commit and exact source blob through read-only public sources;
- searched the public issue/PR surfaces for visible equivalent work and found no matching carrier;
- copied the exact canonical patch into the unit packet;
- wrote source map, deep dive, test matrix, issue draft, pull-request draft, decision log, summary, and this handoff;
- attempted a fresh local checkout for zero-fuzz application and focused execution;
- classified the checkout failure as environment DNS before repository retrieval;
- performed no public upstream contact.

## Changed paths

- `upstream-packets/units/13-make-mirror-top-level-lifecycle/README.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/SOURCE_MAP.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/DEEP_DIVE.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/TESTS.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/UPSTREAM_ISSUE.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/UPSTREAM_PR.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/DECISIONS.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/HANDOFF.md`
- `upstream-packets/units/13-make-mirror-top-level-lifecycle/patches/0001-make-mirror-top-level-signal-proxy-ownership.patch`

## Distinguishing observations

- PR #205's parent repair remained correct for cleanup, result, reaping, rerun, and publication, yet left two child-launch/PID-registration intervals.
- PR #224 closes both intervals through temporary first-signal handlers and delayed ordinary-trap restoration.
- The first launch occurs before private-cache deletion ownership. Final tests correctly require zero signal-time cache deletion calls there and use startup preflight for retained-state cleanup on rerun.
- The second launch occurs after private-cache ownership begins and requires private-cache deletion on cancellation.
- An intermediate #224 design restored ordinary handlers before pending dispatch; a later INT could replace a retained TERM. Final #224 dispatches while launch handlers remain active.
- PRs #305/#324 target the `update_cache()` pipeline subshell and belong to unit 14 despite sharing `make_mirror.sh`.
- Public Forgejo `main` head `77ec9be5417ee44c96343d2347145585da1b1f94`, Debian dgit, and Linux Fieldwork imported source identify the same `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590`.

## Gates completed

- historical baseline/candidate signal matrix: PASS;
- historical proxy reaping and immediate rerun: PASS;
- historical active-cache preservation: PASS;
- historical two-launch registration matrix: PASS twice consecutively;
- historical first-signal precedence: PASS;
- historical ownership-accurate launch-one and launch-two cleanup: PASS;
- historical exact patch dry-run and complete `/bin/sh -n`: PASS;
- PR #224 exact-head CI `30586490855`: PASS;
- PR #224 complete five-file review `4823717630`: PASS;
- current public source identity lookup: MATCH;
- public overlap search: no visible equivalent carrier found.

## Red or neutral runs classified

- current pass local clone: environment DNS failure before retrieval;
- #159 malformed hunk counts: patch packaging;
- #159 source/runtime path collision: fixture;
- #159 weak retained-trap assertion: evidence assertion;
- #159 post-publication cleanup gap: product lifecycle, repaired;
- intermediate #224 pending-signal handoff race: product lifecycle, repaired;
- intermediate #224 launch-one cleanup overclaim: fixture/source fidelity, repaired.

## Cleanup state

The failed local clone created only `/tmp/lf-unit13` before DNS resolution stopped repository retrieval. No checkout, patched source, child process, proxy, socket, mount, container, mirror cache, or generated test state remained. The packet intentionally retains the canonical patch and written evidence on the unit branch.

## First incomplete step

Retrieve the exact public upstream base and prove zero-fuzz application plus complete shell syntax for the packet patch.

## Next safe action

From an environment with repository DNS access:

```sh
set -eu

rm -rf /tmp/lf-unit13-next /tmp/mmdebstrap-unit13

git clone --branch upstream/unit-13-make-mirror-top-level-lifecycle \
  https://github.com/teamleaderleo/linux-fieldwork.git \
  /tmp/lf-unit13-next

git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git \
  /tmp/mmdebstrap-unit13

git -C /tmp/mmdebstrap-unit13 checkout \
  77ec9be5417ee44c96343d2347145585da1b1f94

test "$(git -C /tmp/mmdebstrap-unit13 hash-object make_mirror.sh)" = \
  6c4be092edcf23b56b63a3befe238c099c45f590

patch --batch --forward --fuzz=0 \
  -d /tmp/mmdebstrap-unit13 -p1 \
  -i /tmp/lf-unit13-next/upstream-packets/units/13-make-mirror-top-level-lifecycle/patches/0001-make-mirror-top-level-signal-proxy-ownership.patch

/bin/sh -n /tmp/mmdebstrap-unit13/make_mirror.sh

cd /tmp/lf-unit13-next
python3 -m unittest -v tests/test_make_mirror_signal_exit.py
python3 -m unittest -v tests/test_make_mirror_proxy_launch_ownership.py
```

Record exact stdout/stderr, command statuses, shell identity, durations, cleanup, and immediate rerun in `TESTS.md`. Review the patched upstream diff completely before changing disposition.

## Unresolved blockers

- technical: fresh current-base zero-fuzz application, syntax, focused rerun, and complete upstream diff remain incomplete;
- compatibility: full mirror/APT/QEMU execution, escalation, HUP, process-group delivery, hostile descendants, and permanently blocking cleanup remain outside current evidence;
- overlap: no visible public match was found; recheck immediately before any authorized submission;
- environment or tooling: the current local runner could not resolve `github.com` before checkout;
- authority: controlled fork creation and all public contact remain unauthorized.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. Linux Fieldwork #397 unit 13, issue #157, and PR #224
7. PRs #159/#205 for predecessor evidence and #305/#324 for the unit 14 boundary

## External-contact state

`false; none occurred`.

Public activity in this pass was read-only source and overlap verification. No upstream issue, pull request, fork, branch, email, comment, review, or message was created.

## Do not repeat

- do not select #159 or #205 as the complete top-level candidate; #224 supersedes them;
- do not restore ordinary signal handlers before pending launch-signal dispatch;
- do not grant first-launch private-cache deletion ownership before readiness;
- do not combine PR #324's `update_cache()` finalizer into unit 13 without new upstream direction;
- do not treat source-blob identity alone as an executed patch application;
- do not classify the DNS checkout failure as candidate evidence;
- do not contact upstream or create a public fork without explicit authorization.
