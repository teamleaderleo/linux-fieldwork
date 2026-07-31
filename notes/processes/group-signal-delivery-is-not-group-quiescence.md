# Group signal delivery is not group quiescence

## In simple words

Sending a signal to every process in an owned group is one useful guarantee. It does not prove every process stopped.

A wrapper may exit while a descendant ignores or defers the signal. Waiting for the wrapper then succeeds even though backend work remains alive.

## Separate the contracts

Review cancellation in four layers:

1. **delivery** — did the selected signal reach the intended operation group?
2. **leader settlement** — did the immediate wrapper exit and get reaped?
3. **group quiescence** — are any live non-zombie group members still running?
4. **result stability** — can a later parent signal interrupt cleanup or replace the first result?

Evidence for one layer must not be silently promoted into another.

## Why first-signal retention is not enough

A common repair ignores later SIGINT or TERM while cleanup runs. That protects the first cancellation result and avoids reentrant handlers.

It is safe only when cleanup is independently bounded. When a child ignores TERM, suppressing later SIGINT can turn an interruptible hang into an uninterruptible wait.

Use this review question:

> What event ends the cleanup wait when every cooperative assumption fails?

If the answer is only “the child eventually exits,” first-signal retention has not solved liveness.

## Bounded policies are different choices

### Diagnostic-only bound

A supervisor may wait for a grace interval, report surviving PIDs/groups, and return without escalation.

This provides bounded caller behavior and useful evidence. It intentionally leaves work running and must say so.

### Escalating bound

A supervisor may send TERM, wait a documented grace interval, report survivors, then send KILL to the still-owned group.

This can establish quiescence for in-group processes, but it changes product policy. Review:

- why the grace interval is appropriate;
- what graceful cleanup KILL can interrupt;
- whether privileged or stateful work may be killed;
- how group/session escapes are handled;
- whether group identity can be reused during the sequence;
- what diagnostics survive escalation;
- whether the platform can distinguish live processes from zombies.

Do not select escalation only because it makes a synthetic test green.

## Required comparison

Use one deterministic backend with:

- a wrapper that can exit on TERM;
- a descendant that records TERM and remains alive;
- a second mode where the wrapper also remains alive;
- parent-only first and second SIGINT;
- group, session, and reparenting records;
- later-work markers;
- ordinary unsignaled success;
- a `setsid()` escape control;
- fixture-owned cleanup independent of assertions.

Compare at least:

1. current group delivery plus unbounded wrapper wait;
2. later-signal suppression alone;
3. bounded diagnostic without escalation;
4. bounded TERM-to-KILL escalation.

## Interpreting outcomes

- **Wrapper exits, descendant survives:** leader waiting is insufficient.
- **Second SIGINT aborts cleanup:** first result and cleanup ownership are unstable.
- **Second SIGINT is ignored, driver waits forever:** first-signal retention is incomplete without a bound.
- **Driver returns with survivor report:** bounded diagnosis succeeded; cleanup did not.
- **Escalation drains the group:** the mechanism works in that topology; policy proportionality remains open.
- **Escaped descendant survives:** the ownership boundary was narrower than the operation.

## Working rule

> Own signal delivery, settlement, quiescence, and result stability as separate claims.

A strong receipt names which claims were executed and which depend on cooperative descendants.