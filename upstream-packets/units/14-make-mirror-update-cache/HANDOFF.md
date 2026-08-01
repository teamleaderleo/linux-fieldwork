# Current handoff

Updated: `2026-07-31 17:01 PDT`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-14-make-mirror-update-cache` |
| Linux Fieldwork packet snapshot before this handoff commit | `6aa9b8efc13df8af1aa8bfdd8912bc6ab804483d` |
| Linux Fieldwork final branch tip | commit containing this HANDOFF; exact SHA recorded in the final unit #397 checkpoint |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Upstream source blob | `make_mirror.sh` `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Patch or series | `patches/0001-update-cache-worker-lifecycle.patch` |
| Patch SHA-256 | `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42` |
| Owning issue/PR | #397 unit 14; issue #231; merged component PRs #286 and #324 |
| Latest workflow/run/artifact | PR #324 CI `30630467076` / 916, success |

## Current bounded claim

On current upstream source blob `6c4be092...`, the retained real-shell matrices establish that the composed `update_cache()` worker lifecycle:

- cleans only worker-owned APT state;
- leaves parent-owned proxy stop/wait to the top-level shell;
- returns INT/QUIT/TERM as 130/131/143;
- converges success, ordinary failure, implicit EXIT, explicit signals, cleanup-time signals, and cleanup failure through one finalizer;
- records the first handled signal during ordinary cleanup and ignores later handled signals until bounded cleanup completes;
- applies `existing ordinary or explicit-signal failure > cleanup-time signal > cleanup failure > success`;
- cleans once, removes worker state, omits later work, and permits an immediate clean rerun.

This pass collapsed the two landed internal patches into one upstream-facing patch. Full-tree application of that new single carrier and upstream-native execution remain pending.

## Work completed in this pass

- read issue #397, `upstream-packets/README.md`, `upstream-packets/INDEX.md`, and the complete packet template;
- claimed unit 14 internally and created the canonical Linux Fieldwork branch;
- read issue #231, its comments/final receipt, and carrier PRs #238, #259, #260, #267, #286, #305, #322, and #324;
- read adjacent ownership/hold/tool carriers PR #224, issue #263 / PR #264, issue #271 / PR #273, and PR #302;
- read the retained investigation, cleanup-signal record, both provenance patches, and current imported source;
- pinned current canonical upstream `main` and verified the upstream source blob matches the retained import;
- searched indexed official upstream issue and pull-request surfaces for equivalent active work;
- created one combined upstream-root patch and fixed its SHA-256 identity;
- verified combined hunk grammar/count/line arithmetic with a local exact-position synthetic carrier and `patch --fuzz=0`;
- wrote the complete unit packet, drafts, evidence matrix, decisions, and this handoff;
- made no upstream contact.

## Changed paths

- `upstream-packets/units/14-make-mirror-update-cache/README.md`
- `upstream-packets/units/14-make-mirror-update-cache/SOURCE_MAP.md`
- `upstream-packets/units/14-make-mirror-update-cache/DEEP_DIVE.md`
- `upstream-packets/units/14-make-mirror-update-cache/TESTS.md`
- `upstream-packets/units/14-make-mirror-update-cache/UPSTREAM_ISSUE.md`
- `upstream-packets/units/14-make-mirror-update-cache/UPSTREAM_PR.md`
- `upstream-packets/units/14-make-mirror-update-cache/DECISIONS.md`
- `upstream-packets/units/14-make-mirror-update-cache/HANDOFF.md`
- `upstream-packets/units/14-make-mirror-update-cache/patches/0001-update-cache-worker-lifecycle.patch`

## Distinguishing observations

- Current upstream `make_mirror.sh` has the same blob as the Linux Fieldwork import. The unit has zero source drift at the pinned base.
- Unit 14 requires both landed component repairs. PR #286 fixes ownership, terminating statuses, once-only cleanup, and basic precedence. PR #324 retains the first cleanup-time signal and protects bounded cleanup from later handled signals.
- The two patches overlap the same finalizer and belong in one upstream source patch. Sending the first alone would publish a known intermediate lifecycle gap.
- Prompt foreground-descendant cancellation remains a separate latency hold. PR #264 found a larger supervisor/group mechanism disproportionate under current evidence.
- Indexed official upstream searches found no equivalent public carrier on 2026-07-31. A live direct overlap check remains required before authorization.

