# Current handoff

Updated: `2026-08-01 08:29 +08:00`  
Worker or variant: `ChatGPT`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-04-qemu-image-builder-lifecycle` |
| Packet content parent head | `7196c4563bcecd9aa362606330578a201b716ba7` |
| Internal review carrier | draft PR #400, base `main` |
| Current packet CI at handoff write | run `30675572981`, queued |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Upstream builder last-change commit | `ff91e582194f99c72c460815d2fc32018aad9e97` |
| Imported/public-mirror file blob | `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate identity | patch SHA-256 `0ef272d4613e1744957630c5de7da081e248601f934aa98efb43ea22b143c4dd` |
| Patch or series | `patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch` |
| Owning issue/PR | issue #397 unit 4; issue #193; merged composition PR #195 |
| Historical composed workflow | run `30578489526`, job `90992563661`, green at PR #195 head `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154` |

This handoff commit follows the packet content parent above. Resolve the branch ref or draft PR #400 for the final metadata commit SHA. A handoff-only push may create a successor CI run; classify the newest run attached to the final branch head.

## Current bounded claim

The single patch expresses the reviewed PR #195 lifecycle against the byte-identical current builder source and uses upstream-root paths with complete-file coordinates. It constructs under a private same-filesystem sibling, publishes once, preserves an existing output on ordinary failure and pre-publication signals, returns HUP/INT/QUIT/TERM statuses 129/130/131/143, cleans active state once, preserves a published image after late TERM, and supports immediate reruns.

The repaired reduced lifecycle model passes three cases. The initial packet matrix passed six dynamic cases with one environment skip. Repository test `tests/test_unit04_qemu_packet_patch.py` now owns exact imported-source application with `--fuzz=0`, rejection of offset/fuzz transcripts, complete `sh -n`, image-mutator routing, one publication rename, and lifecycle-model execution.

The unit remains `ACTIVE`: current packet CI, upstream-native `shellcheck`/`shfmt`, and one real builder run remain.

## Work completed in this pass

- Read issue #397, `upstream-packets/README.md`, `upstream-packets/INDEX.md`, and every unit-4 carrier: #170/#172, #191/#192, and #193/#195.
- Claimed unit 4 and continued the canonical branch.
- Confirmed PR #195 is the single source composition; focused PRs #172 and #192 are historical mechanism evidence.
- Confirmed current upstream identities and byte identity between the Linux Fieldwork import and a reviewed public mirror.
- Extracted one upstream-root patch and repaired sliced-source hunk coordinates to full-file lines 318, 406, 465, 474, and 483.
- Retained packet regression `tests/test_packet_patch.py` and its recorded matrix.
- Added and reviewed `scripts/verify_lifecycle_model.py`; repaired the raw trailing-slash fixture and obtained 3/3 passing cases.
- Added top-level repository regression `tests/test_unit04_qemu_packet_patch.py` so PR CI exercises exact source application.
- Updated `README.md`, `SOURCE_MAP.md`, `TESTS.md`, and `SHA256SUMS` to match the actual patch, tests, evidence, and internal review carrier.
- Opened draft internal PR #400 solely for Linux Fieldwork CI and review.
- Prepared upstream issue and PR drafts without publication.
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

