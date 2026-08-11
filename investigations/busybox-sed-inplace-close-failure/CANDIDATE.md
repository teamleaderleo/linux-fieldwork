# BusyBox sed close-check candidate

## Status

Draft local candidate only. It has not been compiled against the exact current BusyBox tree because the execution runtime could not clone `vda-linux/busybox_mirror`. No upstream contact is authorized.

## Intended source boundary

```text
vda-linux/busybox_mirror
7473045ad3504db9b421427a452fd9b146346306
editors/sed.c
```

## Minimal change

The current code is:

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

The smallest candidate observed in this pass is:

```diff
 			process_files();
 			fflush(G.nonstdout);
-			if (ferror(G.nonstdout)) {
+			if (ferror(G.nonstdout) || fclose(G.nonstdout)) {
 				xfunc_error_retval = 4;  /* It's what gnu sed exits with... */
 				bb_simple_error_msg_and_die(bb_msg_write_error);
 			}
-			fclose(G.nonstdout);
 			G.nonstdout = stdout;
```

## Why this boundary

This preserves the existing behavior for a stream that already has its error indicator set: the left side of `||` short-circuits, so the fatal path runs before `fclose()`, just as it does today.

For the previously uncovered branch, where `ferror()` is clear but `fclose()` reports failure, the close now feeds the same existing write-error path and exit code before either backup or final rename.

Successful operation still closes the stream exactly once and continues unchanged.

The candidate therefore adds one missing discriminator without introducing a new helper, recovery mode, output format, or rename policy.

## Cleanup interaction

For `-i`, `sed_main()` installs `cleanup_outname` as `die_func`. The existing fatal write-error path already relies on this to remove the temporary output when `ferror()` is set.

A close failure routed through the same fatal path should reuse that cleanup. The deterministic regression gate must verify that no temp survives and the input pathname remains unchanged.

## Required gates before this becomes a source candidate

1. Apply the diff to the exact current BusyBox head.
2. Build BusyBox with `sed` enabled.
3. Run the existing `testsuite/sed.tests`.
4. Run ordinary `sed -i` and `sed -iSUFFIX` controls.
5. Run a deterministic close-only failure seam:
   - preceding `fflush()` succeeds;
   - output `fclose()` reports failure;
   - plain `-i` exits `4` and leaves original input intact;
   - backup mode exits `4` before moving the original to the suffix;
   - no temporary output survives.
6. Run the same close seam against `dos2unix` as a stable negative-control comparison.
7. Measure the BusyBox text-size delta using the project's normal size-report convention.
8. Inspect the complete exact-head diff and rerun after cleanup.

## Test-fixture decision

The local `LD_PRELOAD` wrapper in [`RESULTS.md`](RESULTS.md) is good evidence for the branch but is probably too environment-specific to assume as the upstream regression fixture. Current `testsuite/sed.tests` does not appear to use `LD_PRELOAD`, and targeted source searches found no established ENOSPC/close-injection helper convention.

Before adding test machinery, prefer the smallest project-acceptable seam. Options to evaluate on an exact checkout:

- a testsuite helper already used elsewhere for syscall failure injection, if one is found by a broader local source search;
- a tiny optional test helper compiled only for the test suite;
- retaining the deterministic external seam in Fieldwork if upstream's test conventions make a permanent close-only fixture disproportionate.

Do not broaden product code merely to make the test easy.

## Evidence boundary

The one-line candidate follows directly from the reproduced control-flow defect, but it is still a design proposal until exact-head compilation, tests, cleanup, and size measurement run.

## External-contact state

No upstream greenlight; no BusyBox interaction has been made.
