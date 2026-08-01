# Decision log

## 2026-08-01 — keep one composed wrapper lifecycle

**Decision:** Retain PR #196's parser, verifier-status, status-spool, signal-ownership, and cleanup work as one upstream contribution unit.

**Reason:** The behaviors share the same `gpgvnoexpkeysig` option scan, dynamic status descriptor, child PID state, spool state, signal traps, and final precedence block. The focused carriers exposed known-bad intermediate states: a live FIFO can feed filter failure back into `gpgv`, a foreground verifier delays wrapper-only cancellation, direct background launch leaves PID-registration windows, and filter-liveness-only replay can duplicate completed status.

**Evidence:** Issues #41, #175, and #176; focused PRs #138, #177, and #180; canonical PR #196 at `bc8d88089d931cd0b78dd0c95dd72c784195fcdc`, merged internally as `65d4213393cf2b2d84c71a8b6a05fdad15396b9b`; [`DEEP_DIVE.md`](DEEP_DIVE.md).

**Alternatives considered:**

- submit the three focused patches as an ordered stack;
- require Bash and use `PIPESTATUS` or `pipefail`;
- retain a live FIFO for status streaming;
- rewrite the helper in a larger language.

**Consequences:**

- one complete diff carries the shared lifecycle invariant;
- focused PRs remain historical evidence and stay closed;
- status bytes remain buffered until verifier completion;
- escalation and descendant process-group policy remain separate.

**Reopen trigger:** Current upstream source changes the helper substantially, or upstream explicitly requests a review split that preserves the complete invariant in every intermediate commit.

**Authority effect:** Internal composition and packet work remain authorized. External contact remains unauthorized.

---

## 2026-08-01 — use a regular status spool and owned child phases

**Decision:** Keep the selected private regular-file handoff with separately owned verifier and filter children, recording traps during launch, durable `FILTER_STARTED` state, and explicit result precedence.

**Reason:** This is the smallest POSIX `/bin/sh` design in the existing evidence that preserves the verifier result, prevents filter-to-verifier SIGPIPE feedback, forwards wrapper-only signals, closes launch/PID-registration windows, prevents late duplicate replay, and cleans temporary state.

**Evidence:** PR #196 synthetic matrix and CI run `30578936718`; retained patch blob `a30b37ca1228df1d80fd7611d4a591549314aeb0`; candidate helper blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed`.

**Alternatives considered:**

- live FIFO;
- foreground verifier;
- unprotected background launch;
- process-group kill or automatic SIGKILL escalation.

**Consequences:**

- verifier failure wins over filter and cleanup failure;
- HUP/INT/TERM use signal-derived statuses after forwarding and reaping;
- a signal-ignoring child can still delay exit;
- the small interval between `mktemp -d` and final trap installation remains documented for reviewer attention.

**Reopen trigger:** A lower-complexity POSIX mechanism closes the pre-trap interval, or upstream rejects completion-buffered status.

**Authority effect:** No change to external-contact authority.

---

## 2026-08-01 — accept the generated real GnuPG and local APT fixture

**Decision:** Use the committed generated-key fixture as the real cryptographic and APT-oriented closeout gate.

**Reason:** It is deterministic in behavior while generating fresh disposable key material: a key created at fake time 2000-01-01 expires before current verification, direct `gpgv` emits genuine `EXPKEYSIG`, a tampered payload emits genuine `BADSIG` with status 1, and an isolated local `apt-get update` exercises `Apt::Key::gpgvcommand` without remote services or host APT state.

**Evidence:** [`scripts/run-real-gpg-fixture.sh`](scripts/run-real-gpg-fixture.sh), [`fixtures/Release`](fixtures/Release), two receipts in [`artifacts/real-gpg-fixture.txt`](artifacts/real-gpg-fixture.txt), and the matrix in [`TESTS.md`](TESTS.md).

**Alternatives considered:**

- rely only on fake verifier fixtures;
- depend on a remote historical Debian snapshot;
- commit private key material.

**Consequences:**

- the baseline's false success is demonstrated with real GnuPG;
- the intended expired-key relaxation is exercised through APT;
- no reusable secret or network dependency enters the packet;
- fingerprints differ between runs while asserted status classes remain stable.

**Reopen trigger:** The fixture fails on a supported GnuPG/APT version or upstream requests a different native test form.

**Authority effect:** Internal execution is authorized; no generated key or result was sent externally.

---

## 2026-08-01 — target one Forgejo pull request; no separate issue required

**Decision:** Prepare one pull request against canonical mmdebstrap `main`. Keep `UPSTREAM_ISSUE.md` as `NOT NEEDED` unless maintainers request issue-first discussion.

**Reason:** The pull-request draft contains the concrete baseline result, bounded implementation, real fixture, compatibility limits, and reviewer questions. A second public carrier would duplicate the same technical explanation.

**Evidence:** Current canonical repository inspection at upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94`; [`UPSTREAM_PR.md`](UPSTREAM_PR.md); indexed issue and pull-request overlap search on 2026-08-01.

**Alternatives considered:**

- issue first, then pull request;
- Debian-only downstream patch;
- mailing-list patch series.

**Consequences:**

- controlled fork and candidate branch remain `NEEDS FORK` / `NEEDS BRANCH`;
- overlap must be refreshed immediately before any authorized submission;
- no public action occurs from this decision alone.

**Reopen trigger:** Upstream contribution guidance changes, equivalent work appears, or maintainers request an issue or ordered series.

**Authority effect:** External contact remains unauthorized.

## Final disposition

`READY FOR AUTHORIZATION` on 2026-08-01.

The retained patch applies cleanly to current unchanged helper bytes, the synthetic lifecycle matrix is green at its exact canonical head, the generated real-GnuPG fixture distinguishes baseline and candidate, local APT integration passes, cleanup and immediate rerun pass, the complete packet and public draft are present, and the destination is identified. The remaining step is the repository owner's explicit send/hold decision. No external contact occurred.
