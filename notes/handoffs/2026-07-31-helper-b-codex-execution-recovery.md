# Helper B Codex execution recovery

Date: 2026-07-31

Tracking: issue #194, Packet B and adjacent Packet I review.

## TL;DR

A long autonomous session produced useful repository changes, but its live narration became noisy and its tool path briefly drifted. The technical work remained recoverable because exact heads, GitHub Actions runs, artifacts, issue comments, pull-request bodies, and tracked records existed outside the chat.

The recovery rule is: stop narrating, reload the live instructions, reconstruct facts from durable records, classify each failure by owner, and resume from the latest exact head.

The recovery produced three concrete follow-ups:

- PR #222 — repository scanner for relative executables combined with child cwd changes;
- PR #250 — guarded cleanup parents and preserved runtime source copies for issue #130;
- PR #251 — Packet B's exact four-file focused unit extracted onto current `main`.

## Explain like I'm five

Imagine building a model train while writing down every move. The train can still work when the notebook becomes messy. To recover, look at the train, the parts on the table, and the test results. Avoid guessing from the messy notebook.

Here, GitHub commits and test artifacts are the train. Chat narration is the notebook.

## Why care

An agent can accidentally confuse four different things:

1. the product is broken;
2. the test harness is broken;
3. the tool used to inspect or edit the repository failed;
4. the narration lost the current decision boundary.

Treating all four as one failure causes needless product edits, duplicate branches, stale receipts, and misleading confidence.

## Safe execution log

This is a factual execution log, separate from private scratch reasoning.

1. Packet B exact-head tests passed after repairing a missing per-run directory in the guard harness.
2. The first composed Debian sid run stopped at Black before functional cases because the retained `coverage.py` hunk used a form Black rewrote.
3. The formatter-compatible patch passed focused repository CI.
4. The second composed sid run completed the container and uploaded evidence, then classified the package test as exit 6.
5. Artifact inspection showed the Packet B capability case never ran. The earlier main phase stopped on `cwd-directory-not-accessible-by-unshared-user`: that test changes directory and the temporary proxy command was relative (`./mmdebstrap`).
6. An intermediate absolute-path repair pointed at the preserved imported source, whose executable mode was intentionally absent. That run failed at the first preflight command with permission denied.
7. A later reduction carrier reused the executable temporary proxy through a stable absolute path and added a cwd-change control.
8. During adjacent PR #109 review, a retained unified diff had one malformed hunk count. A direct patch application check caught it; the hunk count was repaired before relying on CI.
9. Attempts to download raw GitHub files directly through the local container failed because that path belonged to the GitHub connector and the container had no external DNS. GitHub connector fetches were used instead.
10. The session reloaded `README.md`, `START_HERE.md`, `ADAPTIVE_COORDINATION.md`, `FIELD_GUIDE.md`, and issue #194 before continuing.
11. Packet B was extracted from the stale historical branch into current-main PR #251.
12. Issue #130 gained dedicated repair PR #250.
13. The relative-executable failure class was generalized in PR #222; cross-review replaced optimizer-removable receipt assertions with explicit schema and identity failures.

## What went wrong in the working process

### Narration outran the decision

Updates continued while long jobs were active, producing a large stream of partial states. A reader could lose the current disposition even though the repository records stayed accurate.

Decision: one concise update per meaningful state transition. Put detailed transcripts in tracked records.

### Tool routing was attempted through the wrong path

The local container was asked to fetch raw GitHub content even though the GitHub connector already owned that data path. The environment rejected or could not resolve those requests.

Decision: use the source-owning connector first. Use the container for mounted files and local execution.

### A test-carrier path assumption survived early review

The proxy worked from the suite root but failed after a test changed working directory. This was a harness defect, separate from Packet B scheduling.

Decision: commands passed into generated tests need absolute or deliberately resolved paths. Add a control that changes directory before invocation.

### An absolute path named the wrong artifact

The first absolute-path repair pointed at the imported source file. That file was deliberately preserved without executable mode, while the executable proxy lived in the package-test temporary directory.

Decision: record executable identity and lifecycle together. “Absolute” answers location; it does not answer which artifact owns execution.

### A patch file was treated as plausible before exact application

The product idea in PR #109 was sound, while one unified-diff hunk count was malformed.

Decision: every retained patch gets an exact `patch --batch --forward` application test before it becomes evidence.

## Related Linux Fieldwork precedents

- `FIELD_GUIDE.md` — “Green but unexecuted”: repository CI can pass while the real privileged or long-running job is skipped or stops before the probe.
- `FIELD_GUIDE.md` — “One source gate bypassed, another remains”: defeating one preflight can expose another earlier than behavioral execution.
- issue #54 — a workflow referenced investigation tooling absent from `main`; the job failed before the research question.
- issue #75 — branch-name matching alone could route fork-controlled code into a privileged container.
- issue #130 — a reusable harness trusted caller-selected cleanup roots and mutated imported source mode.
- PR #72 — a relative staged command failed after a generated test changed working directory.
- PR #109 — prose and probes described a future absolute-wrapper source state while the exact source still used bare `env`.
- PR #222 — the recurring relative-executable/cwd class is now encoded as reusable review tooling.

These examples share one rule: identify the owner of the first failure before editing product code.

## Tiebreakers

