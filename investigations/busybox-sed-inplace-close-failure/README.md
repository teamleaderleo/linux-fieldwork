# BusyBox sed in-place publication on close failure

## TL;DR

Current BusyBox master at `7473045ad3504db9b421427a452fd9b146346306` has a bounded `sed -i` finalization defect: the in-place path calls `fflush()`, checks `ferror()`, ignores the return from `fclose()`, then renames the temporary output over the input.

A targeted local probe on Debian BusyBox 1.37.0 reproduced the error-handling consequence. The shim let the real temporary-output close complete, then made that `fclose()` report `EOF`/`EIO`. BusyBox `sed -i` still exited `0` and published the transformed output. `sed -i.bak` behaved the same while retaining the old file in the requested backup. BusyBox `dos2unix`, which checks output `fclose()` before rename, rejected the identical injected close result, exited `1`, and preserved the original.

Full commands, shim source, outputs, controls, and limits are in [`RESULTS.md`](RESULTS.md).

The remaining practical-consequence question is narrower: the synthetic seam proves that `sed -i` ignores a reported close error, while a filesystem-backed delayed close failure is still needed to demonstrate damaged persisted bytes under a real storage failure.

## Explain like I'm five

`sed -i` edits a temporary copy and swaps it into the original filename. BusyBox checks whether flushing that copy failed, but closing the copy can also report a late write error. Current `sed` ignores that final answer and performs the swap anyway.

BusyBox `dos2unix` already uses the safer rule for an analogous in-place conversion: if closing its temporary output fails, it deletes the temp and leaves the original alone.

## Why care

Linux permits some write and finalization failures to become visible at close time. A command that replaces the old file after `fclose()` reported failure can report success even though the output stream's final result was failure.

The confirmed claim is:

> BusyBox `sed -i` ignores a reported `fclose()` failure for its temporary output and can continue to rename that output over the input while returning success.

The evidence does **not** yet claim a particular real filesystem produces truncated or corrupt output in this sequence.

## Source and execution boundary

- Project: BusyBox
- Official source mirror: `https://github.com/vda-linux/busybox_mirror`
- Reviewed current-master revision: `7473045ad3504db9b421427a452fd9b146346306`
- Primary source: `editors/sed.c`
- Internal comparison: `coreutils/dos2unix.c`
- Existing tests: `testsuite/sed.tests`
- Current release observed during this pass: BusyBox 1.38.0, released 2026-05-13
- Runtime model: `/usr/bin/busybox` 1.37.0, Debian `1:1.37.0-6+b8`, dynamically linked with glibc
- Exact-current execution: blocked because the local runtime could not resolve GitHub for cloning; source review remained available through the GitHub connector
- Upstream contact: **not authorized and not performed**

## Bounded question

Does BusyBox `sed -i` preserve the invariant that the original pathname is replaced only after the complete temporary output stream has finalized without a reported error?

## Source observation

At the reviewed current head, `sed -i` executes:

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

Then it performs the optional backup and replacement:

```c
if (opt_i) {
    char *backupname = xasprintf("%s%s", *argv, opt_i);
    xrename(*argv, backupname);
    free(backupname);
}
xrename(G.outname, *argv);
```

The `fclose()` return does not affect either rename.

This is distinct from the write-error class fixed in 2024. That BusyBox change added `fflush()` plus `ferror()` so flush-visible errors such as ordinary ENOSPC stop before rename. A close-only error still has no branch.

## Internal negative control

At the same reviewed head, `coreutils/dos2unix.c` gates an analogous temp-file replacement on close success:

```c
if (fclose(in) < 0 || fclose(out) < 0) {
    unlink(temp_fn);
    bb_perror_nomsg_and_die();
}
xrename(temp_fn, resolved_fn);
```

This proves BusyBox already treats output-close failure as a publication blocker in a closely related path.

## Runtime reproduction

The local shim targeted only the adjacent temporary output stream. It called the real `fclose()` first and, after a successful real close, returned `EOF` with `errno=EIO` to the BusyBox caller. That isolates the handling of the close result from byte-persistence effects.

Observed matrix:

| Case | Injected temp close error | Exit | Transformed output published | Old content retained |
|---|---:|---:|---:|---:|
| `sed -i` | yes | 0 | yes | no explicit backup |
| `sed -i.bak` | yes | 0 | yes | yes, `.bak` |
| `dos2unix FILE` | yes | 1 | no | yes, original pathname |
| normal `sed -i` | no | 0 | yes | n/a |

See [`RESULTS.md`](RESULTS.md) for exact commands and outputs.

## Existing-test boundary

`testsuite/sed.tests` contains ordinary `-i` cases, including newline and EOF behavior. This pass found no deterministic close-failure injection or assertion that the original survives failed finalization.

## Repair boundary

A candidate should stay local to the `sed -i` finalization path:

1. check the result of `fclose(G.nonstdout)` before any backup or final rename;
2. use the existing write-error exit code (`4`);
3. leave state safe for the existing `cleanup_outname` fatal cleanup hook, which is installed for `-i` and removes `G.outname`;
4. preserve successful rename order;
5. add a deterministic close-error regression test;
6. measure BusyBox code-size delta.

No source candidate has been committed yet.

## Cross-context result

Plain `-i` and `-iSUFFIX` both ignore the close result. Backup mode retains the old bytes under the suffix, but still publishes the temporary output and reports success.

The important discriminator is flush-visible versus close-only failure:

- flush-visible failure: existing 2024 guard exits before rename;
- close-only failure: current source and runtime model continue to rename.

`dos2unix` provides the same-project counterexample where close-only failure blocks publication.

## Evidence boundary

Established:

- exact current-master source sequence;
- unchecked temporary-output `fclose()` before replacement;
- current tests lack a close-failure case;
- installed BusyBox 1.37.0 reproduces replacement plus exit `0` after targeted reported close failure;
- backup mode behaves the same with the old content retained in `.bak`;
- `dos2unix` rejects the same close failure and preserves the original;
- normal `sed -i` control succeeds.

Still open:

- exact-current binary execution at `7473045ad3504db9b421427a452fd9b146346306`;
- a real filesystem-backed delayed-close failure;
- persisted-byte consequence under that real failure;
- candidate compilation, tests, and code-size result;
- upstream maintainer interpretation or prior unindexed discussion.

## Next action

Prepare and execute the smallest local current-master candidate once an exact source checkout is available. The first gate should be the deterministic close-return test, followed by normal `sed -i`, backup mode, existing `sed.tests`, and code-size comparison.

A filesystem-backed close-error experiment can follow as a consequence/reachability test; it is a separate question from whether the current code ignores the error result.

## External-contact state

No upstream greenlight was given. No BusyBox issue, mailing-list post, patch submission, comment, email, or other external contact was made.
