# Cross-context review prevents myopia

## In simple words

A narrow investigation can prove the exact thing it set out to prove and still miss the next failure one boundary away.

Before selecting or landing a change, look sideways across the codebase: the caller and callee, direct and mediated paths, producer and consumer, sibling backends, lifecycle phases, retained metadata, and adjacent tests. Reuse defect classes learned elsewhere instead of waiting for each subsystem to rediscover them independently.

## Why care

Many Linux Fieldwork findings were not hidden in the headline mechanism. They appeared when a result crossed context:

- a signal result entered cleanup;
- an archive name was interpreted across repeated members;
- a safe parent path became an unsafe recursive-deletion target;
- a normalized environment still resolved its outer wrapper through caller state;
- a component-level equality claim was read as whole-tree equality;
- a retained patch was syntactically valid-looking but did not apply to its claimed source state.

The broader pass helps find edge cases, identify the actual result owner, and keep a local repair compatible with the surrounding codebase.

## Required cross-context pass

For meaningful product, harness, workflow, or evidence changes, name the adjacent contexts that could change the decision. Usually choose two to four from this map:

1. **Call path** — caller, callee, wrapper, direct path, package-manager path, retry path.
2. **Lifecycle** — setup, ordinary execution, failure, interruption, cleanup, publication, rerun.
3. **Identity** — canonical path, alias, duplicate name, stable device identity, process identity, source/head identity.
4. **Representation** — bytes, logical value, metadata, archive headers, schema, status, diagnostic.
5. **Ownership** — process, file, descriptor, lock, cache entry, mount, temporary directory, result.
6. **Platform or mode** — rootless/rootful, direct/mediated, Linux/other supported platform, backend, architecture, privilege level.
7. **History and intent** — adjacent tests, prior fixes, reverted mechanisms, compatibility comments, downstream patches.
8. **Evidence path** — fixture construction, patch application, workflow selection, exact-head execution, artifact and classifier.

For each selected context, write one question or discriminator that could make the current design lose.

## Transfer defect classes across subsystems

When one investigation finds a reusable defect shape, test nearby work for the same shape.

Examples:

- **First result replaced later** — signals, guest status, cleanup failures, classifiers, retries.
- **String identity mistaken for object identity** — paths, device aliases, archive names, process names, source refs.
- **Partial state mistaken for complete state** — EOF, archive trailers, component equality, cache publication, generated receipts.
- **Cleanup authority inferred from a parent** — recursive deletion, mount teardown, process ownership, temporary roots.
- **Sanitizer found through unsanitized state** — `env`, shells, interpreters, helper binaries, configured wrappers.
- **Green result from the wrong executable surface** — skipped jobs, duplicate discovery, stale patches, generated fixtures, merge refs.
- **Metadata left behind after payload changes** — hard links, PAX headers, sparse maps, modes, schema versions, indexes.

A transferred defect class is a hypothesis, not a verdict. Keep a negative control and allow the adjacent context to disprove it.

## Breadth needs a defensible stop condition

Cross-context review is not permission for endless browsing. Stopping does not mean claiming that unknown defects are impossible. It means the declared decision is saturated inside its stated premises, and remaining concerns need a materially different experiment.

Before the pass, record:

- the current claim;
- the fixed premises, such as source generation, operation owner, input class, lifecycle phase, platform, privilege boundary, and result interface;
- the two to four adjacent contexts being sampled;
- the discriminator for each;
- the stop condition;
- the facts that would reopen the decision.

Stop when every selected context either:

- cannot change the mechanism, evidence boundary, compatibility claim, or next decision; or
- has produced a distinct follow-up that should be separated into its own carrier.

Do not silently expand one patch to absorb every adjacent defect. Preserve the relationship, then split independent owners and tests.

## Use the known and unknown matrix

Classify the review boundary rather than relying on a vague statement that the work is “thorough.”

### Known knowns

Facts directly supported by the exact source, complete diff, executed fixture, negative control, artifact, cleanup state, and rerun.

### Known unknowns

Named questions outside the current evidence, such as another platform, process topology, protocol mode, filesystem, privilege level, full integration path, resistant descendant, or current upstream revision.

A known unknown is not a defect in the current result when answering it changes a declared premise. It should become a hold, caveat, or focused successor question according to consequence.

### Unknown knowns

