# BusyBox sed in-place publication on close failure

## TL;DR

Source review of current BusyBox master at commit `7473045ad3504db9b421427a452fd9b146346306` found a bounded in-place-edit finalization concern in `editors/sed.c`.

For `sed -i`, BusyBox writes transformed output to a temporary file, calls `fflush()`, checks `ferror()`, then calls `fclose()` without checking its return value. It immediately renames the temporary output over the input file. A close-time I/O failure can therefore be reported by the C/POSIX stream layer without changing the publication decision.

This is a source-level finding. No close-only fault-injection execution has been run yet. The next useful action is a local synthetic probe that makes the final `fclose()` report failure after the preceding `fflush()` succeeds, then observes whether BusyBox still replaces the input.

## Explain like I'm five

`sed -i` edits a copy first and swaps the copy into place at the end. BusyBox checks whether writing the copy failed, which is good. But closing the copy is also allowed to report a late write error. BusyBox currently ignores that final answer and swaps the copy into place anyway.

Another BusyBox applet, `dos2unix`, handles the same temp-file pattern more conservatively: it checks `fclose(out)` and deletes the temporary file on close failure before any rename.

## Why care

A stream close can be the point where delayed write errors become visible. On filesystems or storage paths where the final close reports an error after an earlier flush appeared successful, `sed -i` can replace the known input with output whose finalization was reported unsuccessful.

The strongest current claim is narrow: **BusyBox `sed -i` does not gate replacement on successful `fclose()` completion.** This record does not claim that such close-only failures are common, and it does not yet establish persisted-byte damage in a concrete filesystem fixture.

## Source boundary

- Project: BusyBox
- Official source browser points to: `https://github.com/vda-linux/busybox_mirror`
- Reviewed revision: `7473045ad3504db9b421427a452fd9b146346306`
- Current release observed during this pass: BusyBox 1.38.0, released 2026-05-13
- Primary file: `editors/sed.c`
- Internal comparison: `coreutils/dos2unix.c`
- Existing test file: `testsuite/sed.tests`
- Historical fix reviewed: 2024 `sed: check errors writing file with sed -i`, which added `fflush()` plus `ferror()` handling but left `fclose()` unchecked
- Upstream contact: **not authorized and not performed**

## Bounded question

Does BusyBox `sed -i` preserve the invariant that the original pathname is replaced only after the complete temporary output stream has finalized successfully?

## Invariant

An in-place transformation should keep the original file as the surviving input unless every required output step, including final stream close, has completed without a reported write/finalization error.

## Operation owner

`sed_main()` in `editors/sed.c` owns the temporary output, write-finalization check, optional backup rename, and final replacement rename.

## Source observations

### 1. `sed -i` checks flush state, then ignores `fclose()`

At the reviewed head, the in-place path executes:

```c
process_files();
fflush(G.nonstdout);
if (ferror(G.nonstdout)) {
    xfunc_error_retval = 4;
    bb_simple_error_msg_and_die(bb_msg_write_error);
}
fclose(G.nonstdout);
G.nonstdout = stdout;
```

It then proceeds to the optional backup and final replacement:

```c
if (opt_i) {
    char *backupname = xasprintf("%s%s", *argv, opt_i);
    xrename(*argv, backupname);
    free(backupname);
}
xrename(G.outname, *argv);
```

The return value from `fclose(G.nonstdout)` does not influence either rename.

### 2. This is distinct from the write-error class fixed in 2024

The historical BusyBox fix for `sed -i` write errors added the explicit `fflush()` and `ferror()` test. That closes the common buffered-write hole where ENOSPC appears while flushing userspace buffers.

The remaining question is narrower: a final `fclose()` may itself report an error after the preceding `fflush()` did not set the stream error indicator. Current source ignores that result.

### 3. Close-time errors are a real interface contract

Linux/POSIX stream semantics allow `fclose()` to fail because flushing or closing the underlying descriptor failed. Linux `close(2)` documentation specifically warns that errors such as I/O failure, quota exhaustion, or NFS-delayed write errors may become visible at close time.

That does not establish frequency for BusyBox users. It establishes that the unchecked return is semantically meaningful rather than dead error handling.

### 4. BusyBox already uses the stronger rule in `dos2unix`

At the same reviewed head, `coreutils/dos2unix.c` performs another in-place temp-file conversion and gates rename on both input and output close success:

```c
if (fclose(in) < 0 || fclose(out) < 0) {
    unlink(temp_fn);
    bb_perror_nomsg_and_die();
}
xrename(temp_fn, resolved_fn);
```

This is a useful internal negative control: BusyBox already treats an output `fclose()` failure as sufficient reason to discard the temporary result and avoid replacement in a closely related workflow.

### 5. The existing sed test suite does not exercise close failure

`testsuite/sed.tests` contains several `-i` cases, including ordinary in-place transformations and EOF/newline behavior. The inspected test file has no deterministic close-failure injection or assertion that the original survives a failed finalization.

### 6. The existing fatal-cleanup hook can support a small repair

When `-i` is enabled, `sed_main()` installs `cleanup_outname` as `die_func`. `cleanup_outname()` unlinks `G.outname` when a fatal path is taken.

That means a close failure can plausibly reuse the existing fatal cleanup behavior rather than requiring a new recovery mechanism. Exact patch design still needs execution and review.

## What evidence could make this intentional?

This pass looked for evidence that a successful `fflush()` is intended to make later `fclose()` errors irrelevant for BusyBox `sed -i`.

