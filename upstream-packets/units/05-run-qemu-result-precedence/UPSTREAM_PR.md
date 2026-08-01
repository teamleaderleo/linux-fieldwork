# DRAFT — DO NOT SEND

External contact authorized: `false`

## Proposed title

`run_qemu: preserve host, guest, signal, and cleanup result precedence`

## Proposed merge-request body

### Summary

`run_qemu.sh` now preserves the earliest authoritative failure while completing cleanup once.

The final result order is:

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
- the guest result is read without replacing an earlier host failure;
- unreadable, missing, malformed, or nonzero completed guest status becomes generic 1 when the host succeeded;
- the first INT or TERM during ordinary cleanup is retained;
- later handled INT or TERM cannot replace an established signal result or interrupt bounded cleanup;
- the first cleanup failure is retained while later cleanup actions still run;
- EXIT is cleared before finalization, so cleanup runs once;
- a completed guest failure remains ahead of a later cleanup-time signal;
- successful work followed by a cleanup-time signal returns 130 or 143.

### Commit sequence

1. **Preserve the primary result through cleanup**
   - split ordinary EXIT and explicit-signal handlers;
   - preserve host, guest, and first cleanup-failure results;
   - clear EXIT before finalization.

2. **Retain the first handled signal through cleanup**
   - ignore later handled INT and TERM during bounded explicit-signal cleanup;
   - preserve first-signal identity and cleanup completion.

3. **Retain signals received during ordinary EXIT cleanup**
   - record the first INT or TERM during ordinary cleanup;
   - switch handled signals to ignored before final selection.

4. **Keep completed guest failure before a later cleanup signal**
   - select host, guest, cleanup-time signal, then cleanup failure.

### Tests

Current packet extraction proves on the retained imported base:

```text
git apply --check patches/0001-preserve-primary-result.patch
...
git apply --check patches/0004-preserve-completed-guest-before-cleanup-signal.patch
/bin/sh -n run_qemu.sh
```

All checks and applications returned zero. The composed script SHA-256 is:

```text
8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f
```

The full proposed test section must be refreshed from a live current-Salsa candidate before publication. It should include:

- the exact upstream base and candidate commits;
- focused host/guest/signal/cleanup matrix results;
- competing-signal and ordinary-cleanup signal cases;
- cleanup completion and immediate rerun;
- project syntax, lint, and ordinary test targets;
- any authorized real QEMU/`debvm-run` smoke result.

### Scope

This change leaves QEMU command construction, timeout duration, HUP/QUIT behavior, process-group delivery, signal escalation, guest image behavior, networking, and mount policy unchanged.

## Publication checklist

- [ ] explicit authorization recorded;
- [ ] controlled Salsa fork and branch recorded;
- [ ] current `master` base commit recorded;
- [ ] source and test delta reviewed on the exact candidate head;
- [ ] current equivalent upstream work search completed;
- [ ] all test commands and results refreshed;
- [ ] cleanup and immediate rerun repeated after a clean checkout;
- [ ] Linux Fieldwork-private references removed or converted to self-contained rationale.
