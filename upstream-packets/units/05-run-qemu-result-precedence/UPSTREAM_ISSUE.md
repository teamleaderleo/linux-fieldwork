# DRAFT — DO NOT SEND

External contact authorized: `false`

## Proposed title

`run_qemu.sh` can replace the primary failure during cleanup

## Proposed issue body

`run_qemu.sh` currently uses one cleanup function for `EXIT`, `INT`, and `TERM`. The handler captures `$?`, performs cleanup, reads the guest result, and may replace the captured status with generic failure 1.

This can produce several misleading results:

- a QEMU, timeout, or host failure can become guest failure 1;
- INT or TERM can return a guest-dependent status instead of 130 or 143;
- calling `exit` from the signal handler can re-enter cleanup through the installed EXIT trap;
- a second signal can replace the first signal result or interrupt cleanup;
- the first signal during ordinary EXIT cleanup can disappear;
- a later cleanup-time signal can replace a guest failure that had already completed.

The proposed behavior preserves outcomes in execution order:

```text
captured host failure
> completed guest or protocol failure
> first INT/TERM received during ordinary cleanup
> first cleanup failure
> success
```

The candidate separates ordinary EXIT and explicit signal handlers, clears EXIT before finalization, retains the first signal during ordinary cleanup, ignores later handled INT/TERM during bounded cleanup, records the first cleanup failure while continuing later cleanup actions, and selects the earliest authoritative result.

A reduced real-`/bin/sh` regression matrix covers host, guest, signal, and cleanup combinations, competing signals, cleanup completion, and immediate rerun. A current upstream base identity and upstream-native test command should be added before this draft is used.

## Publication checklist

- [ ] explicit authorization recorded;
- [ ] current Salsa `master` SHA recorded;
- [ ] equivalent open issue or merge request search completed;
- [ ] exact current source comparison completed;
- [ ] rebased candidate and test receipts linked;
- [ ] maintainer-preferred issue channel confirmed;
- [ ] private Linux Fieldwork-only identifiers removed or translated.