Relevant knowledge that existed elsewhere but was not initially connected to the unit: adjacent tests, prior reverted designs, another investigation's defect class, downstream patches, source comments, or an earlier failure classification.

Search nearby records and history specifically to recover these. Stop when additional directed searches no longer change the mechanism, test matrix, evidence boundary, or next decision.

### Unknown unknowns

Defects that cannot be named in advance. Do not claim they have been eliminated. Reduce their practical risk through:

- a narrow claim and explicit premises;
- losing and negative controls;
- complete-diff and cross-context review;
- exact source, patch, checkout, execution, and artifact identities;
- failure, interruption, cleanup, and rerun coverage;
- residual-risk recording;
- concrete counterexamples and identity changes that automatically reopen the decision.

The objective is not omniscience. It is a decision that fails visibly when its supporting world changes.

## Search-saturation test

A bounded review may stop when all of these are true:

1. **Premises are fixed.** The owner, input class, lifecycle phase, source generation, platform or mode, and result interface are explicit.
2. **Branches are covered.** Every relevant event branch inside those premises has executed evidence, a distinguishing control, or a clearly identified source contract.
3. **The mechanism can lose.** Baseline, mutation, negative, or losing controls prove the probe is not merely confirming every implementation.
4. **Adjacent contexts were directed.** The selected caller/callee, setup/cleanup, producer/consumer, representation/metadata, ownership, mode, history, or evidence-path checks had discriminators and recorded results.
5. **Evidence identities agree.** Source, patch, branch head, checkout class, test discovery, artifacts, cleanup state, and rerun describe the same generation.
6. **Remaining concerns change a premise.** Each unresolved question requires a different platform, topology, authority, integration surface, input class, or source generation rather than another undirected reading of the same bounded unit.
7. **Reopen triggers are concrete.** The record says what counterexample, identity change, claim expansion, or new evidence invalidates the stop decision.

Failure of one item does not automatically require a larger patch. It may require a repair, a hold, a narrower claim, or a separate successor experiment.

## Residual-risk register

Record meaningful remaining risk without turning every possibility into an active blocker:

```text
risk or unknown:
which premise it changes:
why it is outside the current claim:
practical consequence if true:
current disposition: accept | hold | successor | reconvene
reopen trigger:
```

A residual risk should block the current decision when it could invalidate the claim inside the declared premises, crosses a safety or authority boundary, or has consequence too high for the available evidence. Otherwise keep it as an explicit successor question.

## Reopen the decision when the world changes

Reopen review when any of these occurs:

- the recommended branch head, base, retained patch, imported source, workflow, fixture, parser, or artifact identity changes;
- a counterexample appears inside the declared premises;
- a supposedly losing control begins to pass or a negative control stops distinguishing behavior;
- the executed checkout, discovered tests, or artifact identity no longer matches the reviewed generation;
- cleanup, rerun, ownership, or compatibility state contradicts the retained receipt;
- a broader claim is proposed than the fixture and premises support;
- a newly connected adjacent context changes the mechanism, evidence boundary, or next decision;
- the safety, privacy, destructive-operation, or external-contact authority boundary changes.

Do not reopen solely because an unlimited search could always be imagined. Reopen because a named supporting premise, identity, discriminator, or authority condition changed.

## Bad reasons to stop

Do not stop merely because:

- CI is green;
- the planned test passed once;
- no reviewer immediately thought of another case;
- a fixed number of review passes was completed;
- the branch is old or the investigation is tiring;
- the remaining concern is difficult to test;
- the prose sounds confident.

The stop reason must be tied to the bounded decision and its evidence.

## Review receipt

A compact receipt can be:

```text
claim:
fixed premises:
adjacent contexts checked:
- context → discriminator → result
- context → discriminator → result
transferred defect classes:
known knowns:
known unknowns:
unknown knowns recovered:
unknown-unknown controls:
new edge cases:
separate follow-ups:
residual risks:
reopen triggers:
stop reason:
```

The receipt belongs in the investigation, pull request, issue comment, or durable review note when the cross-context pass changes a decision.

## Practical rules

> Review narrowly enough to prove the mechanism, then broadly enough to challenge its boundaries.

> Stop searching this room when every remaining concern requires entering a different room, and write down which doors would bring you back.

Internal Linux Fieldwork guidance only. It changes no external-contact authority.
