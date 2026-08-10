# util-linux libblkid cache publication on close failure

## TL;DR

Source review of `util-linux/util-linux` at commit `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6` found a bounded cache-integrity concern in `libblkid/src/save.c`: `blkid_flush_cache()` marks the cache clean before `close_stream()` proves the write completed, ignores a `close_stream()` failure except for debug logging, and on the temporary-file path still proceeds to rename the temporary cache over the destination because `ret` remains positive. This is a source-level finding only; no fault-injection execution has been run yet.

The next useful action is a local synthetic fault-injection probe that makes the final stream flush/close fail and distinguishes whether a partial cache is published, whether `BLKID_BIC_FL_CHANGED` remains cleared, and what return value the caller receives.

## Explain like I'm five

libblkid writes a refreshed device cache. When an old regular cache exists, it wisely writes a temporary file first so a failed write should not replace the good cache. But the current control flow decides "the write succeeded" before the file is actually closed. If closing reports that buffered data could not be written, the code only logs that fact and can still rename the temporary file into place.

That creates a hole in the safety mechanism: the temporary file protects the old cache only if write failure changes the decision before rename.

## Why care

`libblkid`'s cache is specifically meant to preserve block-device information for later lookups, including consumers that cannot directly probe raw devices. Publishing an incompletely written cache, or clearing the in-memory dirty flag after a failed write, can turn a recoverable I/O failure into stale or truncated cached state.

The strongest current claim is deliberately narrow: **the source control flow does not gate publication or dirty-state clearing on successful `close_stream()` completion.** Runtime consequence still needs a fault-injection fixture.

## Source boundary

- Project: `util-linux/util-linux`
- Upstream repository: https://github.com/util-linux/util-linux
- Reviewed revision: `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Reviewed files:
  - `libblkid/src/save.c`
  - `include/closestream.h`
  - `libblkid/src/cache.c`
  - `tests/ts/blkid/cache`
- Upstream issue search: no open or closed issue was found by searches for the specific `blkid` cache / `close_stream` write-failure terms used in this pass.
- Upstream contact: **not authorized and not performed**.

## Bounded question

Does `blkid_flush_cache()` preserve the invariant that a cache is published and marked clean only after the complete cache stream has been successfully written and closed?

## Invariant

A cache refresh should not replace the prior regular cache, nor clear its changed/dirty state, until the complete replacement stream has been accepted successfully by the write/close path.

## Operation owner

`blkid_flush_cache()` in `libblkid/src/save.c` owns serialization, temporary-file selection, close handling, dirty-state clearing, backup creation, and final rename.

`close_stream()` in `include/closestream.h` is the component that turns prior stream errors or a failing `fclose()` into an `EOF` result.

## Authority boundary

Filesystem writes to the configured libblkid cache path. The default cache is normally under the libblkid runtime/default cache location, but `BLKID_FILE` or configuration may select another path. This investigation does not claim a privilege escalation or security boundary crossing.

## Source observations

### 1. Success state is committed before close succeeds

After serializing devices, `blkid_flush_cache()` does this when `ret >= 0`:

```c
cache->bic_flags &= ~BLKID_BIC_FL_CHANGED;
ret = 1;
```

Only afterward does it call:

```c
if (close_stream(file) != 0)
    DBG(SAVE, ul_debug("write failed: %s", filename));