- PR #172 and PR #192 both alter the cleanup/trap region. Mechanical application in either order is an invalid release path; PR #195 owns the composition.
- The retained PR #195 patch began its lifecycle hunk at source line 1 because it was generated from a tail slice. Full-source application depended on a large offset. Packet coordinates now begin at actual source line 318.
- The packet uses canonical upstream-root paths instead of Linux Fieldwork import paths.
- The imported builder and reviewed public mirror share Git blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3`.
- The first reduced-model trailing-slash case used `pathlib.Path`, which removed the slash before shell invocation. Preserving the raw string made the intended control execute and pass.
- `tests/test_unit04_qemu_packet_patch.py` sits under `tests/**`, allowing Linux Fieldwork PR CI to execute the exact-source gate.
- Upstream `coverage.sh` runs shellcheck and shfmt on this builder. No focused dynamic builder case was located in `coverage.txt`.
- Publication is the ownership transition: before rename cleanup owns `IMAGE_TMP`; after rename the published final image survives later signals.

## Gates completed

- Historical PR #195 exact-head CI and full source syntax: green, run `30578489526`, job `90992563661`.
- Historical eight-test lifecycle/path matrix: green.
- Initial packet regression: seven discovered, six passed, one exact-source test skipped in the checkout-free container.
- Repaired reduced lifecycle model: 3/3 passed.
- HUP/INT/TERM reduced signal matrix: 129/130/143, prior output preserved, later work omitted.
- Existing/absent output failure, success, post-publication TERM, cleanup precedence, mode, rerun, and path assertions: green in retained evidence.
- Repository exact-application gate committed at `6d5afb1aea17e44b665c1e74e95aba86dd50d3cc`.
- Complete carrier and branch diff review completed through the packet content parent above.
- Draft internal PR #400 opened for CI and review.

## Red or neutral runs classified

- Harness method `run` shadowed `unittest.TestCase.run`: test-tooling red; renamed. Product patch unchanged.
- Function extraction matched `cleanup()` inside `exit_cleanup()`: test-tooling red; anchored extraction repaired it. Product patch unchanged.
- Reduced-model trailing-slash red: `pathlib.Path` removed the spelling under test; raw string repaired it. Product patch unchanged.
- Initial exact-source packet test skip: environment neutral; the first container lacked a checkout and outbound clone DNS failed.
- Local `shellcheck` and `shfmt` absence: environment neutral.
- Branch-only workflow lookup produced no run because CI uses PR events: routing neutral; PR #400 now carries CI.
- Earlier PR #400 runs remained queued during repeated metadata pushes. No product result is claimed from a queued run.
- `capture-bug-report` and `reproduce-mmdebstrap` skips are expected branch-filter behavior.

## Cleanup state

All owned subprocesses were waited. Temporary harness directories were removed. No sockets, mounts, containers, QEMU processes, package transactions, or generated images remain. Intentional retained state consists of the branch, packet files, tests, draft internal PR #400, and queued CI.

## First incomplete step

Classify the newest PR #400 `lab-tools` job attached to the final branch head. A green job completes the repository exact-source application and reduced-model gate. A red job must be classified from its first independent failing step before changing product code.

## Next safe action

```text
# Linux Fieldwork focused gates
python -m unittest -v tests/test_unit04_qemu_packet_patch.py
python -m unittest -v \
  upstream-packets/units/04-qemu-image-builder-lifecycle/tests/test_packet_patch.py \
  tests/test_qemu_builder_composed_lifecycle.py \
  tests/test_qemu_builder_composed_lifecycle_paths.py

# Exact upstream checkout at 77ec9be5417ee44c96343d2347145585da1b1f94
patch --batch --forward --fuzz=0 -p1 \
  -i /path/to/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch
sh -n mmdebstrap-autopkgtest-build-qemu
shellcheck --exclude=SC2016 mmdebstrap-autopkgtest-build-qemu
shfmt --binary-next-line --case-indent --indent 2 --simplify -d \
  mmdebstrap-autopkgtest-build-qemu

# Prepared Debian host, one real image build
./mmdebstrap-autopkgtest-build-qemu \
  --boot=efi --arch="$(dpkg --print-architecture)" \
  unstable /tmp/unit04-autopkgtest.img
```

For the real build, record output SHA-256 and mode, absence of private sibling residue, immediate rerun result, and removal of `/tmp/unit04-autopkgtest.img` afterward.

## Unresolved blockers

- technical: current packet CI has not completed; upstream-native static checks and one real builder run remain.
- compatibility: root-parent refusal and replaced-inode metadata behavior are explicit; a new decision is needed only if upstream review objects.
- overlap: no equivalent active upstream work was found; recheck immediately before an authorized submission.
- environment or tooling: a Debian host with `shellcheck`, `shfmt`, builder dependencies, and a usable mirror is required.
- authority: controlled fork creation and public upstream PR remain unauthorized.

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

Authorization is `false`. No upstream issue, pull request, email, comment, review, fork, or other public action occurred. Draft PR #400 is inside Linux Fieldwork and exists solely for internal CI and review.

## Do not repeat

- Do not treat PR #172 or PR #192 as independent landing patches; PR #195 supersedes them for composition.
- Do not reuse the retained `@@ -1...` sliced-tail hunk numbering.
- Do not reintroduce `pathlib.Path` for the raw trailing-slash argument.
- Do not use historical PR #195 CI as a substitute for the regenerated packet's exact-application gate.
- Do not interpret expected branch-filter skips as product failures.
- Do not add child signal forwarding, fsync, locking, validation, or metadata copying without a new bounded decision and evidence pass.
- Do not contact upstream without explicit authorization for unit 4.
