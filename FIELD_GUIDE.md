# Linux Fieldwork review field guide

## In simple words

This is the practical companion to the repository rules. It records the habits that have repeatedly produced trustworthy Linux and Debian investigations, the shortcuts that repeatedly caused bad evidence, and the areas that have produced useful findings.

Use this guide while planning, implementing, self-reviewing, or peer-reviewing work. Update it when a new recurring lesson appears.

## Relationship to the working rules

[`START_HERE.md`](START_HERE.md) routes work to the smallest useful record.
[`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md) is the canonical
coordination, ownership, review, and external-contact contract. This field
guide is its practical companion: it supplies review questions, examples, and
recurring failure patterns without creating a second ownership or review
workflow.

## Core rule

A convincing report is not the goal. The goal is a bounded technical claim that survives source review, a distinguishing probe, a negative control, exact-head execution, cleanup, rerun, and peer challenge.

## Do

### Start from the exact system

- Search open and closed issues and pull requests before creating a new record.
- Search notes, investigations, target maps, programme lanes, and imported source.
- Record the exact source revision, package version, branch head, environment, and privilege boundary.
- Read the implementation and adjacent tests. Issue prose and pull-request prose are orientation, not source evidence.
- Map the owner of each operation: caller, wrapper, child process, package script, kernel, service, serializer, cache, or test harness.

### Build a distinguishing probe

- Make the probe fail on the old or deliberately broken behavior.
- Assert the complete contract, not one convenient symptom.
- Include a passing control so the classifier or detector cannot label every transcript as failure.
- When a patch changes ownership, publication, release, or reuse across a lifecycle boundary, pair the failure regression with a successful-lifecycle control where practical. The regression should keep the historical failure dead; the success control should keep the intended state transition alive through later refactors.
- Assert both sides of an ownership handoff. A live replacement should remain owned across interruption, while a dead predecessor should eventually become releasable or reusable after successful cleanup. If release is staged, check the meaningful intermediate state as well as the final endpoint.
- Keep assertion and expectation text tied to the invariant being checked rather than an incidental implementation assumption. For example, distinguish “allocator returns a different live-safe cluster” from “allocator must reuse an existing free cluster” when extension is also valid.
- Exercise failure, interruption, cleanup, and a clean rerun where relevant.
- Preserve the first meaningful failure and enough context to reproduce it.
- Prefer real local protocols, processes, filesystems, archives, and package tools over passive text inspection when execution is safe.

### Review the invisible compatibility surface

Whenever an implementation mechanism changes, compare more than the headline output:

- bytes and logical content;
- file type, mode, ownership, timestamps, allocation, and extended metadata;
- member names, link targets, PAX headers, ordering, and extraction behavior;
- exit status, signal identity, stderr, and later continuation;
- process, descriptor, socket, lock, mount, temporary path, and child ownership;
- environment variables that are intentionally preserved, normalized, or removed;
- cache publication, retry behavior, permissions, and incomplete-stream handling;
- component-level state and the complete retained tree or archive.

### Treat execution as evidence only when it is authoritative

- Run against the exact reviewed head.
- Confirm that the intended job actually ran instead of being skipped by a path, branch, permission, or merge-ref condition.
- Separate product failures from malformed patches, stale workflows, missing dependencies, formatting gates, and evidence-classifier defects.
- Retain the command, status, relevant logs, artifact name, digest, and environment.
- Re-review after every semantic change. An older green run does not validate a newer head.

### Make the work resumable before it becomes complicated

- Create a compact live checkpoint before a long hosted run, multi-tool source walk, broad scope change, or result that will be difficult to reconstruct.
- Update it after the first distinguishing observation, after every semantic head change, and before switching to another work unit.
- Keep the exact head, completed gates, first incomplete step, cleanup state, evidence boundary, and next safe action visible.
- Treat chat narration as a transport surface. Put commands, result identities, and decision-changing observations in the repository while they are fresh.
- Once the result stabilizes, move detail into the investigation and keep the live checkpoint as a short pointer instead of accumulating duplicate partial reports.

### Leave reusable knowledge

- Write down stable lessons under `notes/`.
- Keep target-specific transcripts and bounded results under `investigations/`.
- Record observations separately from interpretation and policy.
- State what was not tested.
- Name the next disposition: fix, retain, expand, block, stop, or prepare an explicitly authorized upstream packet.

### Prepare release packets for readers

- Lead with `TL;DR`, `Explain like I'm five`, and `Why care`.
- Give the issue draft one bounded observed problem, minimal reproduction, exact result, expected result, and evidence limits.
- Give the pull-request draft one bounded change, test plan, compatibility boundary, and rollback or follow-up plan.
- Point both drafts to the tracked investigation rather than pasting a second copy of every transcript.
- Keep drafts internal until the external-contact state explicitly authorizes their destination.

## Do not

- Do not approve a change because CI is green.
- Do not claim a product result when the harness stopped first.
- Do not treat one component comparison as whole-system equality.
- Do not classify a transcript by fixed category priority when the requirement is to preserve the first event in time.
- Do not use unresolved string-prefix checks before `rm -rf`, recursive removal, or other destructive operations.
- Do not introduce atomic publication without checking final permissions, ownership, and durability behavior.
- Do not clear an environment without identifying required normalized variables and supported execution modes.
- Do not treat process creation as readiness.
- Do not treat EOF as a complete response when a declared length says otherwise.
- Do not rewrite archive payload layout while retaining stale metadata describing the old layout.
- Do not let a test merely record values that its report later describes as required.
- Do not maintain duplicate canonical fixes for the same defect.
- Do not combine independent defects into one patch unless the stack and test ownership are explicit.
- Do not silently broaden a claim beyond the exact fixture, platform, privilege level, format, signal, or protocol that ran.
- Do not leave the only copy of a command, exact head, artifact identity, first failure, or next action in chat.
- Do not contact an external project without explicit repository authority.

## 🍩 Donuts

A **donut** is work that looks complete around the outside but has a hole in the middle. The headline improvement is real, but an untested compatibility or evidence boundary makes the conclusion incomplete.

Common donuts found during Linux Fieldwork:

### Atomic but inaccessible

A cache file is published atomically, but the temporary-file mechanism changes the final mode from the baseline `0666 & umask` contract to `0600`.

**Check:** permissions, ownership, umask behavior, replacement semantics, and other consumers.

### Guarded but unresolved

A path begins with `/tmp/`, passes a prefix check, and later resolves through `..` or a symlink to a parent selected for recursive deletion.

**Check:** resolve first, reject roots, require a strict child, then delete.

### Sanitized but broken

A scrubbed environment removes credentials but also removes a safe value that the program already normalized, such as a target-contained temporary directory or fakeroot state.

**Check:** every supported mode, required variables, caller values versus program-normalized values, and false positives.

### Green but unexecuted

The repository suite passes while the actual privileged, Debian, matrix, or long-running job was skipped, missing, unable to obtain a merge ref, or stopped before the probe.

**Check:** job presence, step conclusions, exact head, artifact contents, and real status.

### Correct result, missing recovery state

A branch, workflow, or chat contains useful work, but the repository does not say which head produced the observation, where execution stopped, what cleanup completed, or what command should run next.

**Check:** exact head, changed paths, first distinguishing result, first incomplete step, artifact or gate identity, cleanup state, evidence boundary, and next safe action. Another worker should be able to resume without the conversation.

### Correct label, wrong event

A classifier recognizes mirror, preflight, named-case, and wrapper failures, but chooses a fixed precedence after scanning the complete log instead of retaining the first failure in transcript order.

**Check:** mixed-phase logs and failures before and after named cases.

### Equal components, unequal target

A script log and alternatives entry are equal, but the complete target tree differs.

**Check:** define each equality layer and retain whole-tree or whole-archive diffs.

### Correct cache, damaged first client

A short upstream response is prevented from poisoning the final cache, but headers were already sent and the first client still received a partial HTTP 200 response.

**Check:** state clearly whether the fix protects cache integrity, downstream signaling, or both.

### One source gate bypassed, another remains

A wrapper avoids a formatter check but still fails POD, lint, shell, mirror, or workflow preflight before behavioral execution.

**Check:** map the complete preflight sequence and bypass only the source-only boundary that is invalid for the installed artifact.

### Correct sparse bytes, stale sparse metadata

A rewritten archive carries expanded logical bytes while preserving a map that describes compact sparse extents, or dense fallback removes one required header but leaves the rest.

**Check:** content hash, extents, hole bytes, allocation, archive size, type flag, and every sparse header.

### Signal observed, success still reported

A handler logs a signal but never stores it, so later code cannot distinguish interruption from successful child completion.

**Check:** owner-only and process-group delivery, all handled signals, first-signal retention, child cleanup, and rerun.

### Cleaned but still running

A signal handler performs cleanup and returns, so the script continues into later work and may invoke the same cleanup again through `EXIT`. A similar re-entry occurs when an ordinary path calls cleanup while an EXIT trap still points at it and cleanup fails.

**Check:** separate ordinary EXIT from signal termination, clear or ignore overlapping traps before cleanup, define `primary or signal > cleanup > success` precedence, assert the later-work marker is absent, count cleanup calls, and run an immediate clean rerun.

## Areas that have been fruitful

### Lifecycle and interruption

Signals, cancellation, child ownership, background-service readiness, cleanup traps, process groups, waits, and repeated execution frequently expose misleading success or leaked state.

### Paths, names, and containment

URL decoding, archive member paths, link targets, `..`, absolute paths, symlinks, caller-controlled output roots, and account-name matching are high-yield because small string assumptions cross real security boundaries.

### Metadata-preserving transformations

Sparse files, PAX headers, type flags, ownership, permissions, timestamps, ordering, hard links, symlinks, transform flags, and extraction semantics reveal defects that simple content checks miss.

### Chrootless package execution

Host configuration, maintainer-script environment, service inhibition, needrestart hooks, temporary directories, fakeroot, apt-versus-dpkg execution, and host-session sockets remain productive because chrootless mode deliberately crosses boundaries.

### Package-test infrastructure

Mirror readiness, suite selection, package dependencies, subordinate-ID setup, source-formatting gates, workflow branch selection, retained first failure, and neutral exit classification often own an apparent package regression.

### Caches and streaming protocols

Concurrent misses, partial final-name visibility, premature EOF, declared lengths, retries, file modes, cache-root containment, symlink races, and downstream-after-header errors are productive because correctness spans network, filesystem, and concurrency contracts.

### Evidence schemas and classifiers

Machine-readable summaries can be wrong while the raw trace is correct. Enums, schema versions, event ordering, explicit unknown states, whole-tree comparison, and synthetic negative controls improve every later investigation.

### Reproducibility boundaries

Build path, time, locale, timezone, hostname, user identity, parallel scheduling, file order, declared epochs, archive metadata, and buildinfo/changes output are useful when varied independently and described without overclaiming isolation.

## Things to keep in mind during review

Ask these questions in order:

1. What exact claim is being made?
2. Which source line or operation owns it?
3. Does the test fail for the old behavior?
4. Does it assert the full written contract, including both failure and successful lifecycle behavior when ownership, cleanup, or reuse changes?
5. Did the intended exact-head job actually run?
6. What happens on failure, interruption, retry, and rerun?
7. What state survives: files, modes, processes, descriptors, sockets, mounts, locks, environment, cache entries, or metadata?
8. Did the mechanism change a compatibility property outside the headline result?
9. Is a component-level observation being described as whole-system behavior?
10. Is the first failure preserved in time order?
11. Are the evidence limits written as clearly as the result?
12. Is the durable note useful without reading the original pull request?
13. Is there one canonical issue and one canonical fix carrier?
14. Has upstream contact remained inside the authorized boundary?
15. Could another worker resume from the repository alone, including the first incomplete step and next safe action?
16. Which premises are fixed for this decision: source generation, operation owner, input class, lifecycle phase, platform or mode, privilege boundary, and result interface?
17. Which adjacent contexts could still change the mechanism, compatibility claim, evidence boundary, or next decision, and what discriminator was used for each?
18. Do the remaining concerns invalidate the claim inside those premises, or do they require a materially different experiment?
19. What exact counterexample, identity change, claim expansion, or authority change would reopen the decision?

## Decide when the bounded review is saturated

A reviewer should not claim that unknown defects are impossible. The useful conclusion is narrower: the declared question is saturated inside its stated premises, and the remaining plausible concerns need a different experiment.

Before stopping broad review:

- classify known knowns, known unknowns, recovered unknown knowns, and the controls used against unknown unknowns;
- confirm that every important branch inside the fixed premises has executed evidence, a distinguishing control, or an explicit source contract;
- prove that the mechanism can lose rather than only confirming the candidate;
- direct the adjacent search toward named caller/callee, setup/cleanup, producer/consumer, representation/metadata, ownership, mode, history, or evidence-path discriminators;
- reconcile source, patch, branch head, checkout class, test discovery, artifact, cleanup, and rerun identities;
- separate concerns that invalidate the present claim from successor questions that change a platform, topology, authority, integration surface, input class, or source generation;
- write residual risks and concrete reopen triggers.

Do not stop because CI is green, a planned test passed once, a fixed review count was reached, no one immediately imagined another case, or the investigation is tiring.

Use [`notes/processes/cross-context-review-prevents-myopia.md`](notes/processes/cross-context-review-prevents-myopia.md) for the full known/unknown matrix, seven-part search-saturation test, residual-risk record, reopen rules, and compact receipt.

## Investigation selection heuristic

Prefer questions with:

- an exact source owner;
- a small distinguishing fixture;
- at least two plausible outcomes;
- a clean negative control;
- bounded privilege and cleanup;
- a result that changes a concrete next decision;
- nearby code that appears to assume completeness, readiness, containment, identity, ordering, or compatibility.

Avoid broad exploration that cannot name a distinguishing result, cleanup boundary, or disposition.

## Maintenance

Add a new entry when the same mistake or successful technique appears more than once, or when one finding generalizes cleanly across targets. Keep exact transcripts and one-off details in their investigation records; keep this guide focused on reusable judgment.

Version boundary: lessons retained from Linux Fieldwork work through 2026-08-14. Revalidate tool-, distribution-, and upstream-specific details when they change.
