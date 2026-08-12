# libblkid cache finalization results

## Current state

The source-level publication concern is now backed by a repair candidate, an executable regression discriminator, a historical intent clue, and two hosted CI carriers. The decisive baseline-versus-candidate Linux execution is still in progress at this checkpoint.

- Reviewed upstream base: `util-linux/util-linux` `53e442154c97b872b529a9f61e335d150ad0f742`
- Candidate head: `teamleaderleo/util-linux` `fd9b056063921ff887de1e49989dc5bb28ccb004`
- Candidate CI: Build test run `31549879575`, internal draft PR 4
- Baseline-probe head: `02fdc9bcd473b9d40f967adea2c6a496b3fde86d`
- Baseline negative-control CI: Build test run `31549975503`, internal draft PR 5
- External-contact state: not authorized; no upstream interaction performed

## Historical intent evidence

Commit `8d21d9ab8ff65decfd03499a29627b6c9ecb21f2` from 2013 is titled:

> `libblkid: check writing to a file was successful`

That commit changed `libblkid/src/save.c` from an unchecked `fclose(file)` to:

```c
if (close_stream(file) != 0)
    DBG(SAVE, blkid_debug("write failed: %s", filename));
```

but left the already-positive `ret` and subsequent temporary-file publication decision unchanged.

This is useful intent evidence: final stream failure was explicitly considered meaningful enough to detect, but the change only added diagnostic logging. The current candidate closes the remaining control-flow hole by making that same failure prevent publication and by delaying dirty-state clearing until publication succeeds.

A 2025 memory-leak cleanup (`dfe1c4bc742ed3f53c06bb232ebc1f5fadd0881e`) touched nearby exits but did not change the close/publication ordering.

## Execution discriminator

The same regression test is being run in two controlled fork variants:

1. **Baseline probe** — upstream product source plus only the new test. Expected: Linux `blkid/cache` fails because a forced close/final-write failure still replaces the prior cache.
2. **Candidate** — the same test plus the `save.c` repair. Expected: Linux `blkid/cache` passes because the failed temporary cache is removed and the prior cache remains intact; a normal retry then succeeds.

The fault is induced locally and disposably with `RLIMIT_FSIZE=0` and ignored `SIGXFSZ` in the `blkid` subprocess. No real device data beyond the util-linux test suite's disposable loop devices is modified.

## Evidence boundary

At this checkpoint:

- historical intent evidence: established;
- exact source repair and test diff: established;
- candidate compile/check success on some non-discriminating matrix jobs: observed;
- Linux root execution of the new `blkid/cache` discriminator: not yet finalized;
- baseline negative-control failure: not yet finalized;
- direct-write-path fault injection: not separately executed;
- upstream contact: none.
