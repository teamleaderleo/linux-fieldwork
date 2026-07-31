# Fallback install ownership result

Date: 2026-07-31

Tracking: issue #263 and PR #264.

## TL;DR

The `apt-get install ... || apt-get install fallback ...` chain can preserve its existing result policy while each attempt runs as an explicitly owned child group.

A seven-case real-`/bin/sh` matrix proves:

- first-attempt success omits fallback;
- ordinary first-attempt failure starts fallback;
- fallback success returns success;
- fallback failure is authoritative;
- ordinary failure beats cleanup failure;
- cleanup failure after otherwise successful work remains authoritative;
- TERM during the first attempt stops it, returns 143, omits fallback, and reruns cleanly.

The matrix also finds and rejects one tempting helper design: toggling `set -e` inside `run_child()` can make the shell exit from the failed fallback before the caller records its status.

This removes the fallback chain as a technical blocker, while increasing the demonstrated size of a complete prompt-cancellation implementation. The canonical investigation therefore retains this result but stops without a source patch.

## Explain like I'm five

The worker tries the normal install command. Only when that command fails normally should it try the backup command.

A stop signal is different from “the normal command failed.” A stop must end the current command and must not start the backup command.

The helper also must not secretly change the shell's “quit on errors” switch while the caller is deciding whether to use the backup.

## Why care

The fallback chain is one of the source grammar shapes that prevents a single generic asynchronous wrapper from being accepted without proof. A cancellation repair must keep ordinary fallback behavior while separating cancellation from an ordinary nonzero status.

## Exact regression

`tests/test_make_mirror_fallback_child_ownership.py`

Local command:

```text
python3 tests/test_make_mirror_fallback_child_ownership.py -v
```

Result: 7/7 tests passed.

The model launches each attempt under:

```sh
setsid /bin/sh attempt.sh &
ACTIVE_PID=$!
```

The worker stores the active group leader, waits explicitly, and signals the negative group ID during INT, QUIT, or TERM cleanup.

## Ordinary result matrix

| First attempt | Fallback | Final result | Observed |
| --- | --- | --- | --- |
| 0 | omitted | 0 | pass |
| 5 | 0 | 0 | pass |
| 5 | 7 | 7 | pass |

The second attempt runs only after an ordinary first-attempt nonzero status. When it runs, its status remains authoritative.

## Cleanup precedence

Two controls retain the current lifecycle policy:

- fallback status 7 plus cleanup status 74 returns 7;
- successful first attempt plus cleanup status 74 returns 74.

Cleanup is therefore secondary to an existing ordinary failure and authoritative only when the main operation otherwise succeeded.

## Cancellation result

The first attempt records its PID and remains held. TERM is sent only to the worker.

Observed:

- worker returns 143;
- the held attempt disappears;
- fallback is never called;
- no ordinary result marker is published;
- cleanup executes once even when configured to fail 74;
- an immediate fresh run succeeds and omits its fallback.

Cancellation is therefore distinct from the ordinary nonzero value that authorizes fallback.

## Rejected helper mutation

The first helper prototype used:

```sh
set +e
wait "$ACTIVE_PID"
child_status=$?
set -e
return "$child_status"
```

Inside the second half of an `||` chain, the restored errexit state caused the shell to exit on `return 7` before the caller wrote the final result marker.

The retained model instead uses:

```sh
child_status=0
wait "$ACTIVE_PID" || child_status=$?
return "$child_status"
```

This captures wait status without changing the caller's errexit mode.

## Design consequence

Worker-local simple-command ownership is technically viable, but the helper contract must state:

- never change the caller's `set -e` state;
- preserve ordinary status exactly;
- clear active ownership after wait;
- stop and wait the complete owned group on signal;
- let signal cleanup exit directly so fallback cannot start;
- keep cleanup failure secondary to a signal or ordinary failure;
- support an immediate clean rerun.

A complete source repair would still need this helper to compose with parent pipeline-worker ownership and the separate output-capture primitive. That combined mechanism is not retained because its compatibility cost is disproportionate without measured harmful latency.

## Evidence boundary

The test uses real shells, sessions, process groups, signals, waits, files, and cleanup. It does not run APT, exercise actual apt descendants, close launch-registration windows, test competing signals, or compose the helper with the parent pipeline-worker and output-capture primitives.

## Reopening condition

Use this result if the canonical investigation reopens after measured harmful cancellation latency or an explicit decision to accept the required process-group dependencies. Do not independently turn this model into a source patch.

## Authority

Internal Linux Fieldwork research only. No external contact is included or authorized.
