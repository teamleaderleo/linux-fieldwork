# Completed results must not be replaced by later cleanup signals

## In simple words

A signal received during cleanup is important when the main operation succeeded. It is not earlier than a failure that the completed operation already reported and made durable.

Result precedence should follow ownership and event order, not merely the order in which cleanup code happens to inspect variables.

## Why care

A wrapper may observe several results:

- the host command failed;
- a guest or child completed and reported failure;
- a signal arrived while host cleanup was running;
- cleanup itself failed.

If a later cleanup-time signal replaces an already-completed guest failure, the final status describes cancellation rather than the operation that actually failed first. That can send investigation toward the scheduler or operator instead of the failing test.

Ignoring the cleanup-time signal is also wrong after success. The wrapper must retain it without allowing it to replace an earlier completed failure.

## Preferred order

When the event order is established as:

1. host command result captured;
2. child or guest result durably published;
3. host cleanup begins;
4. signal arrives during cleanup;
5. cleanup result becomes known;

use:

```text
captured host failure
> completed child or guest failure
> first cleanup-time signal
> first cleanup failure
> success
```

This order is not universal. It depends on proving that the child result was complete and durable before cleanup started.

## Review questions

Before assigning precedence, ask:

1. When did each result become final?
2. Which owner produced it?
3. Was it durably published before the next event?
4. Is the later signal cancelling unfinished work, or only interrupting cleanup after work completed?
5. Would changing the final status misclassify the first failure owner?
6. Does cleanup still complete, and can a later signal replace the first retained signal?

## Required controls

A strong matrix should distinguish:

- child success, then cleanup-time INT/TERM;
- child failure, then cleanup-time INT/TERM;
- missing or malformed completed child result, then signal;
- host failure, then signal;
- cleanup failure, then signal after child success;
- first-signal ordering during the same cleanup;
- complete cleanup and immediate rerun.

Retain the losing policy as a negative control. Otherwise a precedence table can encode preference without proving why the selected order matches execution.

## Boundary

Do not apply this rule when the child result is provisional, buffered but not durable, or still able to change. In those cases the signal may genuinely be the first authoritative failure.

The essential rule is:

> Preserve the earliest authoritative completed failure, not the last failure observed by cleanup.