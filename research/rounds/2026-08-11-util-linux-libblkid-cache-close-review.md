# 2026-08-11 util-linux libblkid cache close review

## TL;DR

A source reconnaissance pass on `util-linux/util-linux` found one high-value bounded follow-up in libblkid's cache writer: `blkid_flush_cache()` clears its dirty flag and sets a success-looking return before `close_stream()` proves final output success, then ignores close failure for the temporary-file publication decision. The detailed record is in [`../../investigations/util-linux-blkid-cache-close-failure/README.md`](../../investigations/util-linux-blkid-cache-close-failure/README.md).

## Selection reason

This target matched several Linux Fieldwork bug lenses at once:

- durable publication through temporary-file + rename;
- bytes/completeness vs publication state;
- explicit finalization error reporting;
- cache lifecycle and retry state;
- nearby tests that cover normal behavior but not finalization failure.

The question remained small enough to map exactly from source without probing any live system.

## Exact source

- Repository: https://github.com/util-linux/util-linux
- Revision: `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Primary file: `libblkid/src/save.c`
- Adjacent source: `include/closestream.h`, `libblkid/src/cache.c`
- Adjacent test: `tests/ts/blkid/cache`

## First distinguishing observation

The writer's error branch is keyed off `ret < 0`, but a `close_stream()` failure only emits a debug message. Since `ret` was already set to `1`, the existing-regular-file path can still rename the temporary cache over the destination after the close layer has reported failure.

The same ordering clears `BLKID_BIC_FL_CHANGED` before successful close, so a failed finalization can also suppress a retry from the same cache handle.

## Cross-context result

The concern survives two important adjacent contexts:

- existing regular cache: failure can still flow into rename publication;
- direct-write fallback: no rename occurs, but dirty state is still cleared before finalization succeeds.

A useful built-in negative control also exists: a serialization failure that makes `ret < 0` does trigger temp-file unlink, showing that the intended safety branch exists but is not driven by close failure.

## Existing-work check

Linux Fieldwork search for util-linux/libblkid cache-close work returned no matching prior record. Targeted upstream open/closed issue searches for the same close/write-failure terms returned no matching issue in this pass.

## Next action

Run a local synthetic fault-injection fixture against the exact reviewed head. Force final stream close/write failure for only a disposable cache path, then record destination content, temp-file disposition, dirty flag, return value, and immediate clean rerun. Keep the result local unless upstream contact is separately authorized.

## External-contact state

Not authorized; none performed.
