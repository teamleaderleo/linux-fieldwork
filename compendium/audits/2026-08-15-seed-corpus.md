# Seed corpus audit — 2026-08-15

## In simple words

This pass samples retained Linux Fieldwork cases that already have enough evidence or reusable explanation to pressure-test a bug compendium. The goal is not to canonize every catchy name. It is to identify structures that survive comparison, preserve important distinctions, and expose useful hunting questions.

The strongest first lesson is that several cases really do rhyme across domains, but many nearby cases share vocabulary while differing at the decisive owner or commit boundary.

## Candidate matrix

| Source | Candidate reusable idea | Likely kind | Invariant / question | Strong technique | Generalization risk |
|---|---|---|---|---|---|
| #609 | publication before ownership | bug species | live/reachable objects must already be excluded from reuse | failure-window interruption + reopen | do not assume every publication has a separate ownership phase |
| #611 | false clean-state certification | bug species | clean marker implies required synchronization succeeded | force sync failure + reopen | broader false-success family is valid only when success claims complete work |
| #645 | recoverable owner dropped before fallible handoff | bug species | retain a retryable owner until successor state is established | fail eviction write + retry | related to publication/retirement, but the core defect is loss of retryable state rather than reachability-before-ownership |
| #423 | proxy signal mistaken for authoritative completion | bug species | next lifecycle transition waits for owner-issued completion evidence | delay real completion after proxy | a proxy can be authoritative by explicit contract |
| #517 | acknowledgement before processing | bug species | replay-removing acknowledgement follows durable/complete local handling | fail first post-ack action + restart | separate from ambiguous acknowledgement *loss* after a mutation may already commit |
| #606 | post-commit rollback | bug species | remote commit forbids local rollback that recreates the old active state | fail source-local cleanup after remote Complete ACK | related to acknowledgement ordering but legality changes at a protocol commit point |
| #297 | completed result overwritten by cleanup | bug species | selected authoritative outcome survives later cleanup/signals | inject late signal/cleanup failure | distinguish result precedence from cleanup liveness |
| #580 | missing terminal event owner | bug species candidate | every observable started attempt has one terminal success/failure owner | force errors at several return sites | event taxonomy may legitimately distinguish pre-start and post-start failure |
| #617 | implicit granularity mismatch | bug species | cross-layer units/granularity must be explicit and owner-derived | synthetic non-default granule | do not infer all hard-coded sizes are bugs; backend contracts may intentionally differ |
| reliability cache note | atomic final-name publication | repair pattern | final visible name means complete object | synchronized concurrent reader/writer | atomic rename does not provide integrity or request coalescing |
| lifecycle test note | pair failure and success lifecycle controls | regression pattern | failure keeps live state safe; success eventually releases dead state | mirrored controls | do not preserve obsolete staging mechanisms merely because a test can exercise them |
| ownership note | prepare → own → publish → retire | repair pattern | ownership before publication | stop at each arrow | not a universal transaction template |
| #69 | sanitization changes default containment | candidate species | removing ambient state must not silently select a less-contained default | compare explicit/absent env | environment semantics are tool/platform-specific |
| FEX #672 | escaped executable lifetime outlives wrapper | candidate species | code/data whose address escapes must outlive every retained reference | forced unload/reload generation | very mechanism-specific; likely needs a broader cross-domain sibling before naming generically |

## Strong cross-domain graduates already visible

### False success after incomplete work

Linux #611 and Fieldwork #626 preserve the same core relation despite very different mechanisms:

```text
required work did not complete
→ status surface forgets that fact
→ caller sees success/clean/empty
```

This is strong enough for a generic Fieldwork entry, while `false-clean-certification` remains a useful Linux/storage specialization.

### Cleanup result precedence

Linux #297 and several async/runtime cases in Fieldwork share:

```text
primary result becomes authoritative
→ later cleanup/signal/cancellation produces another outcome
→ later outcome must not silently replace the selected one
```

Keep this separate from cases where cleanup blocks forever. “Wrong result wins” and “right result never gets published” can share a policy family without being one bug species.

### Authoritative state versus proxy observation

Linux #423 is a clean concrete case. The generic rule transfers well to async controllers and tests, but only when the observed symptom is weaker than the owner-issued transition.

## Similar-looking cases that should remain separate

