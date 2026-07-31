# Why the update_cache review can stop without claiming omniscience

Audience: maintainers, reviewers, release decision-makers, and presenters who need to explain why the bounded lifecycle result is complete even though software can always contain undiscovered behavior.

Status: `post-merge epistemic boundary and search-saturation record`

## The direct answer

We do **not** know that there is nothing else anywhere in `make_mirror.sh`, APT, the shell, the process tree, or current upstream mmdebstrap.

We do know that additional broad searching is no longer required to decide the question that PRs #286 and #324 answered:

> When INT, QUIT, or TERM is delivered to the `update_cache()` shell owner, how should that worker preserve ownership, complete bounded cleanup once, retain the first accepted signal, and select its final status?

That decision is saturated because repeated review found no unclassified branch inside that owner-PID, bounded-cleanup model. Every remaining concern changes at least one material premise, such as signal topology, cleanup boundedness, descendant cooperation, full-mirror execution, shell family, or upstream version.

Those are valid follow-up questions. They are not hidden missing cases inside the completed question.

## Explain like I am five

We inspected one room and its emergency exit.

We checked:

- who owns the furniture;
- what happens when the alarm rings;
- what happens if another alarm rings during cleanup;
- whether cleanup happens once;
- whether the next person can use the room cleanly.

There are other rooms in the building. Some have different doors, different alarms, or machinery that may refuse to stop. We are not claiming those rooms were inspected.

We can stop inspecting this room because the remaining questions require entering a different room, not looking under the same chair again.

## The known/unknown matrix

| Category | Meaning here | Current contents | Required action |
| --- | --- | --- | --- |
| Known knowns | Questions directly executed or tied to exact source and patches | owner separation; INT/QUIT/TERM statuses; first-signal retention; once-complete bounded cleanup; result precedence; no later work; removed APT state; immediate rerun; patch composition | retain as the accepted bounded result |
| Known unknowns | Important questions explicitly outside the executed model | whole-process-group delivery; cleanup child receiving the same terminal signal; TERM-resistant descendants; group/session escape; HUP; timeout/escalation; blocking cleanup; full mirror integration; current upstream acceptance | track as separate experiments or policy decisions |
| Unknown knowns | Relevant knowledge that existed elsewhere but had not initially been connected to this case | `run_qemu` cleanup races; top-level proxy ownership; process-group work; explicit unittest discovery; PR checkout-identity classification; conventional shell status practice | surface through cross-context review and incorporate into the record |
| Unknown unknowns | Failure modes not presently named or represented in the model | by definition cannot be enumerated conclusively | reduce exposure through bounded claims, adversarial controls, review diversity, exact identities, rerun tests, and clear reopen triggers |

## Known knowns

The following statements have direct evidence inside the selected model:

1. `update_cache()` is a subshell worker and owns its temporary APT root.
2. The top-level script owns the cache proxy.
3. The imported combined trap crosses those owners.
4. Cleanup commands in a signal trap do not themselves guarantee termination.
5. The losing lifecycle can continue later work, clean twice, kill the parent-owned proxy, or report status 0 after cancellation.
6. Patch 0001 separates parent and worker ownership and introduces one finalizer.
7. INT, QUIT, and TERM are represented as 130, 131, and 143 in the selected shell-status interface.
8. Existing ordinary or explicit-signal failure outranks cleanup failure.
9. Resetting handled signals to default before cleanup creates a competing-signal window.
10. Patch 0002 records the first signal accepted during ordinary cleanup and ignores later handled signals after selection.
11. Cleanup completes once in the deterministic bounded fixture.
12. Temporary APT state is removed, later work is absent, and an immediate unsignalled rerun succeeds.
13. Both patches apply to the retained imported source with zero fuzz.
14. The merged patch and test blobs remain present in current repository history.
15. Historical PR CI 911 and 916 are synthetic merge-ref integration evidence, not literal-head execution.

The conclusion is not based on one green status. It is based on a consistent event model, losing controls, repaired controls, source identity, patch identity, state inspection, and rerun behavior.

