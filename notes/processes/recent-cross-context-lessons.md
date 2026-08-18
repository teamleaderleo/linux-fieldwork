# Recent cross-context fieldwork lessons

## In simple words

The recent work has gone best when a test was allowed to disagree with the story.

A failed gate is not automatically bad news about the product. It can reveal a malformed patch, a dirty workflow state, a lossy receipt, an obsolete carrier, an intentionally different authority boundary, or a real adjacent product defect. The useful habit is to identify which one happened before changing code.

Think of it like a smoke alarm in an apartment building. Hearing an alarm tells us where to investigate; it does not yet tell us whether the fire is in the apartment, the hallway, the alarm wiring, or a scheduled drill.

## What has been working well

### Refresh the live carrier before writing

Claims are visibility signals, not locks, and parallel work is welcome. Even so, refresh the canonical issue, pull request, branch head, and current-main relation immediately before a write.

A branch that was live during the previous review may now be retired, superseded, or preserved only as provenance. Work added to it can still be useful, but it must not be described as changing the canonical candidate.

Use this sequence:

1. identify the current canonical issue and carrier;
2. read its latest disposition and exact head;
3. check whether the intended file or mechanism moved elsewhere;
4. write to the live carrier, or explicitly label the new work experimental/noncanonical.

This is not a long-lived ownership lock. It is an identity check that prevents correct work from being attached to the wrong generation.

### Let the first failure keep its real owner

The recent chrootless work crossed several failure owners in order:

- malformed unified-diff counts stopped patch application;
- a legacy workflow changed tracked source mode;
- flattened shell receipts confused different `env` invocations;
- only after those repairs did the direct and apt-managed product transactions become authoritative.

Do not edit product code merely because a product workflow is red. Classify the first distinguishing failure as product, fixture, capability, workflow, tooling, packaging, or evidence before selecting a repair.

A useful rule is:

> Repair the first owner that prevented the intended observation, then rerun unchanged downstream logic.

### Preserve command purpose, not only executable name

The same executable can participate in different contracts.

For example, a caller-path `env` invocation may be:

- a host dependency/version probe;
- a user-directed setup-hook wrapper;
- the security-relevant sanitizer that launches chrootless `dpkg`;
- another unexpected host call.

A receipt that stores only `env ran` or flattens arguments through `$*` cannot distinguish those purposes. Retain argument boundaries, classify structurally, and keep unknown calls visible.

For argv evidence, prefer one NUL-delimited record per process or another format that preserves exact elements. Include look-alike negative controls so substring matching cannot pass accidentally.

### Challenge adjacent authority, then verify intent

Cross-context review should ask whether the same defect shape exists one boundary away. It should not assume that every adjacent use has the same owner or policy.

The chrootless package-script sanitizer must not be found through caller `PATH`, because its purpose is to replace caller state before launching package management. Setup hooks are different: they are explicit host-side user actions and may intentionally inherit host command lookup. Hardening only their `env` executable while leaving their shell, interpreter, or hook helper under caller lookup would create a partial and misleading authority claim.

An unexpected adjacent call therefore has two legitimate outcomes:

1. it is a real new product surface and receives a separate owner and losing control; or
2. it sharpens the current boundary because the adjacent operation intentionally has different authority.

Both outcomes are useful. Do not force every broad review to produce a larger patch.

### Promote evidence one layer at a time

The most reliable progression has been:

1. exact source owner and current-main applicability;
2. zero-fuzz retained patch composition;
3. focused losing and negative controls;
4. complete syntax/format checks;
5. direct product transaction;
6. mediated or wrapper transaction;
7. failure, interruption, cleanup, and rerun where relevant;
8. exact-head repository and dedicated hosted gates;
9. artifact identity and complete-diff review.

Each layer should reuse the same candidate bytes where possible. When two paths need the same candidate, prepare it once and pass exact paths forward rather than rebuilding subtly different copies.

### Treat workflow steps as stateful neighbors

A workflow is not a set of isolated commands. Earlier steps can change modes, files, caches, environment, generated source, permissions, or process state seen by later steps.

Before accepting a later result:

- record the input state it inherited;
- restore temporary mutations made by earlier steps;
- fence tracked source with Git status or exact hashes;
- retain separate result directories;
- ensure cleanup does not erase the first failure evidence;
- verify a clean rerun from a fresh target.

A test that preserves its incoming dirty state is behaving correctly when it refuses to certify a clean repository.

### Preserve partial outcomes before terminal errors

Some mutation and recovery APIs intentionally return both completed result rows and a terminal error. A cancellation may arrive after the first branch was deleted or restored but before the next delayed operation begins. Treating the error as if nothing happened loses the evidence needed for undo, recovery, and accurate reporting.

Use this order:

1. preserve every completed result row;
2. reconcile recovery or undo receipts from those rows;
3. remove an entry only after confirmed completion;
4. retain failed, skipped, unknown, and unattempted entries by default;
5. keep the terminal error visible after receipt publication;
6. emit structured or human-readable results before returning nonzero when practical.