## Gates completed

- PR #286 exact-head Linux Fieldwork CI `30624335126` / 842: success; 249 tests.
- PR #324 executable-head CI `30630113839` / 911: success; 303 tests.
- PR #324 final documentation-head CI `30630467076` / 916: success; complete retained lifecycle matrix and repository discovery.
- Upstream/current import source identity: blob match `6c4be092edcf23b56b63a3befe238c099c45f590`.
- Combined patch SHA-256: `980720d262d0f5d4a568be54851e144652ae6d882a8ad0e8aa228c8ffed2ae42`.
- Combined hunk arithmetic: local synthetic exact-position `patch --fuzz=0` pass; first new symbol at line 156 and terminal `update_cache_finish 0` at line 298.

## Red or neutral runs classified

- direct `git clone` and direct `curl` retrieval failed before source retrieval because the assistant container could not resolve public hosts: environment/tooling failure;
- `container.download` retrieved response metadata for the raw source but rejected the `text/x-shellscript` materialization type: tooling failure;
- the first local patch check used a fixture named `synthetic`, while the patch targets `make_mirror.sh`; renaming the fixture produced a clean two-hunk application: fixture setup failure, then pass;
- historical PR #238 malformed hunk packaging: patch carrier defect, repaired before canonical composition;
- historical PR #286 duplicate discovery: test import defect, repaired before the exact green head.

## Cleanup state

No test-created process, socket, mount, container, lock, or source checkout remains. Local analysis retained only disposable `/tmp/unit14` files during the session. The intentional durable state is the Linux Fieldwork branch and packet files listed above. No upstream fork, branch, issue, pull request, comment, email, or review was created.

## First incomplete step

Create or identify a controlled mmdebstrap fork and checkout at upstream commit `77ec9be5417ee44c96343d2347145585da1b1f94`, then apply the packet's single combined patch to the full source tree with zero offset/fuzz.

## Next safe action

Run this from a controlled upstream checkout after the fork/branch exists:

```text
git switch --detach 77ec9be5417ee44c96343d2347145585da1b1f94
git switch -c linux-fieldwork/unit-14-update-cache-worker-lifecycle
git apply --check --verbose /path/to/linux-fieldwork/upstream-packets/units/14-make-mirror-update-cache/patches/0001-update-cache-worker-lifecycle.patch
git apply /path/to/linux-fieldwork/upstream-packets/units/14-make-mirror-update-cache/patches/0001-update-cache-worker-lifecycle.patch
/bin/sh -n make_mirror.sh
git diff --check
git diff -- make_mirror.sh
```

After those pass, port or run the retained five focused modules against the controlled source and select the smallest upstream-native gate that avoids an unnecessary network mirror run.

## Unresolved blockers

- technical: full-tree application and `/bin/sh -n` of the newly collapsed single carrier;
- compatibility: upstream-native execution and review of bounded-cleanup policy on the candidate branch;
- overlap: direct live issue/PR list review immediately before authorization;
- environment or tooling: the current assistant container cannot resolve public Git hosts, and connector file reads do not materialize a checkout;
- authority: controlled fork/branch creation is internal technical work, while any upstream-visible issue, PR, comment, email, or review remains unauthorized.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. `patches/0001-update-cache-worker-lifecycle.patch`
7. issue #231, merged PR #286, and merged PR #324

## External-contact state

`false; none occurred`. Public upstream pages were read for source identity and overlap only. No upstream write or message was made.

## Do not repeat

- do not revive PRs #238, #259, #260, #267, or #305 as current carriers;
- do not submit patch 0001 without the cleanup-time signal refinement;
- do not broaden this unit into top-level proxy launch/PID ownership from PR #224;
- do not add process-group supervision without a PR #264 reopen trigger;
- do not treat DNS/materialization failures as product evidence;
- do not infer full-tree application of the new collapsed carrier solely from the local synthetic hunk check; the retained two-patch full-source CI is provenance, and the collapsed carrier still needs its own full-tree gate.
