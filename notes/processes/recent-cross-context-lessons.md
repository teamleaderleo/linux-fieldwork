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

## Bottom line

> Broad review should make the decision harder to fool, not merely make the patch larger.

> A useful failure changes the owner, the evidence, the boundary, or the next experiment before it changes the product.

Internal Linux Fieldwork guidance only. It does not authorize external contact or broaden destructive-operation authority.
