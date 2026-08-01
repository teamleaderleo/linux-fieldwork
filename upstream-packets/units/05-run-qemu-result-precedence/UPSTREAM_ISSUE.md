# DRAFT — DO NOT SEND

External contact authorized: `false`

## Proposed title

`run_qemu.sh` can replace an earlier host, guest, or signal result during cleanup

## Proposed issue body

`run_qemu.sh` combines host execution, guest status publication, signal handling, and cleanup. The original shared `EXIT INT TERM` cleanup handler can replace the result that already owns the failure.

Observed failure classes include:

- host timeout or command failure becoming generic guest failure 1;
- INT or TERM returning a guest-dependent status instead of 130 or 143;
- signal cleanup re-entering through the installed EXIT trap;
- a later signal replacing the first or interrupting cleanup;
- a signal during ordinary cleanup disappearing as success;
- a later cleanup signal replacing a completed guest failure;
- a second signal entering before the explicit handler replaces its traps and replacing first-signal identity;
- a signal entering ordinary EXIT cleanup before recorder traps are installed and bypassing completed guest precedence.

The selected result order is:

```text
captured host failure
> completed guest or protocol failure
> first INT/TERM received during ordinary cleanup
> first cleanup failure
> success
```

The candidate separates ordinary EXIT and explicit signal cleanup, clears EXIT before finalization, retains the first cleanup failure while continuing cleanup, records the first ordinary-cleanup signal, and closes handler-entry windows before overlapping signal handling can re-enter.

Deterministic reduced `/bin/sh` controls include:

```text
host 124 + guest failure: original 1, candidate 124
TERM then INT during explicit handler entry: four-commit candidate 130, repaired candidate 143
completed guest 1 + TERM during EXIT handler entry: four-commit candidate 143, repaired candidate 1
early cleanup TERM + later INT: repaired candidate 143 with cleanup complete
```

The established lifecycle matrix passes 58/58 checks on the repaired source, including cleanup completion and immediate rerun.

Before using this draft, add the exact current Salsa base, equivalent-work search, and current mmdebstrap QEMU-classified project-test results.

## Publication checklist

- [ ] explicit authorization recorded;
- [ ] current canonical Salsa `master` and file blob recorded;
- [ ] equivalent issue, branch, and merge-request search completed;
- [ ] five logical changes rebased on the exact canonical head;
- [ ] upstream-native QEMU tests and cleanup/rerun recorded;
- [ ] checked-in setup-window regression executed in checkout or CI;
- [ ] maintainer-preferred destination confirmed;
- [ ] Linux Fieldwork-only identifiers removed from public text.