```

The close result is logged but does not restore `BLKID_BIC_FL_CHANGED` and does not change `ret`.

### 2. The temporary-file safety path can still publish after close failure

When the destination already exists and is a regular file, the function creates a same-directory temporary file and writes there. After the ignored close failure, publication is decided by `ret`:

```c
if (opened != filename) {
    if (ret < 0) {
        unlink(opened);
    } else {
        ...
        if (rename(opened, filename)) {
            ret = errno;
        }
    }
}
```

Because a close failure leaves `ret == 1`, the code takes the rename branch rather than unlinking the temporary file.

This means the temporary-file mechanism does not currently prove completeness before publication.

### 3. The direct-write path has the same dirty-state problem

If the destination does not already exist, is not a regular file, or a temporary file cannot be created, `blkid_flush_cache()` falls back to opening `filename` directly. A later `close_stream()` failure is still only logged, with the dirty bit already cleared and `ret` still positive.

The publication mechanism differs, but the success-state ordering problem is shared.

### 4. `close_stream()` is explicitly designed to report these failures

`include/closestream.h` records an existing `ferror(stream)` and the result of `fclose(stream)`. It returns `EOF` for an earlier stream error or for relevant close failures. `blkid_flush_cache()` therefore receives an explicit failure signal but currently does not use it to control cache publication or dirty state.

### 5. Existing blkid cache test coverage does not exercise write-finalization failure

`tests/ts/blkid/cache` covers normal cache creation/use and garbage collection with loop devices. The inspected test does not inject an error during flush/close and does not assert preservation of an old cache after failed finalization.

### 6. Cache destruction can make the missed retry permanent for that handle

`blkid_put_cache()` calls `blkid_flush_cache(cache)` and intentionally ignores its return value before freeing the cache object. That means a failed close during this common finalization path has no later in-memory retry opportunity from the same handle.

## Secondary source-level inconsistency to probe

On `rename(opened, filename)` failure, `blkid_flush_cache()` assigns `ret = errno`, which is positive on normal POSIX systems. The test-program code in `save.c` treats only `ret < 0` as a save error. This suggests a second error-signaling mismatch, but this pass has not established a documented public return-value contract for `blkid_flush_cache()` itself. Keep this as a probe target rather than a confirmed API bug.

## What evidence could make the behavior intentional?

The source review looked for nearby evidence that would justify publication despite `close_stream()` failure:

- `close_stream()` treats stream/fclose failures as meaningful errors rather than advisory events.
- the same function deliberately uses a temporary file to avoid overwriting the cache "in case of error";
- the existing cache test exercises ordinary success/garbage-collection behavior, not a contract that permits partial publication;
- targeted open/closed issue searches did not surface a documented intentional exception for this path.

No intent evidence found in this pass explains why a close failure should still clear the dirty bit or permit rename.

## Cross-context pass

### Existing regular cache vs absent/non-regular cache

**Discriminator:** whether `opened != filename` and rename publication is used.

- Existing regular cache: failed close can still flow into rename, potentially replacing a previously good cache.
- Direct-write fallback: there is no rename, but the cache is still marked clean before close success and the direct target may be incomplete.

Both contexts preserve the ordering concern; only the publication mechanism changes.

### Serialization failure vs finalization failure

**Discriminator:** whether `save_dev()` makes `ret < 0` before close.

- Serialization failure: the temporary path unlinks the temp file because `ret < 0`.
- Finalization failure: `close_stream()` failure does not modify `ret`, so the temp path still publishes.

This contrast is the strongest source-level negative control: the cleanup branch exists and is reachable for one failure class but not the close-failure class.

### Explicit flush caller vs destructor path

**Discriminator:** whether a caller can observe/retry after `blkid_flush_cache()`.

- Explicit call: a caller could theoretically inspect the return, though current source-level signaling needs runtime verification.
- `blkid_put_cache()`: the return is discarded and the handle is immediately freed.

The destructor path increases the practical importance of preserving the correct dirty/publication decision inside `blkid_flush_cache()` itself.

## Distinguishing probe to run next

A safe local fixture should avoid real block devices if possible and should operate in a disposable directory.

1. Build the exact reviewed util-linux head (or a minimal test harness around `blkid_flush_cache()`).
2. Seed a known-good regular cache file with recognizable sentinel content.
3. Create an in-memory cache marked changed with enough serialized content to force buffered output.
4. Inject a deterministic finalization failure at the stream layer (for example with a controlled shim/wrapper that makes `fclose`/final write fail for only the test cache descriptor).
5. Call `blkid_flush_cache()`.
6. Record:
   - return value;
   - whether the destination inode/content changed;
   - whether the temporary file remains or was renamed;
   - whether `BLKID_BIC_FL_CHANGED` is still set;
   - debug trace from the save path.
7. Negative control: same fixture without injected close failure must replace the old cache and clear the changed flag.
8. Clean rerun: immediately repeat a normal flush after the injected failure and verify whether the cache handle still considers itself dirty enough to retry.

A second fixture should cover the absent-file/direct-write path separately.

## Expected distinguishing outcomes

### Outcome A: source-level concern reproduces

- close/final-write failure is observed;
- old regular cache is replaced or the direct target is left incomplete;
- `BLKID_BIC_FL_CHANGED` is clear;
- caller receives a non-error-looking result or destructor discards it.

**Disposition:** promote to confirmed defect; prepare a minimal candidate that delays dirty-state clearing and publication until close success, plus regression tests.

### Outcome B: underlying runtime semantics prevent harmful publication

For example, the injected condition cannot produce `close_stream()` failure after the serialized data state assumed here, or some lower layer guarantees the replacement remains complete.

**Disposition:** retain as a negative result and document the exact reason the apparent source hazard is not reachable.

## Candidate repair boundary if reproduced

Keep the repair inside `blkid_flush_cache()`:

- treat `close_stream(file) != 0` as a real save failure;
- do not clear `BLKID_BIC_FL_CHANGED` until all required write/close steps succeed;
- on temp-file finalization failure, unlink the temp file instead of renaming it over the destination;
- define a consistent error return for close and rename failures;
- add tests for existing-regular-cache and direct-write paths.

No source patch has been prepared in this pass.

## Evidence boundary

Established by source review:

- exact control-flow ordering at commit `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`;
- `close_stream()` has an explicit failure signal;
- `blkid_flush_cache()` ignores that signal for `ret`, dirty state, and temp-file publication;
- inspected cache tests do not cover finalization failure;
- `blkid_put_cache()` ignores flush return before freeing the cache.

Not established yet:

- a runtime reproduction on Linux;
- which concrete filesystem/device failure modes trigger the relevant `close_stream()` failure in practice;
- exact persisted bytes after such a failure;
- the intended public return-value contract of `blkid_flush_cache()`;
- whether maintainers already have an unindexed/private fix or discussion;
- behavior on non-Linux platforms or unusual stdio implementations.

## Stop condition

Stop this investigation as a source-only result if a deterministic local close-failure fixture cannot distinguish publication/dirty-state behavior without invasive or unrealistic instrumentation. Otherwise, run the two bounded fixtures above and either promote the defect or retain a disproving result.

## External-contact state

No upstream greenlight was given. No upstream issue, pull request, comment, review, email, or other contact was created.
