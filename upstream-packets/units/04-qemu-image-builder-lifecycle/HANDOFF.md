# Current handoff

Updated: `2026-07-31 17:35 PDT`  
Worker or variant: `ChatGPT`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-04-qemu-image-builder-lifecycle` |
| Linux Fieldwork starting head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Packet code/content parent head | `6edb4dd362ba5ac3208bd89a048459c8600b35ff` |
| Internal review carrier | draft PR #400, base `main` |
| PR #400 code head | `6edb4dd362ba5ac3208bd89a048459c8600b35ff` |
| Current packet CI at handoff write | run `30675401988`, `lab-tools` job `91301476493`, queued |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Upstream builder last-change commit | `ff91e582194f99c72c460815d2fc32018aad9e97` |
| Imported/public-mirror file blob | `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate identity | patch SHA-256 `0ef272d4613e1744957630c5de7da081e248601f934aa98efb43ea22b143c4dd` |
| Patch or series | `patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch` |
| Owning issue/PR | issue #193 / merged PR #195; priority-zero issue #397 unit 4 |
| Historical composed workflow | run `30578489526`, job `90992563661`, green at PR #195 head `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154` |

The commit adding this handoff follows the packet code/content parent above. Because PR #400 includes `tests/**`, the handoff-only push may create a successor CI run; classify the newest run attached to the final branch head.

## Current bounded claim

The single patch expresses the reviewed PR #195 lifecycle against the byte-identical current builder source and uses upstream-root paths with complete-file coordinates. The repaired reduced lifecycle model passes three cases. The initial packet matrix passed six cases with one environment skip. A repository-level test now owns exact imported-source application with zero fuzz and zero offsets, complete `sh -n`, image-mutator routing, one publication rename, and lifecycle-model execution. PR #400 CI remains the current discriminator for that gate.

## Work completed in this pass

- Read issue #397, packet README/INDEX, issue #193 and all comments, PR #195 patch/comments, issue #170/PR #172, and issue #191/PR #192.
- Claimed unit 4 on #397 and created the canonical branch.
- Confirmed the focused carriers are historical mechanism evidence and PR #195 is the single composition.
- Checked canonical upstream state and established byte identity between the Linux Fieldwork import and a reviewed public mirror.
- Extracted one upstream-root patch.
- Detected a concurrent branch continuation that added the retained offset-dependent patch under the canonical packet filename; reviewed it and repaired that file in place to upstream-root paths and full-file coordinates.
- Added packet documentation, source map, decisions, drafts, hashes, and an initial focused regression.
- Reviewed the concurrent reduced lifecycle verifier and its repaired trailing-slash fixture.
- Reviewed the top-level repository regression that applies the patch to the exact imported source and routes the branch through Linux Fieldwork CI.
- Read draft internal PR #400 and its complete branch diff. PR #400 is an internal CI/review carrier only.
- Posted claim and checkpoint comments on issue #397.
- Made no upstream contact.

## Changed paths

- `tests/test_unit04_qemu_packet_patch.py`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/README.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/SOURCE_MAP.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/DEEP_DIVE.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/TESTS.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/DECISIONS.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/UPSTREAM_ISSUE.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/UPSTREAM_PR.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/HANDOFF.md`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/scripts/verify_lifecycle_model.py`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/tests/test_packet_patch.py`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/test-output.txt`
- `upstream-packets/units/04-qemu-image-builder-lifecycle/SHA256SUMS`

## Distinguishing observations

- PR #172 and PR #192 both alter the cleanup/trap region; PR #195 is the canonical reviewed composition.
- Current upstream still carries the baseline builder lifecycle; its latest listed file change is commit `ff91e582194f99c72c460815d2fc32018aad9e97`.
- Linux Fieldwork import and the reviewed public mirror share Git blob `bb7bce0...`, supporting current-source applicability without semantic source drift.
- The retained PR #195 patch began its lifecycle hunk at source line 1 because it was generated from a tail slice. Full-source application depended on a large offset. Packet coordinates now begin at actual source line 318 and continue at 406, 465, 474, and 483.
- Branch history briefly carried that stale retained patch at the packet path; commit `32fc6cb345ff3409038f4d89c558bdea578d147a` replaced it with the corrected upstream-root patch.
- The first reduced-model trailing-slash case accidentally converted the raw spelling to `pathlib.Path`, removing the slash. The repaired model preserves a string argument and passes all three cases.
- `tests/test_unit04_qemu_packet_patch.py` places the exact-source gate under `tests/**`, so the PR workflow includes it even though `upstream-packets/**` alone is outside the workflow path filter.
- Upstream `coverage.sh` runs shellcheck and shfmt on this builder. No focused dynamic builder case was located in `coverage.txt`.

