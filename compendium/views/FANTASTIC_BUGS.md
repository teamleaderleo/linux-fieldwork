# Fantastic Bugs and How to Find Them — Linux Fieldwork seed

## In simple words

This view turns the first Linux Fieldwork extraction into a quick hunting guide. The entries remain derived from concrete case evidence; this page is only a readable route through them.

## Reachable before owned

```text
allocate → publish → own later
```

Look for objects that become reachable before reference counts, allocator state, reservations, leases, or other reuse-prevention state become authoritative.

**Probe:** fail between ownership and publication, then reopen/reconcile and attempt reuse.

Entry: `publication-before-ownership`.

## Clean even though required work failed

```text
sync/validation fails → clean/success marker still published
```

Look at clean bits, current-generation stamps, successful aggregate results, and readiness markers. Ask what work makes each marker truthful.

**Probe:** force prerequisite failure, inspect the marker directly, then exercise the consumer that trusts it.

Entry: `false-clean-certification`.

## The only retryable copy was thrown away

```text
remove dirty/recoverable owner → fallible handoff → failure → nothing left to retry
```

Look at eviction and replacement code that mutates bookkeeping before I/O or another fallible successor operation.

**Probe:** make the handoff fail, repair the environment, then retry through the ordinary path. The original state must still exist.

Entry: `recoverable-owner-dropped-before-handoff`.

## A symptom impersonates completion

```text
proxy symptom → reuse begins → real owner still settling
```

Common suspects include connection loss, process disappearance, socket creation, EOF, and log lines.

**Probe:** make the proxy happen while delaying the owner-issued terminal event.

Entry: `proxy-signal-for-authoritative-state`.
Technique: `authoritative-event-observation`.

## The queue was acknowledged before the work was done

```text
receive → ACK/delete → handler fails → no redelivery
```

Read the queue contract first. Find exactly which action removes replay authority.

**Probe:** fail the first operation after acknowledgement, restart, and inspect replay.

Entry: `acknowledge-before-processing`.

## Rollback after the other side already committed

```text
remote commit → ACK → local cleanup fails → old active state resurrected
```

Look for protocol commit points followed by generic failure recovery that cannot distinguish pre-commit from post-commit errors.

**Probe:** force one post-commit local error and assert rollback to the old topology is forbidden.

Entry: `post-commit-rollback`.

## Cleanup stole the result

```text
primary result complete → cleanup/signal happens → secondary outcome reported instead
```

Write the precedence table before inspecting error propagation.

**Probe:** cross product primary success/failure with cleanup success/failure and late signals.

Entry: `completed-result-overwritten-by-cleanup`.

## The numbers use different units

```text
producer index N in unit A → consumer interprets N in unit B
```

Write units next to every count, offset, bitmap bit, page, sector, tick, or alignment value at subsystem boundaries.

**Probe:** use one valid non-default granule where the wrong multiplier changes a concrete range.

Entry: `implicit-granularity-mismatch`.

## A repair pattern worth recognizing

When readers discover an object through a final pathname:

```text
unique temporary
→ complete write
→ validate
→ atomic rename/replace
```

Entry: `atomic-final-name-publication`.

## A regression pattern worth keeping

For ownership transitions, test both directions:

```text
failure: live state remains safe
success: dead predecessor eventually releases
```

Entry: `paired-failure-success-lifecycle-controls`.

## Do not collapse these merely because the words rhyme

```text
premature ACK
≠ lost ACK after a mutation may already have committed

post-commit rollback
≠ ordinary cleanup failure

publication before ownership
≠ dropping the only recoverable copy before handoff

wrong terminal-result precedence
≠ cleanup liveness preventing any result from settling
```

The distinctions tell us which repair is legal. They are part of the bestiary, not taxonomy clutter.
