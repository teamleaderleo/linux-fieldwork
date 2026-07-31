# Result precedence must survive exit cleanup

## In simple words

A wrapper can learn several bad outcomes while it exits: the main command failed, a guest reported failure, a signal cancelled the wrapper, or cleanup failed. Cleanup must not replace a more important result just because it runs last.

## Stable rule

Capture the primary result before cleanup and make precedence explicit:

1. an existing command or first handled signal failure wins;
2. otherwise a subordinate result channel may report failure;
3. otherwise the first cleanup failure may become final;
4. otherwise return success.

Do not perform fallible result reads in an `EXIT` trap under `set -e` without containing their status. A missing or unreadable result file can otherwise become a new shell failure and overwrite the primary result.

Within cleanup, do not let the last cleanup operation replace the first failed cleanup operation. Record a cleanup status only while no earlier cleanup failure exists.

## Separate signals from ordinary EXIT

One trap body for `EXIT`, `INT`, and `TERM` is unsafe when it derives its result from `$?`:

```sh
trap cleanup INT TERM EXIT
```

A shell can defer INT or TERM while waiting for a foreground command. When the trap finally runs, `$?` may describe the completed command rather than the signal. The handler can then report success or a subordinate failure instead of cancellation.

Use explicit signal statuses. Clear EXIT before the handler calls `exit`, but do not restore default INT/TERM behavior while bounded cleanup is still running:

```sh
prepare_finish() {
  trap '' INT TERM
  trap - EXIT
}

on_exit() {
  status=$?
  prepare_finish
  finish "$status"
}

on_term() {
  prepare_finish
  finish 143
}
```

Ignoring already-handled INT/TERM keeps the first result stable through cleanup. Clearing EXIT prevents the handler's final `exit` from invoking cleanup a second time. Install the ignore rules before clearing EXIT so there is no intermediate default-signal window.

This is not a universal signal policy. HUP, QUIT, escalation, process-group delivery, foreground-child cancellation, and long or blocking cleanup require their own explicit decisions.

## Subordinate result channels

Guest status files, child status pipes, completion markers, and similar channels are subordinate to a primary host or first handled signal failure unless the contract says otherwise.

A useful pattern is:

```text
host or first handled signal nonzero > subordinate failure > first cleanup failure > success
```

The subordinate channel may intentionally normalize several conditions to a generic failure, but it should do so only when no more specific primary failure already exists.

## Cleanup precedence shape

For sequential cleanup actions:

```sh
cleanup_status=0
first_cleanup || {
  status=$?
  [ "$cleanup_status" -ne 0 ] || cleanup_status=$status
}
second_cleanup || {
  status=$?
  [ "$cleanup_status" -ne 0 ] || cleanup_status=$status
}
```

This still attempts later cleanup while retaining the earliest cleanup failure for diagnosis.

## Regression shape

Exercise at least:

- host success plus subordinate success;
- host success plus subordinate failure;
- specific host failure plus subordinate failure;
- signal plus subordinate success and failure;
- a second handled signal delivered after cleanup begins;
- first-signal identity retained through cleanup;
- missing or unreadable subordinate result;
- cleanup failure after success;
- two distinct cleanup failures, requiring the first to win;
- cleanup failure after host or signal failure;
- once-only cleanup;
- complete cleanup after handled cancellation;
- no later marker after handled cancellation;
- discovery that does not duplicate imported test cases.

Use a barrier inside the first cleanup action for the competing-signal case. A sleep-only race may send the second signal outside the relevant window.

## Related records

- `investigations/run-qemu-result-precedence/README.md`
- `investigations/run-qemu-result-precedence/FIRST_SIGNAL_CLEANUP.md`
- `notes/processes/handled-signals-must-remain-stable-through-cleanup.md`
- Linux Fieldwork issue #269