## Known unknowns

The following questions are intentionally unresolved:

### Different signal topology

- What happens when a terminal sends the same signal to the shell and cleanup child?
- Should the complete foreground process group be signalled?
- Can descendants move into another group or session?

These require a process-group fixture and ownership policy. They cannot be answered by adding another owner-PID assertion.

### Different cleanup contract

- Can real `cleanupapt` block indefinitely?
- Should cleanup have a deadline?
- When, if ever, should TERM escalate to KILL?
- What diagnostics should be retained for survivors?

These require timeout and escalation policy. The landed result assumes bounded cleanup.

### Different integration surface

- Does the complete mirror workload behave correctly under cancellation?
- Do APT, network, filesystem, and proxy timing introduce another owner?
- Does current upstream source retain or replace this lifecycle?

These require a disposable full integration and a refreshed upstream comparison.

### Different interface policy

- Should QUIT be returned as 131 or re-raised?
- Should callers receive conventional shell status or direct signal termination?

These are interface choices, not defects hidden by the current precedence tests.

## Unknown knowns and how they were recovered

“Unknown knowns” are facts the project already possessed but had not yet applied to this exact worker.

The review deliberately searched for them in adjacent work:

- `run_qemu` showed that later signals can replace the first result when traps are reset before cleanup;
- top-level `make_mirror` work clarified proxy ownership and registration windows;
- coverage work separated owner-PID delivery from whole-process-group delivery;
- QEMU image lifecycle work reinforced publication, cleanup, and rerun distinctions;
- reusable process notes recorded cleanup re-entry and first-signal rules;
- the explicit unittest runner clarified which inherited tests execute;
- PR evidence-identity work corrected “exact head” versus generated merge-ref language.

After these contexts were applied, they narrowed claims or improved receipts. None exposed another source-visible branch inside the selected owner-PID finalizer.

That is the practical reason additional undirected repository wandering has diminishing value for this decision.

## Unknown unknowns cannot be eliminated

No finite review proves the absence of every possible defect.

The responsible goal is therefore not “zero unknown unknowns.” It is:

1. make the claim narrow enough that evidence actually supports it;
2. search adjacent contexts most likely to contain a counterexample;
3. preserve losing controls so the test can still distinguish the defect;
4. inspect state, not only exit status;
5. rerun after interruption to detect residue;
6. retain exact source, patch, checkout, and test identities;
7. name the conditions that would reopen the conclusion.

This converts unknown-unknown risk from an unqualified confidence claim into a controlled residual risk.

## Search-saturation test

A bounded review may stop when all of the following are true.

### 1. The question has fixed premises

The owner, signal destination, lifecycle phase, cleanup boundedness, source generation, and result interface are stated explicitly.

### 2. Every branch inside those premises has a disposition

For this lifecycle, the relevant event branches are:

- ordinary success;
- ordinary failure;
- explicit INT, QUIT, or TERM;
- signal during ordinary cleanup;
- later handled signal during explicit-signal cleanup;
- cleanup failure;
- result selection;
- immediate rerun.

Each has executable evidence or an explicit source contract.

### 3. Losing implementations remain visible

The imported and predecessor paths still demonstrate false success, cleanup interruption, result replacement, re-entry, or ownership crossing. The test suite is not merely proving that the final code returns expected constants.

### 4. Adjacent precedents no longer change the mechanism

Cross-review of related signal, process, cleanup, publication, and test-discovery work produced claim corrections and evidence improvements, but no additional finalizer branch.

### 5. New concerns require a changed premise

The remaining questions require process-group delivery, resistant descendants, timeout policy, full integration, another shell, or current-upstream comparison.

A concern that requires a new premise should become a separate bounded investigation rather than indefinitely expanding the completed one.

### 6. Identity and execution receipts are explicit

The record distinguishes source blobs, patch blobs, PR heads, generated merge checkouts, merged content, and current persistence. A green run is not allowed to stand in for an execution identity it did not test.

### 7. Rerun and cleanup state agree with the result

