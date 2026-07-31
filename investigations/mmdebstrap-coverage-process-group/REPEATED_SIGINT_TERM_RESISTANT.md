# Repeated SIGINT and TERM-resistant backend cleanup

State: `comparative-evaluation-active`

Tracking: issue #341.  
Exact predecessor mechanism: PR #313 head `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`.  
Comparison branch base: PR #313 documentation head `dfc6d0503fb844f4c428ce16a567a9fdcd35280a`.

## In simple words

PR #313 proves that parent-only SIGINT can send TERM to one caller-owned backend process group. That is enough for the tested backends because every modeled process responds to TERM.

It does not prove what should happen when:

- the wrapper exits but one descendant records TERM and keeps running;
- the wrapper itself keeps waiting after TERM;
- a second parent-only SIGINT arrives while the coverage driver is waiting for cleanup;
- a descendant creates another session or process group.

This comparison makes those cases explicit before any escalation policy is selected.

## Exact disposable topology

The executable comparison creates:

- one Python driver with the exact PR #313 cancellation shape;
- one wrapper in a caller-created session/process group;
- one descendant in the same group unless the escape control is selected;
- wrapper and descendant PID, PGID, SID, readiness, TERM, release, and later-work markers;
- file-backed logs;
- Linux `/proc` accounting that distinguishes live processes from zombies;
- fixture-owned TERM-to-KILL teardown.

Two wrapper modes are retained:

1. `exit` — the wrapper records TERM and exits while the descendant remains alive;
2. `hold` — the wrapper records TERM and continues waiting with the descendant.

The descendant records TERM but deliberately remains alive until a release marker appears.

## Compared policies

### A — current PR #313 policy

```text
SIGINT -> group TERM -> wait wrapper -> return 130
```

This is the accepted narrow signal-delivery contract for responsive topologies.

### B — ignore later SIGINT during cleanup

The driver switches SIGINT to ignored after the first cancellation, sends group TERM, waits the wrapper, restores the prior handler, and returns 130.

This preserves the first signal result but does not bound cleanup.

### C — bounded wait and survivor diagnostic, no escalation

The driver ignores later SIGINT, waits the wrapper and group for a short deterministic interval, records live survivor PIDs, and returns 130 without sending KILL.

This bounds the driver and makes the leak visible, but it deliberately does not establish quiescence.

### D — bounded TERM grace then group KILL

The driver ignores later SIGINT, sends group TERM, waits a grace interval for wrapper/group settlement, sends KILL to the still-owned group when necessary, waits again, and returns 130.

This is an executable policy candidate only. The synthetic result does not authorize its use in product source.

## Executed local discriminator

The focused module passed nine tests locally under real Linux signals and `/proc` accounting.

| Case | Driver result | Group after driver | Later work | Interpretation |
| --- | ---: | --- | --- | --- |
| A, wrapper exits, descendant resists TERM | 130 | descendant live and reparented to PID 1 | possible after release | leader wait is not group quiescence |
| A, wrapper holds, second SIGINT | `-SIGINT` with `KeyboardInterrupt` traceback | wrapper and descendant live | absent until release | later signal interrupts first cleanup |
| B, wrapper holds, second SIGINT | driver remains blocked until release, then 130 | clean only after cooperative release | yes | first-signal retention alone can wait forever |
| C, wrapper holds, second SIGINT | 130 after bounded wait | wrapper and descendant live; survivor PIDs recorded | possible after release | bounded diagnosis is not cleanup |
| D, wrapper holds, second SIGINT | 130 | no live in-group process | no | synthetic full contract passes |
| D, wrapper exits, descendant resists TERM | 130 | no live in-group process | no | group drain must continue after leader settlement |
| ordinary unsignaled control | 0 | clean | expected work completes | cancellation policy does not own ordinary result |
| escaped descendant | 130 | escaped group remains live and receives no TERM | possible after release | process-group ownership does not cross `setsid()` |

## What made policies lose

### Current policy loses the stronger quiescence claim

When the wrapper exits after TERM, `proc.wait()` returns even though the descendant remains alive in the original group. The driver returns 130 while real work survives.

### First-signal retention alone loses boundedness

Ignoring the second SIGINT prevents cleanup interruption, but a TERM-resistant wrapper keeps the driver waiting indefinitely. The operator loses the only remaining interrupt path.

### Bounded diagnostics alone lose cleanup

A timeout plus survivor report is operationally honest, but the group remains live and can perform later work. It is a diagnostic policy, not a cleanup policy.

### Escalation passes the synthetic matrix but remains unselected

TERM-to-KILL is the only compared policy that preserves 130, survives a second SIGINT, drains both wrapper-holds and wrapper-exits topologies, and suppresses later work. It also introduces material policy questions:

- grace-period value and configurability;
- diagnostic content before KILL;
- compatibility with backend-owned graceful cleanup;
- whether KILL is acceptable for privileged or stateful work;
- group/session escape;
- group identity and PID-reuse safety;
- portability beyond Linux `/proc` evidence.

No real mmdebstrap backend has yet been shown to require escalation. Synthetic success is not proportionality evidence.

## Stable conclusions

1. Group-wide TERM delivery, wrapper settlement, group quiescence, and first-signal retention are separate contracts.
2. Waiting only the immediate wrapper cannot prove descendant quiescence.
3. A second SIGINT currently interrupts cleanup and leaves the owned group alive.
4. Ignoring later SIGINT is safe only when cleanup is independently bounded.
5. A bounded no-escalation policy must report that work remains; it cannot claim cleanup.
6. TERM-to-KILL needs explicit product authority and real compatibility evidence.
7. A descendant that calls `setsid()` remains outside every group-local policy compared here.

## Current selection

Retain PR #313's narrow, green claim for tested TERM-responsive topologies.

Do **not** select B alone. Do **not** describe C as complete cleanup. Keep D as the only synthetic full-contract candidate, blocked on proportionality and real-backend evidence.

## Next discriminator

Before proposing product escalation, inspect or execute one real backend that can plausibly defer/ignore TERM or outlive its wrapper. If none exists, stop with the narrowed PR #313 contract and retain this matrix as a reopening test. If one exists, measure a bounded grace interval and the state lost by KILL before selecting D.

Internal Linux Fieldwork evidence only. External contact authorized: `false`.