Safe skips may remain a successful command outcome. A result explicitly marked as a failed mutation should not silently produce exit status zero merely because the outer repository loop itself returned no Go, Rust, shell, or Python exception.

This rule applies beyond branch cleanup. Package publication, filesystem replacement, multi-object rollback, process-tree cleanup, cache recovery, and deployment teardown can all complete one durable side effect before a later step fails.

### Treat workflow admission as a separate state

A workflow file present in a branch is only prepared machinery. A `queued`, `pending`, `skipped`, `action_required`, or jobless run is only admission or platform state. None of those proves that checkout, generation, formatting, tests, cleanup, artifact upload, or self-removal occurred.

Before citing hosted execution, verify:

- which branch or pull-request base supplies the workflow definition;
- whether the event and token are allowed to trigger another workflow;
- whether a job was created;
- which exact step ran;
- which source head the job checked out;
- whether the intended assertion ran;
- whether temporary files were actually removed on a later exact head.

A workflow that promises to delete itself is still active until a later source head proves it is absent. If a helper cannot trigger, remove the dormant workflow rather than leaving hidden control machinery or describing the candidate as executed.

### Keep broad review bounded and productive

Broad review has been productive when it names two to four adjacent contexts and one discriminator for each. It becomes unproductive when it expands by association without a decision-changing question.

A good stopping result can be any of these:

- the candidate loses and needs repair;
- the fixture or receipt loses and needs repair;
- the claim narrows;
- a separate successor is created;
- the adjacent context is intentionally different and the current boundary is confirmed.

The last outcome is not “nothing found.” It is evidence that the review distinguished policy boundaries rather than treating similar syntax as identical intent.

## Reusable failure patterns recovered recently

- **Signal delivered, shell still fails:** a command may reach the process group but return nonzero, which still aborts a `set -e` path.
- **Cleanup finished, result still replaceable:** restoring a signal handler before final publication can lose the first result in a tiny final window.
- **Wrapper exited, owned group still alive:** process settlement and group quiescence are separate contracts.
- **Input identity differs from output identity:** stripping or transforming archive names can invalidate checks performed in the pre-transform namespace.
- **Green product, broken receipt:** raw logs can lose argv boundaries or classify the wrong call surface.
- **Clean local step, dirty inherited workspace:** an earlier workflow step can mutate tracked source while the later step correctly preserves it.
- **Current design, obsolete carrier:** a technically useful branch can become historical provenance while a current-main restack becomes canonical.
- **Same tool, different authority:** a host probe, user hook, sanitizer, and package child can all invoke `env` under different contracts.
- **Completed mutation, discarded result:** a caller sees a terminal error and drops the successful rows returned beside it, leaving undo or recovery incomplete.
- **Unattempted work removed from receipt:** reconciliation retains only explicit failures instead of defaulting unknown entries to still pending.
- **Failure printed, process exits zero:** candidate-level mutation rows are visible but never influence the command result.
- **Workflow committed, no workflow executed:** event authority, pull-request base, or token restrictions prevent job creation.
- **Self-removal promised, carrier still present:** cleanup instructions are mistaken for proof that the temporary workflow is gone.

## Compact operating receipt

```text
canonical issue/carrier refreshed:
exact head and base:
current claim:
first failing owner:
governed operation:
adjacent operation(s):
why authority is same or different:
structured evidence retained:
partial results returned:
terminal error returned:
receipt entries removed only on confirmed completion:
unattempted entries retained:
workflow admission state:
executed job and assertion:
temporary workflow absent at later exact head:
losing/negative control:
state inherited from prior workflow steps:
product change made:
fixture/evidence change made:
separate successor or narrowed boundary:
reopen trigger:
```

## Review questions to carry forward

1. Did the canonical carrier change since the last read?
2. Is this failure from the product, or did evidence stop before the product observation?
3. Does the receipt preserve exact elements, ordering, and process boundaries?
4. Is the unexpected adjacent call governed by the same authority contract?
5. Would the proposed hardening cover the whole authority surface, or only one executable name?
6. Did an earlier workflow step mutate the state this test inherited?
7. Can the mechanism lose on the current head without relying on an old artifact?
8. Is a new finding best composed, split into a successor, or retained as a boundary clarification?
9. Can another worker resume from the repository without chat history?
10. Did the operation return completed rows together with an error, and did the caller preserve both?
11. Does receipt reconciliation retain work that was never attempted?
12. Does a reported mutation failure produce a non-success process result after useful output is preserved?
13. Did the hosted job and intended assertion actually run, or was the workflow merely queued, skipped, or present in source?
14. Is temporary execution machinery absent from the exact head being recommended?

## Bottom line

> Broad review should make the decision harder to fool, not merely make the patch larger.

> A useful failure changes the owner, the evidence, the boundary, or the next experiment before it changes the product.

> Preserve completed work and the error that followed it; neither should erase the other.

Internal Linux Fieldwork guidance only. It does not authorize external contact or broaden destructive-operation authority.