The final status, absence of later work, removed temporary state, once-only cleanup log, and immediate rerun all tell the same story.

PRs #286 and #324 meet this saturation test for the stated model.

## Why not keep searching the entire codebase anyway?

Undirected searching has costs:

- it mixes different contracts into one review;
- it makes completion impossible to define;
- it encourages weak analogies to replace executable evidence;
- it can reopen accepted ownership decisions without a counterexample;
- it obscures which test would change the decision;
- it delays review of genuinely open, higher-risk units.

The better policy is directed expansion:

> Search elsewhere when a concrete analogy can falsify, narrow, or compose with the current claim. Stop when new contexts only restate already recorded boundaries or require a different experiment.

This review followed that policy. Related contexts changed the documentation and evidence terminology, but eventually stopped changing the selected mechanism.

## Counterexample rule

The bounded result must be reopened if any of these is demonstrated:

- an owner-PID INT, QUIT, or TERM path inside the retained shell model returns a result outside the declared precedence;
- cleanup executes more than once;
- later worker code executes after handled cancellation;
- temporary APT state remains after the repaired bounded cleanup;
- a later handled signal replaces an already accepted result;
- the immediate rerun observes residue;
- the retained patches no longer apply exactly to the claimed source;
- current repository discovery no longer executes the intended controls;
- a claimed execution receipt is shown to have tested different bytes or a different checkout class.

By contrast, a process-group survivor, TERM-resistant descendant, blocking cleanup, HUP policy dispute, or full-mirror failure should first be classified against the stated boundary. It may justify a successor investigation without invalidating the owner-PID result.

## Residual-risk register

| Residual risk | Why it remains | Current treatment |
| --- | --- | --- |
| foreground cleanup child receives terminal signal directly | owner-PID fixture does not model terminal group delivery | separate topology experiment |
| descendant ignores TERM or escapes group | descendant cooperation is outside bounded finalizer | process-group and survivor policy |
| cleanup blocks forever | fixture cleanup is deliberately bounded | timeout/escalation design |
| full APT/mirror interaction differs | reduced harness isolates shell lifecycle | disposable integration gate |
| shell implementation differs | executed environment is Ubuntu `/bin/sh` | portability matrix if needed |
| upstream source moved | imported source is a retained generation | refresh before external action |
| novel defect unrelated to lifecycle | no review eliminates unrelated defects | ordinary code review, tests, and future reports |

## Presentation language

Say:

- “The bounded question is saturated.”
- “Remaining risks are named and require different experiments.”
- “We searched adjacent contexts for counterexamples until they stopped changing the mechanism.”
- “Unknown unknowns are controlled by narrow claims and reopen triggers, not declared impossible.”
- “We do not need more undirected searching to make this decision.”

Avoid saying:

- “There cannot be anything else.”
- “We proved the entire script safe.”
- “Unknown unknowns are gone.”
- “Every signal topology is covered.”
- “No other code can affect this.”

## One-minute answer for a skeptical reviewer

“We cannot prove there is no undiscovered behavior anywhere. What we can show is that the decision has a fixed boundary: signals delivered to the `update_cache` shell owner while cleanup is bounded. We enumerated every event branch inside that boundary, preserved losing controls, inspected cleanup state and rerun behavior, reviewed adjacent signal and process work for counterexamples, and corrected the CI identity record. The remaining concerns all change a premise: they involve process groups, resistant descendants, blocking cleanup, full mirror execution, another shell, or a newer upstream source. Those deserve separate experiments. More undirected searching would not strengthen this exact decision unless it produces a counterexample inside the stated model.”

## Decision

The rational stop condition is:

> No additional broad search is required before accepting the canonical internal result for owner-PID INT/QUIT/TERM and bounded `update_cache()` cleanup. Continue only with a named successor question, a concrete counterexample, an identity change, or a future upstream/integration decision.

This is a completion statement for one bounded investigation, not a universal safety claim.

## Authority

Internal epistemic and review-boundary record only. External contact authorized: `false`.