## Gates completed

- Initial packet regression: seven discovered, six passed, one exact-source test skipped in the checkout-free container.
- Repaired reduced lifecycle model: three passed, including baseline-versus-candidate TERM, publication/failure/late-signal behavior, and trailing-slash rejection.
- HUP/INT/TERM reduced signal matrix: statuses 129/130/143 with prior output preserved and later work omitted.
- Existing/absent output failure, success, post-publication TERM, cleanup precedence, mode, rerun, and path assertions: green in retained local evidence.
- Repository exact-application gate and CI routing test: committed at `6d5afb1aea17e44b665c1e74e95aba86dd50d3cc`.
- Complete branch diff reviewed through code/content head `6edb4dd362ba5ac3208bd89a048459c8600b35ff`.
- Draft internal PR #400 opened for Linux Fieldwork CI and review.

## Red or neutral runs classified

- Harness method named `run` shadowed `unittest.TestCase.run`: test-tooling red, repaired by renaming; product patch unchanged.
- Function extractor matched `cleanup()` inside `exit_cleanup()`: test-tooling red, repaired with anchored extraction; product patch unchanged.
- Reduced-model trailing-slash red: `pathlib.Path` removed the spelling under test; repaired by preserving the raw string; product patch unchanged.
- Initial exact-source packet test skip: environment neutral because the first container lacked a checkout and outbound DNS failed.
- `shellcheck` and `shfmt` absent in the first local container: environment neutral.
- PR #400 runs `30675270148` and `30675401988` were queued at the latest checks; no product result exists yet.
- Workflow jobs `capture-bug-report` and `reproduce-mmdebstrap` are expected skips because their branch-name predicates target a separate investigation lane.

## Cleanup state

No child processes, sockets, mounts, containers, package changes, or generated images remain from the local packet work. Temporary harness directories and owned subprocesses were cleaned. Intentional retained state is the unit branch, draft internal PR #400, queued CI, and the reproducible packet copy under `/mnt/data/unit04-work`.

## First incomplete step

Classify the newest PR #400 `lab-tools` job attached to the final branch head. A green job completes the repository exact-source application and reduced-model gate. A red job must be classified from its exact failing step before any patch change.

## Next safe action

From a Linux Fieldwork checkout, execute the same focused gate directly:

```text
python -m unittest -v tests/test_unit04_qemu_packet_patch.py
```

Then run the full retained unit matrix:

```text
python -m unittest -v \
  upstream-packets/units/04-qemu-image-builder-lifecycle/tests/test_packet_patch.py \
  tests/test_qemu_builder_composed_lifecycle.py \
  tests/test_qemu_builder_composed_lifecycle_paths.py
```

After those pass, apply the packet in an upstream checkout at `77ec9be5417ee44c96343d2347145585da1b1f94` and run the shellcheck/shfmt commands and real builder invocation recorded in `TESTS.md`.

## Unresolved blockers

- technical: current packet CI has not completed; upstream-native shellcheck/shfmt and one real builder run remain.
- compatibility: root-parent refusal and replaced-inode metadata behavior are explicit; a new decision is needed only if upstream review objects.
- overlap: no equivalent active upstream work was located; recheck immediately before submission.
- environment or tooling: the first local container lacked checkout/network/static tools; PR #400 now supplies the repository gate.
- authority: external contact is unauthorized.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `SOURCE_MAP.md`
4. `DEEP_DIVE.md`
5. `DECISIONS.md`
6. `tests/test_unit04_qemu_packet_patch.py`
7. `scripts/verify_lifecycle_model.py`
8. draft PR #400, issue #193, merged PR #195, focused PRs #172/#192, and issue #397 unit 4

## External-contact state

Authorization is `false`; no upstream issue, pull request, email, comment, review, or other public action occurred. Draft PR #400 is inside Linux Fieldwork and exists solely for internal CI/review.

## Do not repeat

- Do not treat PR #172 or PR #192 as independent landing patches; PR #195 supersedes them for composition.
- Do not reuse the retained `@@ -1...` sliced-tail hunk numbering.
- Do not reintroduce `pathlib.Path` for the raw trailing-slash test argument.
- Do not use historical PR #195 CI as a substitute for the regenerated packet's exact-application gate.
- Do not interpret expected branch-filter job skips as product failures.
- Do not add child signal forwarding, fsync, locking, validation, or metadata copying without a new bounded decision and evidence pass.
