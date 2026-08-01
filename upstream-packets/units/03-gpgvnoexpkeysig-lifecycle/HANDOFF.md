# Current handoff

Updated: `2026-08-01 08:08 +08:00`  
Worker or variant: `ChatGPT GPT-5.6 Thinking`  
State: `READY FOR AUTHORIZATION`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-03-gpgvnoexpkeysig-lifecycle` |
| Linux Fieldwork handoff parent | `f1a10b95818a6efc6bab02c0b6d4589b7818aff3` |
| Linux Fieldwork stop head | the commit containing this `HANDOFF.md`; exact SHA is recorded in the unit checkpoint on issue #397 |
| Branch starting base | `main` `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Upstream base repository/branch | canonical mmdebstrap repository, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current upstream helper source | blob `83370755454a1322bf6862751aab7381d175aa8b`; displayed latest helper commit `59e5870e7b76cc25dc6cb7b34586451d4ec2a524` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | upstream base plus retained patch; helper blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed` |
| Patch or series | `investigations/mmdebstrap-gpgvnoexpkeysig-canonical/0001-canonical-lifecycle.patch`, blob `a30b37ca1228df1d80fd7611d4a591549314aeb0` |
| Owning issue/PR | #397 unit 03; issues #41, #175, #176; canonical PR #196 |
| Latest retained artifact | `artifacts/real-gpg-fixture.txt`, two complete PASS receipts; script SHA-256 `dce709f2aeca82a2e0d38b427a1fd3aaff0b0c8a6deea1b80b3f13d91d6e6e98` |

## Current bounded claim

On the unchanged current mmdebstrap helper bytes, the retained composed lifecycle patch applies cleanly and preserves the real verifier result while retaining the intended expired-key relaxation. A generated genuine expired key makes direct `gpgv` emit `EXPKEYSIG`; the candidate emits `GOODSIG` and returns 0. A tampered payload makes direct `gpgv` return 1 with `BADSIG`; the baseline wrapper returns 0 while the candidate returns 1 with the same status. An isolated local APT update through `Apt::Key::gpgvcommand` succeeds, candidate temporary state is empty, and the complete fixture passes immediately again.

This claim covers the recorded Linux/GnuPG/APT/dash environment and the direct child lifecycle proved by PR #196. Completion-buffered status, the pre-trap temporary-directory interval, signal-ignoring children, descendants, alternate shells, and broader failure injection remain explicit boundaries.

## Work completed in this pass

- Refreshed issue #397 and its unit-03 scope.
- Re-read `upstream-packets/README.md`, `upstream-packets/INDEX.md`, issues #41/#175/#176, PRs #138/#177/#180/#196, and their decision-bearing comments.
- Continued the existing canonical branch rather than creating a competing variant.
- Reviewed all seven previously committed packet paths and reconciled their identities, receipts, and claims.
- Confirmed the branch was seven commits ahead of its base before closeout and contained the real GnuPG/APT fixture, two execution receipts, and core packet records.
- Rechecked the canonical upstream repository and indexed issue/PR overlap on 2026-08-01; `main` still displayed `77ec9be5417ee44c96343d2347145585da1b1f94` and no equivalent active correction was found.
- Added the missing required packet files: `DECISIONS.md`, `UPSTREAM_ISSUE.md`, `UPSTREAM_PR.md`, and this `HANDOFF.md`.
- Set the durable disposition to `READY FOR AUTHORIZATION`.

## Changed paths

- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/README.md`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/SOURCE_MAP.md`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/DEEP_DIVE.md`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/TESTS.md`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/DECISIONS.md`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/UPSTREAM_ISSUE.md`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/UPSTREAM_PR.md`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/HANDOFF.md`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/fixtures/Release`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/scripts/run-real-gpg-fixture.sh`
- `upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/artifacts/real-gpg-fixture.txt`

The imported helper and retained canonical patch on `main` were deliberately left unchanged.

## Distinguishing observations

- Real GnuPG reproduces the process-result defect: direct `gpgv` returns 1 for a tampered signature, baseline wrapper returns 0, candidate returns 1.
- The expired-key behavior remains intentional and usable: direct status `EXPKEYSIG` becomes candidate `GOODSIG`, and an isolated APT update succeeds.
- The current upstream helper bytes match the retained patch base; no source rework was required.
- The selected regular-file spool avoids the known FIFO/SIGPIPE feedback failure.
- Parser, verifier, filter, signal, and cleanup changes remain one coherent review unit because the state and source lines overlap.
- A separate public issue is currently unnecessary; the PR draft carries the complete report and evidence.

Detailed receipts are in [`TESTS.md`](TESTS.md) and [`artifacts/real-gpg-fixture.txt`](artifacts/real-gpg-fixture.txt). Mechanism and rejected alternatives are in [`DEEP_DIVE.md`](DEEP_DIVE.md) and [`DECISIONS.md`](DECISIONS.md).

## Gates completed

- Retained patch applied without fuzz or offsets to baseline blob `83370755454a1322bf6862751aab7381d175aa8b`.
- Candidate helper blob asserted as `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed`.
- `/bin/sh -n` passed for baseline and candidate in the fixture.
- Generated real expired-key direct/baseline/candidate matrix passed.
- Generated real bad-signature direct/baseline/candidate matrix distinguished baseline and candidate.
- Status-fd 3 separation passed.
- Isolated local APT 3.0.3 update passed through baseline and candidate wrappers.
- Candidate direct and APT TMPDIRs were empty.
- Complete real fixture passed twice.
- PR #196 exact-head synthetic parser/status/signal/cleanup suite and CI run `30578936718` remain the canonical lifecycle evidence.
- Complete packet-link and required-file review completed.
- Indexed upstream overlap rechecked on 2026-08-01.

## Red or neutral runs classified

- Baseline tampered-signature result `0` after direct verifier result `1`: wrapper product defect and primary negative control.
- Earlier development-only patch-path failure (`a/a/...`): fixture packaging error, corrected before retained evidence; the repository patch uses the correct path and both committed receipts pass.
- Broad upstream `coverage.sh`: unexecuted, because it requires the full upstream mirror/chroot test environment and is outside the focused helper/APT fixture.
- Controlled upstream CI: unexecuted, because no fork or public candidate branch is authorized.

## Cleanup state

The retained fixture removes its top-level disposable directory through EXIT/HUP/INT/TERM traps. Generated GnuPG homes, private keys, signatures, keyrings, local APT repository, list/cache directories, source copies, status captures, and candidate spools are removed. Candidate-specific TMPDIRs are asserted empty before top-level cleanup. No child, mount, socket, container, lock, host APT state, or generated secret remains. Intentional retained state consists only of packet text, the public `Release` fixture, the runner, and compact receipts.

## First incomplete step

Obtain an explicit repository-owner decision between:

1. authorize creation of a controlled mmdebstrap fork/branch and one pull request using [`UPSTREAM_PR.md`](UPSTREAM_PR.md); or
2. hold submission and first repair the documented interval between `mktemp -d` and final trap installation.

No fork, branch, public issue, pull request, comment, email, or review may be created before that decision.

## Next safe action

Without external authorization:

```text
Review README.md, DECISIONS.md, TESTS.md, and UPSTREAM_PR.md, then record exactly one owner decision: AUTHORIZE FORK+PR or HOLD FOR PRE-TRAP REPAIR.
```

After explicit authorization for `AUTHORIZE FORK+PR`:

```text
Refresh canonical mmdebstrap main and public overlap; create the controlled fork and candidate branch from the refreshed exact base; apply the retained patch; adapt the real fixture into the upstream-preferred test location; rerun the focused real GnuPG/APT fixture and any requested native gate; review the complete public diff; submit only the authorized pull request; record the exact public head and URL in this packet and issue #397.
```

## Unresolved blockers

- technical: none for the bounded candidate; the pre-trap interval is an explicit optional hold decision.
- compatibility: upstream acceptance of completion-buffered status and the documented narrow pre-trap interval.
- overlap: no indexed equivalent found on 2026-08-01; refresh immediately before submission.
- environment or tooling: broad upstream mirror/chroot suite and public-branch CI remain unexecuted.
- authority: controlled fork, candidate branch, and all external contact require explicit authorization.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. `UPSTREAM_PR.md`
7. owning issues #41/#175/#176 and canonical PR #196

## External-contact state

`false; none occurred.` Internal issue #397 received the authorized claim and will receive the required unit checkpoint. No Debian, mmdebstrap, GnuPG, APT, Forgejo, mailing-list, package, or other external action was taken.

## Do not repeat

- Do not revive PRs #138, #177, or #180 as landing carriers; PR #196 supersedes them while preserving their evidence.
- Do not replace the regular spool with a live FIFO without resolving the demonstrated early-filter SIGPIPE feedback.
- Do not keep the verifier in the foreground while claiming prompt wrapper-only cancellation.
- Do not background verifier/filter children without protecting launch-to-PID registration.
- Do not infer replay need from filter liveness alone; durable `FILTER_STARTED` prevents duplicate completed output.
- Do not commit generated private key material; the fixture generates and deletes it.
- Do not depend on a remote historical snapshot for the primary regression; the local generated fixture already exercises genuine `EXPKEYSIG` and APT integration.
- Do not contact upstream without explicit authorization.
