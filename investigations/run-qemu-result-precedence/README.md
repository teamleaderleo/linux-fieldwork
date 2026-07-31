# run_qemu result, signal, and cleanup precedence

State: `delivery-gate-ready — composed current-main carrier`

Tracking: Linux Fieldwork issues #269 and #297.

## TL;DR

`run_qemu.sh` originally used one cleanup function for `EXIT`, `INT`, and `TERM`. That shape could:

- replace a specific host or timeout failure with generic guest status 1;
- report INT/TERM as guest-dependent 0 or 1;
- run cleanup twice through the still-installed EXIT trap;
- let a second handled signal replace the first signal and interrupt cleanup;
- ignore the first signal that arrives during ordinary EXIT cleanup;
- replace an already-completed guest failure with a later cleanup-time signal.

The composed four-patch carrier separates ordinary and explicit-signal cleanup, retains the first relevant result at each lifecycle stage, completes bounded cleanup once, and selects:

```text
captured host failure
> completed guest failure
> first cleanup-time signal
> first cleanup failure
> success
```

A signal handler that already selected INT 130 or TERM 143 remains authoritative over subordinate and cleanup failures. Later handled INT/TERM are ignored while bounded cleanup finishes.

## Explain like I'm five

The wrapper can receive several reports while it finishes: the machine runner failed, the guest test failed, somebody pressed stop, or cleanup failed.

The repair records when each report became final instead of letting the last line of cleanup overwrite everything else. It also makes sure that putting tools away happens once and cannot be interrupted by a second press of the same stop buttons.

## Canonical source boundary

Imported source:

- `upstream/mmdebstrap/run_qemu.sh`;
- blob `426aeeb854173569b24e64d6eb85019f45bdf0b6`.

Clean current-main branch:

- `fix/run-qemu-result-precedence-composed-current`.

Historical mechanism and comparison carriers:

- PR #270 — primary result, once-only cleanup, first cleanup failure, and first handled signal;
- PR #282 — first INT/TERM during ordinary EXIT cleanup;
- PR #304 — completed guest result before later cleanup-time signal.

Those heads remain evidence. This branch is the only composed landing surface.

## Patch sequence

### Patch 1 — preserve primary result

`0001-preserve-primary-result.patch`:

- introduces `finish STATUS`;
- reads the guest result without letting `set -e` replace an existing host result;
- retains the first cleanup failure across `rm` and `rmdir`;
- separates ordinary EXIT from explicit INT 130 and TERM 143 cleanup;
- clears EXIT before final exit so cleanup runs once.

### Patch 2 — retain the first handled signal through cleanup

`0002-retain-first-signal-through-cleanup.patch` changes explicit-signal and ordinary handlers from restoring default INT/TERM behavior to ignoring already-handled INT/TERM while bounded cleanup runs.

This prevents a second signal from replacing the first result or leaving cleanup half-complete.

### Patch 3 — retain the first signal during ordinary EXIT cleanup

`0003-retain-signal-during-exit-cleanup.patch` adds:

- `cleanup_signal_status=0`;
- a first-writer `record_cleanup_signal()`;
- INT/TERM recorder traps only for ordinary EXIT cleanup;
- a final transition to ignored INT/TERM before result selection.

This prevents a first signal during cleanup after successful work from disappearing.

### Patch 4 — preserve completed guest failure before a later cleanup signal

`0004-preserve-completed-guest-before-cleanup-signal.patch` changes only final precedence inside `finish()`.

Exact guest/host source order is:

1. guest test completes and its status is captured;
2. guest writes `/mnt/exitstatus.txt`;
3. guest unmounts `/mnt`;
4. guest powers off;
5. `debvm-run` returns;
6. host ordinary EXIT cleanup begins.

A guest failure is therefore already authoritative before a later cleanup-time signal. Patch 4 selects host, guest, cleanup-time signal, then cleanup.

## Final result contract