When evidence conflicts, use this order:

1. exact source at the current head;
2. exact-head executed test and raw artifact;
3. tracked investigation record;
4. current issue or pull-request receipt;
5. chat narration and older prose.

When two fixes are plausible:

1. prefer the smallest fix that restores the intended authority boundary;
2. preserve original failure semantics;
3. keep product changes separate from temporary reduction tooling;
4. require a negative control that breaks under the rejected design;
5. choose one canonical carrier after composition succeeds.

For path-sensitive command carriers:

1. identify the executable artifact;
2. identify the directory where lookup occurs;
3. identify any cwd or namespace change before execution;
4. identify who controls the path and executable mode;
5. test from a different cwd and with a decoy where useful.

## Current technical decisions

### Packet B

PR #251 is the current-main focused carrier. PR #171 becomes historical after #251 passes exact-head CI. PR #72 remains the disposable sid composition and first-failure carrier.

The focused unit can reach final human review independently from temporary proxy failures. A sid artifact that reaches the dedicated capability phase remains valuable integration evidence before an upstream proposal.

### PR #72

Keep as an investigation carrier. The proxy is useful for reduction and unsuitable as final reusable tooling because it changes the original source-preflight subject. Use a stable absolute temporary-proxy path during reduction; remove the proxy before any reusable-tooling merge decision.

### PR #109

Keep at `REPAIR`. The retained `/usr/bin/env` patch is a bounded product direction. Apply it on a clean current-main candidate and add fake leading-PATH `env` controls before promotion.

### PR #222

This is the reusable review-tool answer to the relative executable/cwd defect class. The scanner covers high-confidence literal Python, Rust, and GNU `env` cases. Helper B repaired its downloaded Windows receipt to use explicit exact-type and identity validation. A green exact head should move it to `MERGE LOCALLY`.

### PR #250

This is the dedicated issue #130 repair carrier. It accepts named disposable parent families, executes a preserved runtime source copy, and compares incoming/outgoing source mode, Git blob hash, and path-specific Git status. A green exact head makes the retained patch suitable for direct application or current-main extraction.

## Further checks worth doing

The same class is likely where a command is constructed in one directory and executed after `chdir`, namespace entry, privilege drop, or remote handoff. Search imported projects and harnesses for:

- `CMD=./...` passed into generated scripts;
- bare executable names used as security or sanitizing wrappers;
- workflows that describe a source mutation performed by a later job;
- test reports whose headline case never appears in the raw transcript;
- cleanup paths derived from caller-controlled temporary roots;
- artifacts whose classifier reads a summary instead of preserving the first raw failure;
- absolute paths that name a preserved source artifact while execution belongs to a generated or installed copy.

## 2026-08-01 resumption checkpoint

A later interaction stopped while two useful but unfinished paths were visible in chat:

- PR #361's Debian sid run `30640356619` was still in progress;
- a classifier-only branch, `repair/chrootless-env-lossless-invocation-receipts`, had reached `aad79ca2556f45a01c1dc7dfaf3f4c2143a79641` while repairing PR #349's lossy fake-`env` receipt.

The repository and hosted receipts, not the interrupted narration, determine the current state.

### Recovered remote state

1. Run `30640356619` later completed with container status 6 and uploaded artifact `8798679560`, digest `sha256:50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244`. Status 6 alone did not identify the first failing case.
2. A later exact source run, `30641621084`, produced the canonical retained artifact interpreted by merged PR #376. Its typed receipt shows broad `(242/284) chrootless` failed before `root-without-cap-sys-admin` completed. The focus appears only in the skipped inventory and remains `unresolved`.
3. Packet B therefore remains `HOLD FOR FOCUSED EXECUTION`. The artifact neither proves a focused pass nor a focused failure.
4. Historical PR #349 is retired. Its unique receipt defects moved through PRs #367 and #369 into current-main PR #368, which merged the two product patches, lossless direct/APT argv receipts, and exact runtime cleanup guards.
5. The partial classifier branch at `aad79ca...` is abandoned provenance only. Do not resume or promote it; its useful idea already landed through the canonical current-main carrier.
6. Current main at the resumption check is `1ac6aadf884ca69935c2f763b9788476a313645c`, after the landed chrootless authority stack, Packet B typed receipt, and a further APT sanitizer-class tightening.

### Resumption rules added by this interruption

- A local timeout or interrupted chat does not imply that a hosted job, merge, or remote write stopped. Refresh the exact head, run, artifact, and canonical carrier before retrying.
- Do not interpret a package status such as 6 without the retained first-event transcript and typed focus state.
- When a newer current-main carrier already contains the useful bytes and gates, retire the older branch instead of replaying it.
- Preserve partial branch identity when it explains provenance, but do not let it remain an apparent live fix.
- Update the durable checkpoint before switching work units, especially while a long job is running or a classifier is being repaired.

### Next safe action

Review the current-main Packet B artifact-metadata identity follow-up before any new package rerun. Keep Packet B on hold until one focused execution guarantees that `root-without-cap-sys-admin` actually completes and records its own outcome. Treat the broad `chrootless` failure as a separate investigation.

External contact remains unauthorized and none was made.

## Authority

Internal Linux Fieldwork process note only. No OpenAI, Codex, Debian, or other external report, issue, email, comment, or review was sent or authorized.
