# Current handoff

Updated: `2026-08-01 08:08 +08:00`  
Worker or variant: `ChatGPT GPT-5.6 Thinking`  
State: `READY FOR AUTHORIZATION`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-03-gpgvnoexpkeysig-lifecycle` |
| Handoff parent | `516cd424d211c97bfaf936ae3804e17aefbecbf5` |
| Linux Fieldwork stop head | the commit containing this final `HANDOFF.md`; exact SHA is in the unit checkpoint on issue #397 |
| Branch starting base | `main` `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Upstream base repository/branch | canonical mmdebstrap repository, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current helper source | blob `83370755454a1322bf6862751aab7381d175aa8b`; displayed latest helper commit `59e5870e7b76cc25dc6cb7b34586451d4ec2a524` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate source identity | upstream base plus retained patch; helper blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed` |
| Patch | `investigations/mmdebstrap-gpgvnoexpkeysig-canonical/0001-canonical-lifecycle.patch`, blob `a30b37ca1228df1d80fd7611d4a591549314aeb0` |
| Owning carriers | #397 unit 03; issues #41/#175/#176; canonical PR #196 |
| Latest durable artifact | `artifacts/real-gpg-fixture.txt`, two PASS receipts; runner SHA-256 `dce709f2aeca82a2e0d38b427a1fd3aaff0b0c8a6deea1b80b3f13d91d6e6e98` |

## Current bounded claim

The retained composed lifecycle patch applies cleanly to the unchanged current helper bytes. With real GnuPG 2.4.7, a generated expired key makes direct `gpgv` emit `EXPKEYSIG`; the candidate emits `GOODSIG` and returns 0. A tampered payload makes direct `gpgv` return 1 with `BADSIG`; the baseline wrapper returns 0 while the candidate returns 1 with the same status. An isolated APT 3.0.3 update through `Apt::Key::gpgvcommand` succeeds, candidate temporary directories are empty, and the complete fixture passes immediately again.

The claim covers the recorded Linux x86_64, dash, GnuPG, and APT environment. Completion-buffered status, the narrow interval between temporary-directory creation and final trap installation, signal-ignoring children, descendant process groups, alternate shells, and broader filesystem-failure injection remain explicit limits.

## Work completed in this pass

- Refreshed issue #397, `upstream-packets/README.md`, `upstream-packets/INDEX.md`, issues #41/#175/#176, PRs #138/#177/#180/#196, and their decision-bearing comments.
- Continued the existing unit branch and verified its committed real-GnuPG/APT fixture, receipts, exact source blobs, and packet narrative.
- Rechecked canonical upstream and indexed overlap on 2026-08-01; `main` still displayed `77ec9be5417ee44c96343d2347145585da1b1f94`, with no equivalent active correction found.
- Added the missing required records: `DECISIONS.md`, `UPSTREAM_ISSUE.md`, `UPSTREAM_PR.md`, and `HANDOFF.md`.
- Updated `upstream-packets/INDEX.md` from `Composed; real fixture needed` to `READY FOR AUTHORIZATION`.
- Prepared a public-safe pull-request draft and recorded that a separate issue is currently unnecessary.

## Changed paths

- `upstream-packets/INDEX.md`
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

The imported helper and retained canonical patch on `main` remain unchanged.

## Distinguishing observations

- Real verifier failure is masked by the baseline process result: direct `gpgv` 1, baseline wrapper 0, candidate 1.
- Genuine expired-key behavior remains available: direct `EXPKEYSIG` becomes candidate `GOODSIG`, and local APT accepts the result.
- The current helper bytes still match the retained patch base, so no source rework was required.
- Parser, verifier status, regular spool, signal ownership, filter-start state, and cleanup remain one coherent review unit.
- The selected regular-file handoff avoids the demonstrated live-FIFO SIGPIPE feedback.
- A separate public issue would duplicate the complete PR report unless upstream requests issue-first discussion.

## Gates completed

- Exact retained patch application without fuzz or offsets.
- Baseline blob `83370755454a1322bf6862751aab7381d175aa8b` and candidate blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed` asserted.
- `/bin/sh -n` passed for baseline and candidate.
- Real expired-key direct/baseline/candidate matrix passed.
- Real tampered-signature matrix distinguished baseline and candidate.
- Status descriptor 3 remained separate from stdout.
- Isolated local APT update passed through baseline and candidate wrappers.
- Candidate direct and APT TMPDIRs were empty.
- Complete fixture passed twice.
- PR #196 exact-head synthetic parser/status/signal/cleanup suite and CI run `30578936718` remain canonical lifecycle evidence.
- Required packet-file and complete-diff review completed.
- Public overlap rechecked on 2026-08-01.