- The 2024 fix treats write-finalization errors as important enough to preserve the original file and return failure.
- Standard stream semantics give `fclose()` its own failure result.
- BusyBox `dos2unix` checks output `fclose()` before rename in an analogous in-place conversion.
- Current `sed.c` contains no comment documenting a deliberate choice to ignore close errors.
- Targeted source/history searches in this pass did not surface a later close-specific fix.

No source evidence found in this pass explains why a close failure should still permit publication.

## Cross-context pass

### Plain `-i` vs `-iSUFFIX`

**Discriminator:** whether an explicit backup suffix is requested.

- Plain `-i`: the final `xrename(G.outname, *argv)` replaces the input pathname directly after unchecked close.
- `-iSUFFIX`: BusyBox first renames the old input to the backup name, then renames the temporary output into the original pathname. The backup changes the recovery consequence, but the close error is still ignored and the temporary output is still published.

The finding therefore survives both modes, while the amount of surviving old data differs.

### Write/flush failure vs close-only failure

**Discriminator:** whether `fflush()`/`ferror()` observes the error before `fclose()`.

- Write/flush failure: the 2024 guard exits with an error before rename.
- Close-only failure: current source has no corresponding branch and proceeds to rename.

This is the key distinguishing test pair.

### `sed -i` vs `dos2unix FILE`

**Discriminator:** whether the in-place applet checks output `fclose()`.

- `sed -i`: unchecked close, then rename.
- `dos2unix FILE`: checked close; failure unlinks temp and exits before rename.

This comparison helps separate a general BusyBox policy from a local `sed` omission.

## Distinguishing probe to run next

Use only disposable local files.

### Probe A: deterministic close-only failure

1. Build the exact reviewed BusyBox head with `sed` enabled.
2. Create a disposable input file with recognizable original content.
3. Run a normal `sed -i` transformation as the passing control and verify replacement succeeds.
4. Add a test-only close-failure seam, preferably a link-time or tightly scoped wrapper around `fclose()` that:
   - targets only the `sed -i` temporary output stream;
   - allows the real close to occur;
   - makes that final `fclose()` report `EOF` with an I/O-style errno;
   - leaves the preceding explicit `fflush()` successful.
5. Run the same transformation.
6. Record:
   - BusyBox exit status;
   - stderr;
   - original pathname content and inode identity;
   - temporary-path survival;
   - optional backup content for an `-iSUFFIX` run.
7. Immediate clean rerun after the injected failure.

Expected current-source outcome: despite the injected `fclose()` failure, `sed` proceeds to `xrename(G.outname, *argv)` and returns success if no later operation fails.

A wrapper-induced return error proves the control-flow bug class, but it does not prove that a particular real filesystem loses bytes. Keep those claims separate.

### Probe B: filesystem-backed delayed close error, if practical

If a safe local NFS/FUSE/fault-injection fixture can produce a real close-reported write error after successful `fflush()`, repeat the same old-file-survival check without the wrapper.

Do not make this broader fixture a prerequisite for confirming that the close return is ignored; it answers a separate reachability/practical-consequence question.

## Expected distinguishing outcomes

### Outcome A: close failure is ignored and replacement occurs

- explicit flush succeeds;
- wrapped or filesystem-backed `fclose()` reports failure;
- BusyBox still renames the temp output over the input;
- exit status remains success unless a later operation fails.

**Disposition:** promote to confirmed defect; prepare a minimal close-check candidate and regression fixture.

### Outcome B: another mechanism prevents publication

For example, the test seam reveals an already-active fatal path or cleanup behavior that source reading missed.

**Disposition:** retain the disproving execution result and narrow or close the claim.

## Candidate repair boundary if reproduced

Keep the repair local to the `sed -i` finalization sequence:

- check the result of `fclose(G.nonstdout)`;
- on failure, set the same write-error exit code used by the existing `fflush()`/`ferror()` path;
- ensure `G.nonstdout` is left in a safe state before invoking fatal cleanup;
- let the existing `cleanup_outname` hook remove the temporary file;
- preserve the current rename order for successful operation;
- add one deterministic close-failure regression test and keep the existing write/flush failure behavior unchanged.

BusyBox is size-sensitive, so compare code size and avoid a broad helper unless it reduces or preserves cost across callers.

No source patch has been prepared in this pass.

## Evidence boundary

Established by source/history review:

- exact current `sed -i` control flow at `7473045ad3504db9b421427a452fd9b146346306`;
- explicit `fflush()` plus `ferror()` handling exists;
- `fclose(G.nonstdout)` return is ignored;
- replacement rename occurs afterward;
- `dos2unix` checks output close before analogous rename;
- current `sed.tests` includes normal `-i` behavior but no close-failure injection;
- the 2024 write-error fix addressed the flush-visible class, not the close-return class.

Not established yet:

- a runtime reproduction at the exact reviewed head;
- a concrete real filesystem that triggers this close-only sequence in the test environment;
- whether the output bytes are incomplete under any particular real failure mode;
- how often BusyBox deployments encounter delayed close errors;
- a reviewed source patch or code-size result;
- whether maintainers have an unindexed/private report or candidate.

## Stop condition

Stop this investigation as a source-only retained result if a deterministic test seam cannot distinguish `fflush` success from `fclose` failure without changing the publication path itself. Otherwise, execute the bounded probe and either promote the defect or record the disproof.

## External-contact state

No upstream greenlight was given. No BusyBox issue, mailing-list post, patch submission, comment, email, or other external contact was made.
