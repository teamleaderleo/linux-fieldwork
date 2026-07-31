# Research benders need discriminators and stop rules

## In simple words

Going deep is useful when each descent can still change a concrete decision.

A productive research bender is not an indefinitely growing pile of source reading, models, branches, and queued jobs. It is a sequence of bounded questions where every new probe either eliminates an option, strengthens the selected contract, exposes a different owner, or supplies a reason to stop.

The repository must remain understandable while the work is still moving. Exact heads, first distinguishing results, negative controls, cleanup state, and reopening conditions matter more than a polished story written at the end.

## What worked well

### Start with one technical result owner and one result boundary

The strongest investigations named the operation or component that owned the result before changing code.

Examples included:

- a pipeline subshell owns its temporary APT root but not the parent-owned proxy;
- a wrapper owns host, guest, signal, and cleanup results in a defined precedence order;
- a shell waiting for a foreground descendant does not automatically own that descendant's process group;
- a pipeline's final PID is not necessarily the identity of the whole pipeline job.

This made the first fixture small and prevented a broad process-lifecycle rewrite from becoming the default answer.

This is technical ownership, not exclusive human ownership. Several workers and variants may investigate the same boundary, reuse evidence, contradict one another, or produce competing candidates.

### Preserve the first surprising observation before explaining it

The useful sequence was:

1. write the exact source revision and bounded question;
2. retain the first result that distinguishes baseline from expectation;
3. record cleanup and residue;
4. only then interpret the mechanism and design alternatives.

This prevented chat narration, branch churn, or a later theory from becoming the only copy of the evidence.

### Make plausible options lose

A comparison became useful when it included controls designed to disprove attractive shortcuts.

Examples:

- final-stage PID ownership lost because upstream pipeline stages survived and `wait` remained blocked;
- worker-child ownership alone lost because parent-only delivery was still deferred;
- a helper that toggled `set -e` lost because the caller's fallback result marker disappeared;
- cleanup that retained only the last cleanup error lost because it overwrote the first cleanup failure;
- a broad process-group repair lost on proportionality when no harmful latency or supported group contract existed.

A passing candidate without a losing alternative often proves only that one arrangement can work. A negative control explains why the chosen mechanism is needed.

### Separate technical feasibility from selection

Some mechanisms were technically viable but still not selected.

Isolated process groups could provide prompt cancellation in reduced models. That did not prove that several new ownership primitives, external utility dependencies, launch-registration rules, and compatibility obligations were justified for an unmeasured latency path.

The investigation improved when it asked two separate questions:

1. Can this mechanism satisfy the contract?
2. Is this the smallest justified repository-level change for the observed consequence?

A technically possible design may correctly end as `stopped` or `HOLD`.

### Treat exact heads as expiring evidence

Long investigations frequently crossed concurrent repository changes. The reliable pattern was:

- review the exact current head;
- treat any semantic head movement as expiring the review;
- inspect the one-commit delta instead of assuming it is harmless;
- regenerate byte-identical patch and test blobs on current `main` when the landing base moves;
- allow parallel carriers while selection is open, retaining every exact head that carries unique evidence;
- after selection, keep historical heads as evidence rather than presenting every variant as the canonical successor;
- collapse incremental repair commits into one clean source generation before final review.

This preserved technical evidence without pretending that an old green run or old review authorized a newer branch.

### Distinguish product, harness, environment, and connector failures

A failed local rerun caused by GitHub name resolution was retained as a setup failure, not contradictory product evidence. A unittest import that duplicated a test class was repaired as a discovery defect, not reported as extra product coverage. A queued workflow was not treated as a failed or passing gate.

The first incomplete step has an owner. Find that owner before editing product code.

### Stop polling and continue orthogonally

Queued hosted jobs did not justify repeated status polling. Useful work continued on independent source review, canonical finding materialization, negative controls, and adjacent ownership scans.

This kept progress real while preserving the exact queued run as the only authoritative hosted gate for its head.

### Select one canonical carrier at closeout

Exploration may produce stacked, stale, current-main, and independently rewritten variants. Several active carriers are acceptable while they can still change the decision. They become harmful only when the decision has settled and several remain presented as current.

Canonicalization is a closeout result, not admission control. It must not prevent parallel reproduction, competing implementation, or deliberate replacement while evidence is still developing.

The useful closeout pattern was:

- one selected implementation or stopped record;
- exact historical heads retained for unique evidence;
- stale carriers explicitly superseded, retired, or closed;
- issue and finding pointers updated to the successor;
- one clearing gate and one next transition.

## A practical deep-work loop

Use this loop while a rabbit hole remains productive:

1. **Pin** — exact source, branch, environment, technical result owner, worker or variant map, claim, authority, and stop condition.
2. **Checkpoint** — write the live state before expensive or surprising work.
3. **Distinguish** — build a baseline failure and a passing control.
4. **Compare** — instantiate the smallest plausible alternatives.
5. **Eliminate** — run controls that can make each alternative lose.
6. **Adversarially review** — search for changed grammar, status, bytes, metadata, ownership, cleanup, and rerun behavior.
7. **Reconcile** — refresh the exact head, current base, competing work, and current decision pointers.
8. **Select or stop** — choose the best-supported bounded mechanism, or retain the negative result with reopening triggers.
9. **Clean the carrier** — after selection, produce one auditable current-main generation with exact tests, exact review, and an exact gate.
10. **Transfer** — update the owning issue and durable record; supersede stale surfaces without erasing unique evidence.

Do not deepen the same branch merely because more experiments are imaginable. Deepen it when the next experiment can change selection, claim scope, promotion state, or the reopening condition.

## Warning signs that the bender is becoming noise

Stop and restate the bounded question when:

- every new test passes but no alternative can lose;
- the candidate grows several helpers without a measured consequence;
- the only remaining uncertainty is a policy or authority decision already outside the lane;
- branch and issue prose disagree about the current decision or exact head;
- queued CI is being polled instead of independent work continuing;
- a synthetic model is being described as target-native execution;
- a setup or harness failure is pulling product code into scope;
- the work has no written stop condition or reopening trigger;
- another worker could not resume without reading the chat.

## Durable stop outcomes are successful research

A stopped investigation should retain:

- the exact question and source boundary;
- the strongest negative and positive controls;
- mechanisms that were rejected and why;
- mechanisms that remain technically viable;
- the proportionality or compatibility reason not to implement;
- the accepted behavior that remains;
- concrete evidence that would justify reopening.

This makes later duplicate or competing research informed rather than blind, while leaving future workers a precise path when conditions change.

## Compact checkpoint for a research bender

```text
RESEARCH BENDER CHECKPOINT
Unit:
Exact head and base:
Bounded question:
Technical result owner:
Active workers or variants:
First distinguishing result:
Alternatives still alive:
Alternatives eliminated:
Changed paths:
Completed gates:
Cleanup and residue:
Evidence boundary:
Stop condition:
Reopening trigger:
Next safe action:
External-contact state:
```

## Working rule

> Go as deep as the next discriminator, not as deep as the topic permits.

A good research bender leaves a smaller decision surface, a selected carrier only when selection is justified, reusable negative controls, and a repository that explains both why the selected change is justified and why the tempting larger change was not.
