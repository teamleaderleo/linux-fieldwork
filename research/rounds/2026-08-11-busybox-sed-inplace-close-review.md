# 2026-08-11 BusyBox sed in-place close review

## TL;DR

A source reconnaissance pass on current BusyBox master found a bounded follow-up in `sed -i`: the in-place path checks `fflush()`/`ferror()`, ignores the return from `fclose()`, then renames the temporary output over the input. The detailed record is in [`../../investigations/busybox-sed-inplace-close-failure/README.md`](../../investigations/busybox-sed-inplace-close-failure/README.md).

This is source evidence only. The next step is a disposable close-only fault-injection probe that keeps the explicit flush successful while making final close report failure.

## Selection reason

This target combines several useful Linux Fieldwork lenses:

- temporary-file publication followed by rename;
- delayed write/finalization error reporting;
- different decisions for flush-visible and close-only failures;
- a clean same-project comparison in `dos2unix`;
- a small deterministic test boundary.

## Exact source

- Project: BusyBox
- Official source mirror: `https://github.com/vda-linux/busybox_mirror`
- Reviewed revision: `7473045ad3504db9b421427a452fd9b146346306`
- Primary file: `editors/sed.c`
- Comparison file: `coreutils/dos2unix.c`
- Existing tests: `testsuite/sed.tests`
- Current release observed during the pass: 1.38.0, 2026-05-13

## First distinguishing observation

The current `sed -i` sequence is:

```text
process output -> fflush -> ferror check -> unchecked fclose -> rename temp over input
```

The 2024 BusyBox fix added the flush/error check, so ordinary buffered ENOSPC-style failures can stop before rename. A failure reported only by the final close has no equivalent branch.

## Strong internal comparison

At the same source revision, `dos2unix` performs an in-place conversion through a temporary file but checks `fclose(out)`. If close fails, it unlinks the temporary file and exits before rename.

That comparison makes the `sed` question especially compact: both applets use temporary output plus final replacement, but only one treats final close as part of the publication gate.

## Existing-test boundary

`testsuite/sed.tests` contains normal `-i` behavior, including newline/EOF cases. This pass found no close-failure injection or assertion that an original file survives a failed finalization.

## Next action

Run a local synthetic close-only failure against the exact reviewed head. Keep the explicit `fflush()` successful, force only the temporary output's `fclose()` to report an I/O-style error, and record exit status, stderr, final input content, temporary path, optional backup, and immediate clean rerun.

If replacement still occurs, prepare a minimal local candidate that checks `fclose()` and reuses the existing `cleanup_outname` fatal cleanup path. Keep any candidate internal until upstream contact is separately authorized.

## External-contact state

Not authorized; none performed.