### Host or explicit signal failure

A captured nonzero host status, timeout, or explicit INT 130 / TERM 143 remains authoritative over guest and cleanup results.

### Completed guest result

When the host path succeeded, guest nonzero, missing, unreadable, or malformed status becomes generic 1 before any later signal received during host cleanup.

### Cleanup-time signal

When host and completed guest results are successful, the first INT/TERM during ordinary EXIT cleanup becomes 130/143. A later handled INT/TERM cannot replace it.

### Cleanup failure

When host, guest, and cleanup-time signal all indicate success, the first cleanup failure becomes final. Later cleanup actions still run but cannot replace it.

### Success

Only complete success across host, guest, signal, and cleanup returns 0.

## Executable evidence fence

Primary tests:

- `tests/test_run_qemu_result_precedence.py`;
- `tests/test_run_qemu_cleanup_failure_precedence.py`;
- `tests/test_run_qemu_first_signal_cleanup.py`;
- `tests/test_run_qemu_exit_cleanup_signal.py`;
- `tests/test_run_qemu_guest_before_cleanup_signal.py`.

The matrices retain losing controls rather than only candidate success:

- imported host 124 plus guest failure becomes 1;
- imported INT/TERM can become guest-dependent 0/1 and cleanup runs twice;
- the first candidate can lose TERM 143 to later INT and leave cleanup partial;
- the two-patch predecessor can ignore TERM during ordinary EXIT cleanup and return 0;
- the three-patch policy can replace an already-completed guest failure with later TERM 143.

The final candidate proves:

- host 0, 42, 124, and signal-like status;
- guest success, nonzero, malformed, unreadable/missing status;
- INT 130 and TERM 143;
- first-signal stability through cleanup;
- signal capture during ordinary cleanup;
- completed guest failure before later cleanup signal;
- first cleanup failure over later cleanup failure;
- host over guest, signal, and cleanup;
- guest over later cleanup signal and cleanup;
- cleanup-time signal over cleanup failure after successful work;
- once-only complete cleanup;
- no post-signal later work;
- immediate clean rerun;
- zero-fuzz application of patches 1–4;
- complete `/bin/sh -n`;
- nonduplicating unittest discovery.

## Historical receipts

Green exact-head evidence retained from the component carriers:

- PR #270 head `76ffad2ea25f03272c788d37de6232b6a0b287d7`, CI `30623610733` / 828;
- PR #282 head `e973546c350682e1175fa68fbf705c83487c2cf9`, CI `30624661338` / 844;
- PR #304 head `0d5864c53badee91b403676ecc55e7aef5c38679`, CI `30625359304` / 854.

Those runs validate their exact generations. The composed branch still requires its own complete exact-head gate.

## Cleanup and safety

Dynamic tests use disposable directories, short-lived `/bin/sh` processes, PID-targeted INT/TERM, deterministic file barriers, and explicit waits. No QEMU, debvm, guest image, network, package, mount, root, or public target is used.

Cleanup failures are captured explicitly rather than allowed to trigger implicit `set -e` replacement.

## Evidence boundary

Established:

- shell trap timing;
- result event ordering;
- guest-status handling;
- once-only cleanup;
- first-cleanup-failure retention;
- first handled signal stability;
- first signal during ordinary cleanup;
- complete tested cleanup and rerun.

Not established:

- real QEMU/debvm integration;
- process-group delivery and foreground-child cancellation;
- HUP or QUIT policy;
- TERM-to-KILL escalation;
- unbounded cleanup;
- background log follower behavior beyond its existing parent-death design;
- unusual filesystem failures;
- current public upstream source.

## Next transition

Run exact-head Linux Fieldwork CI on the composed current-main branch and complete the full seventeen-file review. If unchanged and green, mark the carrier review-ready and retire PRs #270, #282, and #304 as historical component evidence without merging them independently.

Internal Linux Fieldwork work only. External contact authorized: `false`.