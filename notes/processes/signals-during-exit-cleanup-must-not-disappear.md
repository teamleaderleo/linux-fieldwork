# Signals during EXIT cleanup must not disappear

## In simple words

A wrapper can enter cleanup for two different reasons:

1. ordinary work finished and the EXIT trap started cleanup;
2. a signal handler already selected a signal-derived result and started cleanup.

Those paths need different signal treatment.

## Stable rule

After a signal handler has already selected INT 130 or TERM 143, later handled INT/TERM may be ignored during bounded cleanup so they cannot replace the first result or interrupt cleanup.

During ordinary EXIT cleanup, no signal result has been selected yet. Ignoring INT/TERM at entry can turn cancellation into success. Instead:

- retain the first cleanup-time signal;
- continue bounded cleanup;
- keep an already-captured host failure authoritative;
- otherwise make the retained signal outrank guest and cleanup outcomes;
- disable further handled signals before final result selection.

## Distinguish the handlers

This is appropriate for explicit signal cleanup:

```sh
on_term() {
  trap '' INT TERM
  trap - EXIT
  finish 143
}
```

The first signal is already represented by 143.

The same shape is incomplete for ordinary EXIT:

```sh
on_exit() {
  status=$?
  trap '' INT TERM
  trap - EXIT
  finish "$status"
}
```

If `status` is zero and TERM arrives while cleanup runs, TERM is ignored and the wrapper can return success.

A bounded ordinary-cleanup shape can record the first signal instead:

```sh
cleanup_signal_status=0

record_cleanup_signal() {
  if [ "$cleanup_signal_status" -eq 0 ]; then
    cleanup_signal_status=$1
  fi
}

on_exit() {
  status=$?
  trap 'record_cleanup_signal 130' INT
  trap 'record_cleanup_signal 143' TERM
  trap - EXIT
  finish "$status"
}
```

After cleanup, switch INT/TERM to ignored before reading the recorded status and exiting. That closes the last window where a newly accepted signal could be recorded after result selection.

## Precedence

A useful first-event policy is:

```text
captured host failure > first cleanup-time signal > subordinate failure > first cleanup failure > success
```

The captured host status exists before ordinary EXIT cleanup begins, so it remains authoritative. If it is zero, the first signal accepted during cleanup becomes the primary failure.

## Regression shape

Use deterministic barriers rather than sleeps alone:

1. let ordinary work call `exit 0`;
2. block inside the first cleanup action and publish a ready marker;
3. send INT or TERM;
4. optionally send the competing handled signal;
5. release cleanup;
6. assert final status, complete cleanup, removed temporary state, and immediate rerun.

Retain the previous candidate as a negative control. It should demonstrate false success when it ignores the first cleanup-time signal.

Also exercise:

- host failure before cleanup plus later signal;
- subordinate failure plus later signal;
- cleanup failure plus later signal;
- INT then TERM and TERM then INT;
- syntax and exact patch composition.

## Boundary

This rule assumes cleanup is bounded and safe to finish. Long-running or potentially stuck cleanup needs a separate escalation policy. HUP, QUIT, process groups, and foreground-child delivery are independent contracts.

## Related record

- `investigations/run-qemu-result-precedence/EXIT_CLEANUP_SIGNAL.md`
- Linux Fieldwork PR #270
