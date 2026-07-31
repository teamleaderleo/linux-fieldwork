# Completed guest failure versus cleanup-time signal

State: `comparative-evaluation-active`

Tracking: issue #297 and comparison branch `comparison/run-qemu-guest-before-cleanup-signal`.

## TL;DR

The cleanup-time signal repair in PR #282 correctly prevents cancellation from disappearing after guest success. Its current precedence also replaces an already-completed guest failure with a later signal received during host cleanup.

Exact source ordering shows that the guest test result is durable before host EXIT cleanup begins:

1. the guest worker executes `test.sh` and captures its status;
2. it writes that status to `/mnt/exitstatus.txt`;
3. it unmounts `/mnt`;
4. it powers off;
5. only after `debvm-run` returns does the host wrapper enter ordinary EXIT cleanup.

The comparison therefore retains the signal-capture mechanism but moves its final status below the completed guest result:

```text
captured host failure
> completed guest failure
> first cleanup-time signal
> first cleanup failure
> success
```

## Explain like I'm five

The guest finishes its test, writes “failed” on the shared card, closes the shared folder, and turns off. While the host is putting away its temporary log, someone presses stop.

The stop still matters if the card says “success.” It should not erase a failure already written before cleanup began.

## Exact source evidence

The generated guest worker in imported `make_mirror.sh` contains:

```sh
... || ret=$?
echo $ret > /mnt/exitstatus.txt
...
umount /mnt
systemctl poweroff
```

The imported host wrapper contains:

```sh
"$@" ... || ret=$?
if [ "$ret" -ne 0 ]; then
  exit $ret
fi
```

Ordinary EXIT cleanup follows the successful command return. A nonzero guest result has therefore completed and been published before a cleanup-time INT or TERM can be recorded.

## Compared policies

PR #282 policy:

```text
captured host failure > cleanup-time signal > guest failure > cleanup failure > success
```

Event-order variant:

```text
captured host failure > completed guest failure > cleanup-time signal > cleanup failure > success
```

Both policies:

- report INT/TERM after guest success;
- retain the first signal during ordinary cleanup;
- ignore later handled INT/TERM once a signal has been retained;
- finish bounded cleanup;
- preserve host failure over later events.

The discriminator is guest failure that is already durable before TERM arrives during cleanup.

## Patch 4

`0004-preserve-completed-guest-before-cleanup-signal.patch` changes only final precedence inside `finish()`.

It removes the early conversion of `rv` into `cleanup_signal_status` and selects results in this order:

1. captured host status;
2. guest status;
3. recorded cleanup-time signal;
4. cleanup status.

Signal capture, first-signal retention, trap state, cleanup actions, and source ownership are unchanged.

## Executable comparison

`tests/test_run_qemu_guest_before_cleanup_signal.py` retains the current policy as a negative control and covers:

- current guest failure plus cleanup-time TERM returns 143;
- event-order guest nonzero plus TERM returns 1;
- malformed and missing completed guest status plus TERM return 1;
- guest success plus INT/TERM returns 130/143;
- INT→TERM and TERM→INT preserve the first signal after guest success;
- host failure 42 remains ahead of guest failure and TERM;
- cleanup-time signal remains ahead of cleanup failure after guest success;
- signaled cleanup completes and the candidate reruns cleanly;
- all four patches apply with zero fuzz;
- complete composed source passes `/bin/sh -n`;
- source-shape assertions require host, guest, signal, cleanup order.

## Expected losing result

The current PR #282 policy is expected to pass its own table while failing event-order review:

```text
guest result durable: failure 1
later cleanup-time signal: TERM
current final status: 143
selected final status: 1
```

This is not an argument to ignore cancellation after successful work. It narrows cancellation precedence to the case where no earlier authoritative failure exists.

## Evidence boundary

The comparison uses exact retained patches, imported source text, real `/bin/sh`, PID-targeted signals, deterministic cleanup barriers, disposable files, and immediate rerun.

It does not run QEMU, debvm, a guest image, network traffic, package installation, root operations, process-group delivery, HUP/QUIT, escalation, or unbounded cleanup.

The event-order conclusion depends on the guest result write being durable and complete before poweroff and host command return. If that source contract changes, re-evaluate the precedence table.

## Next transition

Run exact-head Linux Fieldwork CI and complete the four-file comparison review. If the event-order matrix is green, update the canonical cleanup-time signal mechanism before composing the final #270 successor. Do not land the current `signal > guest` policy merely because its repaired harness turns green.

Internal work only. External contact authorized: `false`.