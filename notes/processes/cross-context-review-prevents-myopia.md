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

## Breadth needs a stop condition

Cross-context review is not permission for endless browsing.

Before the pass, record:

- the current claim;
- the two to four adjacent contexts being sampled;
- the discriminator for each;
- the stop condition.

Stop when every selected context either:

- cannot change the mechanism, evidence boundary, compatibility claim, or next decision; or
- has produced a distinct follow-up that should be separated into its own carrier.

Do not silently expand one patch to absorb every adjacent defect. Preserve the relationship, then split independent owners and tests.

## Review receipt

A compact receipt can be:

```text
claim:
adjacent contexts checked:
- context → discriminator → result
- context → discriminator → result
transferred defect classes:
new edge cases:
separate follow-ups:
stop reason:
```

The receipt belongs in the investigation, pull request, issue comment, or durable review note when the cross-context pass changes a decision.

## Practical rule

> Review narrowly enough to prove the mechanism, then broadly enough to challenge its boundaries.

Internal Linux Fieldwork guidance only. It changes no external-contact authority.