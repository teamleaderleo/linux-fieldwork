# DRAFT — DO NOT SEND

External contact authorized: `false`

## Proposed title

`run_qemu: preserve host, guest, signal, and cleanup result precedence`

## Proposed merge-request body

### Summary

`run_qemu.sh` now preserves the earliest authoritative failure while completing bounded cleanup once.

```text
captured host failure
> completed guest or protocol failure
> first signal received during ordinary cleanup
> first cleanup failure
> success
```

### Behavior

- ordinary EXIT cleanup captures the existing command status before cleanup;
- explicit INT and TERM select 130 and 143;
- guest status cannot replace an earlier host failure;
- unreadable, missing, malformed, or nonzero completed guest status becomes 1 after host success;
- the first INT or TERM during ordinary cleanup is retained;
- later handled signals cannot replace the first result or interrupt bounded cleanup;
- signal trap actions disable overlapping INT/TERM handling before handler-body commands;
- ordinary cleanup phase is marked in the same assignment-only command that captures `$?`;
- a signal delivered during ordinary-handler entry rejoins the ordinary cleanup path instead of bypassing host/guest precedence;
- the first cleanup failure is retained while later cleanup actions run;
- EXIT is cleared before finalization, so cleanup runs once;
- immediate reruns remain clean.

### Commit sequence

1. **Preserve primary result through cleanup**
   - separate ordinary EXIT and explicit-signal handlers;
   - preserve host, guest, and first cleanup failure;
   - clear EXIT before finalization.

2. **Retain the first handled signal through cleanup**
   - keep later INT/TERM from replacing the selected explicit signal or interrupting cleanup.

3. **Retain signals during ordinary EXIT cleanup**
   - add a first-writer cleanup signal slot and recorder traps.

4. **Preserve completed guest failure before cleanup signal**
   - select host, guest, cleanup-time signal, cleanup failure, success.

5. **Close signal-handler setup windows**
   - disable overlapping signals in trap actions before entering handlers;
   - mark ordinary cleanup with status capture;
   - route an early cleanup signal back into the ordinary first-writer recorder path.

### Tests

Exact controlled candidate:

```text
base: 574048f2a720057b75e56622003932f344dc700a
head: 6efe6945f9f89cff57fe84086ede7bda747c3879
run_qemu.sh blob: 1fc816d6fe982351f6519fd1458329112eebdcfb
SHA-256: 434e7b6b9c32e30b506ea6af121608414c42b668c329e6395e75e19dc09ff276
/bin/sh -n: pass
```

Reduced real-`/bin/sh` lifecycle matrix:

```text
58 passed
0 failed
```

Complete-diff setup-window controls:

```text
four-commit: TERM then INT during explicit handler entry -> 130 (losing)
fifth-commit: same event order -> 143, cleanup complete

four-commit: completed guest 1 then TERM during EXIT handler entry -> 143 (losing)
fifth-commit: same event order -> 1, cleanup complete

fifth-commit: early cleanup TERM, recorder installation, later INT -> 143, cleanup complete
```

The final public test section must add:

- current canonical Salsa base and rebased candidate heads;
- exact execution of the checked-in setup-window regression;
- current QEMU-classified `coverage.py` or `coverage.sh` results;
- cleanup and immediate-rerun result on the exact rebased head;
- any authorized bounded real QEMU/`debvm-run` smoke result.

### Compatibility boundary

The change leaves QEMU command construction, timeout duration, HUP/QUIT handling, process-group delivery, escalation, guest image content, networking, and mount policy unchanged. Ignoring later handled INT/TERM assumes bounded cleanup. Guest precedence assumes guest status is complete before `debvm-run` returns.

## Publication checklist

- [ ] explicit authorization recorded;
- [ ] controlled Salsa fork/branch and current `master` identity recorded;
- [ ] equivalent current issue/branch/merge request search completed;
- [ ] complete rebased diff reviewed;
- [ ] checked-in regression and upstream-native QEMU tests executed;
- [ ] cleanup and immediate rerun repeated on the exact final head;
- [ ] Linux Fieldwork-private references removed or translated into self-contained rationale.
