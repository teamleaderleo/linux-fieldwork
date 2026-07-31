# Handled signals must remain stable through cleanup

## In simple words

Once a wrapper accepts a signal and chooses its final status, cleanup must not reopen a window where a later signal can replace that result or stop cleanup halfway.

## The trap distinction

Clearing EXIT before a handler calls `exit` prevents cleanup from running twice. INT and TERM need a different decision.

This shape restores default terminating behavior too early:

```sh
on_term() {
  trap - EXIT INT TERM
  finish 143
}
```

A second INT or TERM during `finish` can terminate the shell and replace the first result.

For a bounded cleanup path where the first handled INT/TERM should win:

```sh
on_term() {
  trap '' INT TERM
  trap - EXIT
  finish 143
}
```

Ignore the already-handled signals first, then clear EXIT. The order avoids an intermediate default-signal window.

This is not a universal signal policy. HUP, QUIT, escalation, process groups, and long or blocking cleanup need their own explicit contracts.

## Why care

A later signal can otherwise:

- replace TERM 143 with INT 130 or direct signal termination;
- interrupt cleanup after only one action;
- leave temporary state for the next run;
- make a green single-signal regression miss the real lifecycle race.

## Regression shape

Use a deterministic barrier inside the first cleanup action:

1. send the first signal;
2. wait until cleanup publishes a ready marker;
3. send a competing handled signal;
4. release cleanup only when the process remains alive;
5. assert the first result, complete cleanup log, removed temporary state, and absence of later work.

Test the predecessor and candidate under the same barrier. A sleep-only race is weaker because it may send the second signal before or after the relevant window.

## Related record

- `investigations/run-qemu-result-precedence/FIRST_SIGNAL_CLEANUP.md`
- Linux Fieldwork PR #270