### #517 acknowledgement-before-processing versus Fieldwork ambiguous external outcome

They both mention acknowledgements, retries, and interruption, but the failure grammar differs.

#517:

```text
message is replayable
→ consumer deletes/acks it
→ required local handling fails
→ replay source is gone
```

Ambiguous external outcome:

```text
mutation may already have committed remotely
→ acknowledgement/result is lost
→ local state cannot tell committed from absent
```

Moving an acknowledgement later helps the first family. It does not solve the second; the second needs stable identity/idempotency/reconciliation.

### #606 post-commit rollback versus ordinary cleanup failure

After the destination acknowledges the migration commit point, source-local cleanup errors no longer authorize returning to the pre-commit topology. The important rule is not merely “cleanup errors are secondary.” It is:

```text
commit point crossed
→ rollback legality changed
```

That deserves its own species.

### #645 recoverable-owner loss versus #609 publication before ownership

Both involve metadata ordering and conservative failure states, but:

- #609 allows a live object to be reconstructed as reusable because ownership was not established before publication;
- #645 destroys the only dirty retryable copy before a fallible persistence step succeeds.

A future higher-level family may unify them as unsafe handoffs, but the first seed should preserve the distinct owner relationships.

## Reusable techniques worth first-class entries

1. **Failure-window interruption** — ask “what if we stop right here?” at meaningful phase edges.
2. **Reopen/restart testing** — reconstruct truth from durable state rather than trusting the live process.
3. **Immediate clean rerun** — expose leaked locks, stale state, orphaned resources, or non-idempotent cleanup.
4. **Authoritative-state observation** — wait on the state/event owned by the transition owner rather than a correlated symptom.
5. **Negative control** — prove the probe can also recognize correct behavior.
6. **Earliest divergence** — compare good/bad traces and find the first meaningful state difference.
7. **Paired failure/success lifecycle controls** — preserve both safety after interruption and release after ordinary success.
8. **Commit-point tracing** — identify exactly where rollback/retry legality changes.
9. **Cross-context discriminator** — test sibling owners/backends before widening a rule.
10. **Unit/granularity perturbation** — rerun logic with a valid non-default unit to expose hidden constants.

## Concepts that recur enough to deserve glossary objects

```text
publication
ownership
reachability
reusable/free state
durability
clean marker
retryability
idempotency
authoritative state
observation
reconciliation
attempt identity
acknowledgement
partial progress
operation owner
authority boundary
terminal owner
commit point
remote-effect certainty
generation
granularity
```

Several need domain-qualified definitions. In particular, Rust ownership, allocator ownership, cleanup ownership, and lease ownership have useful structural overlap but are not interchangeable.

## First extraction tranche

Materialize these before adding more taxonomy:

### Bug species

- `publication-before-ownership`
- `false-clean-certification`
- `recoverable-owner-dropped-before-handoff`
- `proxy-signal-for-authoritative-state`
- `acknowledge-before-processing`
- `post-commit-rollback`
- `completed-result-overwritten-by-cleanup`
- `implicit-granularity-mismatch`

### Techniques / repair / regression patterns

- `atomic-final-name-publication`
- `authoritative-event-observation`
- `paired-failure-success-lifecycle-controls`

The first tranche intentionally does **not** create an umbrella `unsafe-handoff` species. That name currently hides distinctions that matter for repair selection.

## Retrieval questions to test after materialization

```text
corruption appears only after reopen

success even though selected work was skipped

message cannot be replayed after handler failure

remote side already committed but local code wants rollback

cleanup signal replaced a result that was already complete

works on 4K but fails when the backend unit is 16K

reader saw a final cache name before bytes were complete
```

A useful index should surface both the direct species and nearby techniques/counterexamples without requiring the reader to know which note directory contains the original lesson.

## Next corpus expansion

The next pass should deliberately sample outside QCOW and Cloud Hypervisor:

- QEMU/process publication and cleanup lanes;
- file-mirror path/cleanup confinement;
- tar/archive representation and metadata cases;
- maintainer-script interruption/idempotency;
- signal-result precedence cases;
- FEX thunk lifetime as a possible escaped-reference lifetime family;
- negative results where a superficially similar ordering turned out intentional.

That expansion should be used to break the current model, not merely confirm it.