## Red or neutral runs classified

- Baseline tampered-signature status 0 after direct verifier status 1: wrapper product defect and primary negative control.
- Earlier development-only `a/a/...` patch-path failure: fixture packaging error, corrected before retained evidence.
- Broad upstream `coverage.sh`: unexecuted because it requires the full upstream mirror/chroot environment and exceeds the focused helper/APT gate.
- Controlled upstream branch CI: unexecuted because no fork or public branch is authorized.

## Cleanup state

The runner removes its disposable top-level directory through EXIT/HUP/INT/TERM traps. Generated GnuPG homes, private keys, signatures, keyrings, local APT repository, list/cache directories, source copies, status captures, and candidate spools are removed. Candidate TMPDIRs are asserted empty before top-level cleanup. No process, mount, socket, container, lock, host APT state, or generated secret remains. Intentional retained state is limited to the packet, public `Release` fixture, runner, and compact receipts.

## First incomplete step

Obtain one explicit owner decision:

1. `AUTHORIZE FORK+PR` — create a controlled mmdebstrap fork/branch and submit the prepared pull request; or
2. `HOLD FOR PRE-TRAP REPAIR` — repair the documented interval between `mktemp -d` and final trap installation before submission.

No fork, public branch, issue, pull request, comment, email, or review may be created before that decision.

## Next safe action

Without external authorization:

```text
Review README.md, DECISIONS.md, TESTS.md, and UPSTREAM_PR.md, then record exactly one decision: AUTHORIZE FORK+PR or HOLD FOR PRE-TRAP REPAIR.
```

After explicit `AUTHORIZE FORK+PR` approval:

```text
Refresh canonical mmdebstrap main and public overlap; create the controlled fork and candidate branch from the refreshed exact base; apply the retained patch; adapt the real fixture to the upstream-preferred test location; rerun the focused real GnuPG/APT fixture and requested native gates; review the complete public diff; submit only the authorized pull request; record the exact public head and URL in this packet and issue #397.
```

## Unresolved blockers

- technical: none for the bounded candidate; the pre-trap interval is an explicit optional hold decision.
- compatibility: upstream acceptance of completion-buffered status and the documented pre-trap interval.
- overlap: no indexed equivalent found on 2026-08-01; refresh immediately before submission.
- environment or tooling: broad upstream mirror/chroot suite and public-branch CI remain unexecuted.
- authority: controlled fork, candidate branch, and every external action require explicit authorization.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. `UPSTREAM_PR.md`
7. issues #41/#175/#176 and canonical PR #196

## External-contact state

`false; none occurred.` The internal claim and unit checkpoint on issue #397 are authorized repository coordination. No Debian, mmdebstrap, GnuPG, APT, Forgejo, mailing-list, package, or other external action occurred.

## Do not repeat

- Do not revive PRs #138, #177, or #180 as landing carriers; PR #196 supersedes them.
- Do not replace the regular spool with a live FIFO without solving the demonstrated filter-to-verifier SIGPIPE feedback.
- Do not keep the verifier in the foreground while claiming prompt wrapper-only cancellation.
- Do not background verifier/filter children without protecting launch-to-PID registration.
- Do not infer replay need from filter liveness alone; durable `FILTER_STARTED` prevents duplicate output.
- Do not commit generated private key material.
- Do not depend on a remote snapshot for the primary regression; the local fixture already exercises genuine `EXPKEYSIG` and APT integration.
- Do not contact upstream without explicit authorization.
