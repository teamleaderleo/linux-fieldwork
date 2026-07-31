# Final SIGINT publication and unrelated-process containment

State: `focused comparison prepared — exact-head execution pending`

## TL;DR

The TERM-resistant comparison in PR #347 correctly shows that group delivery, wrapper exit, group quiescence, and result stability are separate contracts. Its non-current policies ignore later SIGINT while cleanup runs, but restore the previous SIGINT handler before publishing status 130 and exiting.

That creates one final signal window: a third SIGINT can replace the first result after backend cleanup is complete.

This focused successor retains a losing restore-before-publication control and compares it with keeping SIGINT ignored through final status publication and process exit. It also proves that the bounded escalation topology drains the owned backend group without touching an unrelated process in another session.

## Explain like I'm five

The cleanup worker ignores extra stop-button presses while putting the tools away, then turns the buttons back on just before writing “stopped.” One last button press can still erase the result.

The safer short-lived policy keeps the buttons ignored until the result is written and the worker exits. A separate bystander must remain untouched while the owned crew is stopped.

## Why care

First-signal retention is incomplete if the handler is restored before final publication. A result can remain stable throughout expensive cleanup and still be replaced in the last few instructions.

Escalation also needs a containment control. Draining the intended process group is not enough if an unrelated process can be signaled accidentally.

## Predecessor source boundary

PR #347's synthetic driver does:

```python
finally:
    signal.signal(signal.SIGINT, previous_sigint)

(root / "driver.done").write_text("130\n", encoding="ascii")
raise SystemExit(130)
```

The restore occurs before the durable marker and final exit. The nine-test comparison sends one later SIGINT during cleanup, not another signal after the restore.

This is a comparison-fixture boundary, not yet a production `coverage.py` patch.

## Deterministic finalization control

`tests/test_mmdebstrap_coverage_final_sigint_containment.py` uses a small finalizer with an explicit `handler-ready` marker written **after** the selected signal disposition is installed.

Two variants share the same initial state:

1. install `SIG_IGN`;
2. write `finalizing`;
3. optionally restore the previous handler;
4. write `handler-ready`;
5. wait at `final-release`;
6. write `driver.done=130`;
7. exit 130.

The predecessor-shaped variant restores the handler before `handler-ready`. A SIGINT sent after that marker must raise `KeyboardInterrupt` and prevent final publication.

The retained variant leaves SIGINT ignored through exit. A SIGINT after `handler-ready` must leave the process alive; release then produces status 130 and the durable marker.

The marker ordering removes the timing ambiguity from the first draft of this fixture, which wrote a general finalization marker before changing the signal disposition.

## Unrelated-process containment

The focused test reuses PR #347's real Linux escalation topology:

- driver;
- wrapper in an owned backend process group;
- TERM-resistant descendant in the same group;
- separate unrelated sleeper in another session/process group.

It sends the first parent-only SIGINT, then a later SIGINT while cleanup runs. Required results:

- wrapper and descendant record TERM;
- bounded escalation occurs;
- the backend group has no live members;
- wrapper and descendant later-work markers are absent;
- driver returns 130;
- unrelated process remains alive.

The unrelated process is fixture-owned and terminated during test cleanup.

## Cross-context review receipt

- **cleanup versus final publication** — separate barrier and losing control;
- **second versus third SIGINT** — cleanup-time and finalization-time signals distinguished;
- **group quiescence versus result stability** — both required;
- **owned group versus unrelated process** — explicit session-separated sentinel;
- **fixture timing versus signal disposition** — marker written only after handler state changes;
- **rerun/cleanup authority** — all processes are fixture-owned and registered for teardown.

## Result boundary

A green focused gate establishes two synthetic conclusions:

1. restoring the default SIGINT handler before publication leaves a final result-replacement window;
2. keeping SIGINT ignored through immediate exit closes that window in the reduced model, while the selected escalation topology preserves an unrelated process.

It does not select a production escalation timeout, prove PGID reuse safety, cover descendants that call `setsid()`, or execute real mmdebstrap backends. Those remain owned by issue #341 and PR #347's stop rule.

## Disposition

`EXECUTE FOCUSED FINALIZATION AND CONTAINMENT MATRIX`.

If green, compose this evidence into PR #347 and remove “full matrix” ambiguity. Product selection still requires a real backend discriminator or an explicit decision that bounded escalation is proportionate.

Internal Linux Fieldwork work only. No external contact is authorized or included.

Refs #341, PR #347, and PR #313.
