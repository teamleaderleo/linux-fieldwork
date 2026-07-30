# Helper B Codex execution recovery

Date: 2026-07-31

Tracking: issue #194, Packet B and adjacent Packet I review.

## TL;DR

A long autonomous session produced useful repository changes, but its live narration became noisy and its tool path briefly drifted. The technical work remained recoverable because exact heads, GitHub Actions runs, artifacts, issue comments, pull-request bodies, and tracked records existed outside the chat.

The recovery rule is: stop narrating, reload the live instructions, reconstruct facts from durable records, classify each failure by owner, and resume from the latest exact head.

## Explain like I'm five

Imagine building a model train while writing down every move. The train can still work even when the notebook becomes messy. To recover, look at the train, the parts on the table, and the test results. Do not guess from the messy notebook.

Here, GitHub commits and test artifacts are the train. Chat narration is the notebook.

## Why care

An agent can accidentally confuse four different things:

1. the product is broken;
2. the test harness is broken;
3. the tool used to inspect or edit the repository failed;
4. the narration lost the current decision boundary.

Treating all four as one failure causes needless product edits, duplicate branches, stale receipts, and misleading confidence.

## Safe execution log

This is a factual execution log, not hidden chain-of-thought.

1. Packet B exact-head tests passed after repairing a missing per-run directory in the guard harness.
2. The first composed Debian sid run stopped at Black before functional cases because the retained `coverage.py` hunk used a form Black rewrote.
3. The formatter-compatible patch passed focused repository CI.
4. The second composed sid run completed the container and uploaded evidence, then classified the package test as exit 6.
5. Artifact inspection showed the Packet B capability case never ran. The earlier main phase stopped on `cwd-directory-not-accessible-by-unshared-user`: that test changes directory and the temporary proxy command was relative (`./mmdebstrap`).
6. A parallel worker repaired the carrier to use `$SRC/mmdebstrap` and added a working-directory-change regression.
7. During adjacent PR #109 review, a retained unified diff had one malformed hunk count. A direct patch application check caught it; the hunk count was repaired before relying on CI.
8. Attempts to download raw GitHub files directly through the local container failed because the URL had not been opened through an approved connector path and because the container had no external DNS. GitHub connector fetches were used instead.
9. The session then reloaded `README.md`, `START_HERE.md`, `ADAPTIVE_COORDINATION.md`, `FIELD_GUIDE.md`, and issue #194 before continuing.

## What went wrong in the working process

### Narration outran the decision

Updates continued while long jobs were active, producing a large stream of partial states. A reader could lose the current disposition even though the repository records stayed accurate.

Decision: one concise update per meaningful state transition. Put detailed transcripts in tracked records.

### Tool routing was attempted through the wrong path

The local container was asked to fetch raw GitHub content even though the GitHub connector already owned that data path. The environment rejected or could not resolve those requests.

Decision: use the source-owning connector first. Use the container only for mounted files and local execution.

### A test-carrier path assumption survived early review

The proxy worked from the suite root but failed after a test changed working directory. This was a harness defect, not a Packet B scheduling result.

Decision: commands passed into generated tests need absolute or deliberately resolved paths. Add a control that changes directory before invocation.

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

## Current technical decisions

### Packet B

PR #171 remains the focused scheduling candidate. Its parser, hard-failure, timeout, hook-exclusion, and capability-assertion contracts passed exact-head repository tests. The sid composition failure belongs to PR #72's temporary relative proxy carrier. Packet B should advance after a composed run reaches the dedicated hook-free phase and records the capability case result.

### PR #72

Keep as an investigation carrier. The proxy is useful for reduction and unsuitable as final reusable tooling because it changes the original source-preflight subject. Use an absolute staged proxy path during reduction; remove the proxy before any reusable-tooling merge decision.

### PR #109

Keep at `REPAIR`. The retained `/usr/bin/env` patch is a bounded product direction. Apply it on a clean current-main candidate and add fake leading-PATH `env` controls before promotion.

## Further checks worth doing

The same class is likely where a command is constructed in one directory and executed after `chdir`, namespace entry, privilege drop, or remote handoff. Search imported projects and harnesses for:

- `CMD=./...` passed into generated scripts;
- bare executable names used as security or sanitizing wrappers;
- workflows that describe a source mutation performed by a later job;
- test reports whose headline case never appears in the raw transcript;
- cleanup paths derived from caller-controlled temporary roots;
- artifacts whose classifier reads a summary instead of preserving the first raw failure.

## Authority

Internal Linux Fieldwork process note only. No OpenAI, Codex, Debian, or other external report, issue, email, comment, or review was sent or authorized.
