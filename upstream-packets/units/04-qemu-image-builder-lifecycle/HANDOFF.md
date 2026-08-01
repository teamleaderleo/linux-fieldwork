# Current handoff

Updated: `2026-07-31 17:20 PDT`  
Worker or variant: `ChatGPT`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-04-qemu-image-builder-lifecycle` |
| Linux Fieldwork starting head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Packet content parent head | `18c653ff4e0d7d888e7474abd7d74df59abaa84a` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Upstream builder last-change commit | `ff91e582194f99c72c460815d2fc32018aad9e97` |
| Imported/public-mirror file blob | `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS EXACT APPLY COMMIT` |
| Patch or series | `patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch`, SHA-256 `0ef272d4613e1744957630c5de7da081e248601f934aa98efb43ea22b143c4dd` |
| Owning issue/PR | issue #193 / merged PR #195; priority-zero issue #397 unit 4 |
| Latest authoritative carrier workflow | run `30578489526`, job `90992563661`, green at PR #195 head `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154` |

## Current bounded claim

The extracted single patch expresses the reviewed PR #195 lifecycle against the current byte-identical builder source, uses upstream-root paths and full-file hunk coordinates, and passes the reduced local lifecycle matrix. Repository execution must still prove that the regenerated patch applies to the exact imported source with zero fuzz and zero offsets and passes complete-source/static checks.

## Work completed in this pass

- Read issue #397, packet README/INDEX, issue #193 and all comments, PR #195 patch/comments, issue #170/PR #172, and issue #191/PR #192.
- Claimed unit 4 on #397 and created the canonical branch.
- Confirmed the focused carriers are historical mechanism evidence and PR #195 is the single composition.
- Checked canonical upstream state and established byte identity between the Linux Fieldwork import and a public mirror.
- Extracted one upstream-root patch.
- Detected a concurrent branch continuation that added the retained offset-dependent patch under the canonical packet filename; reviewed it and repaired that file in place to upstream-root paths and full-file coordinates.
- Found and repaired sliced-tail hunk numbering from the retained integration artifact.
- Added a packet regression covering layout, exact-source application, lifecycle, signals, cleanup precedence, reruns, mode, and path rejection.
- Ran the local reduced matrix and recorded hashes/transcript.
- Prepared upstream issue and pull-request drafts without publication.

## Changed paths

- `upstream-packets/units/04-qemu-image-builder-lifecycle/README.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/SOURCE_MAP.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/DEEP_DIVE.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/TESTS.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/DECISIONS.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/UPSTREAM_ISSUE.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/UPSTREAM_PR.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/HANDOFF.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/tests/test_packet_patch.py`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/test-output.txt`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/SHA256SUMS`

## Distinguishing observations

- PR #172 and PR #192 cannot be applied mechanically because both alter the cleanup/trap region; PR #195 is the canonical composition.
- Current upstream still lists the baseline lifecycle in the builder; its most recent listed file change is an April 2025 shfmt commit.
- Linux Fieldwork import and public mirror share Git blob `bb7bce0...`, supporting a current-source rebase without semantic source drift.
- The retained PR #195 patch starts its lifecycle hunk at source line 1 because it was generated from a tail slice. Full-source application therefore depends on a large offset. Packet coordinates now start at actual source line 318.
- Branch history briefly carried that stale retained patch at the packet path through a concurrent continuation; commit `32fc6cb345ff3409038f4d89c558bdea578d147a` replaced it with the corrected upstream-root patch.
- Upstream `coverage.sh` runs shellcheck and shfmt on this builder; no focused dynamic builder entry point was located.

## Gates completed

- Local packet regression: seven discovered, six passed, one exact-source test skipped because checkout unavailable.
- HUP/INT/TERM reduced signal matrix green with statuses 129/130/143.
- Existing/absent output failure matrix green.
- Success, post-publication TERM, cleanup precedence, mode, rerun, and trailing-slash cases green.
- Packet path and full-file coordinate assertions green.
- Artifact SHA-256 manifest written.

## Red or neutral runs classified

- Harness method named `run` shadowed `unittest.TestCase.run`: test-tooling red, repaired by renaming; product patch unchanged.
- Function extractor matched `cleanup()` inside `exit_cleanup()`: test-tooling red, repaired with anchored extraction/reconstruction; product patch unchanged.
- Exact-source test skipped locally: environment neutral, because the container had no checkout and direct clone failed DNS lookup.
- `shellcheck` and `shfmt` unavailable locally: environment neutral.

## Cleanup state

No child processes, sockets, mounts, containers, package changes, or generated images remain. Temporary harness directories were removed automatically. Intentional retained state is the unit branch and the reproducible packet copy under `/mnt/data/unit04-work`. The branch packet content through `18c653ff4e0d7d888e7474abd7d74df59abaa84a` is committed; this handoff is the final branch addition for the pass.

## First incomplete step

Run the packet regression from a Linux Fieldwork checkout so the exact imported-source application test executes instead of skipping. The repository CI path filter excludes `upstream-packets/**`, so a packet-only branch does not automatically exercise this gate.

## Next safe action

```text
python3 upstream-packets/units/04-qemu-image-builder-lifecycle/tests/test_packet_patch.py
```

Require seven passes and zero skips. Then create an exact upstream checkout at `77ec9be5417ee44c96343d2347145585da1b1f94`, apply patch 0001 with `--fuzz=0`, and run `sh -n`, shellcheck, and shfmt as recorded in `TESTS.md`.

## Unresolved blockers

- technical: exact full-source application and upstream static gates have not executed on the regenerated patch.
- compatibility: root-parent refusal and replaced-inode metadata behavior are explicit; no new decision is pending unless upstream objects.
- overlap: no equivalent active upstream work was located; recheck immediately before submission.
- environment or tooling: current container lacks a source checkout, outbound DNS for clone, shellcheck, and shfmt.
- authority: external contact is unauthorized.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. issue #193, merged PR #195, focused PRs #172/#192, and issue #397 unit 4

## External-contact state

Authorization is `false`; no public issue, pull request, email, comment, or review occurred.

## Do not repeat

- Do not treat PR #172 or PR #192 as independent landing patches; PR #195 supersedes them for composition.
- Do not reuse the retained `@@ -1...` sliced-tail hunk numbering.
- Do not reopen the trailing-slash interpretation defect; it is already repaired and tested.
- Do not rerun the old PR #195 CI as a substitute for applying this regenerated packet patch at zero offset.
- Do not add child signal forwarding, fsync, locking, validation, or metadata copying to this unit without a new bounded decision and evidence pass.
