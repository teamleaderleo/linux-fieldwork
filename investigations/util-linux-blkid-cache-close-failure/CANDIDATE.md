# libblkid cache finalization candidate

## Live checkpoint

- Unit: util-linux libblkid cache publication on finalization failure
- Worker/variant: source-only repair candidate
- Upstream base: `util-linux/util-linux` `53e442154c97b872b529a9f61e335d150ad0f742`
- Owned fork: `teamleaderleo/util-linux`
- Branch: `linux-fieldwork/libblkid-cache-finalize`
- Exact candidate head: `3fddc9e317ff9b2f25e6973bde42d7c04a8e8ab6`
- Changed paths: `libblkid/src/save.c` only
- Diff size: 7 additions, 5 deletions
- Automatic workflow runs observed for candidate head: none
- Runtime fault-injection gate: not executed
- External-contact state: not authorized; none performed

## Candidate design

The candidate keeps `BLKID_BIC_FL_CHANGED` set until the cache write has passed both stream finalization and, for the temporary-file path, final rename publication.

It makes three bounded control-flow changes:

1. successful serialization no longer clears the dirty flag before `close_stream()`;
2. a `close_stream()` failure becomes `-BLKID_ERR_IO`, which drives the existing temporary-file unlink path rather than rename publication;
3. the dirty flag is cleared only after successful rename, or after successful close on the direct-write path.

This also preserves dirty state when `rename()` fails, an adjacent ordering hole visible in the same original control flow.

The candidate deliberately does **not** normalize the existing positive-`errno` return convention on `fopen()` or `rename()` failure. That return-value inconsistency remains a separate question because the current investigation has not established a documented contract for `blkid_flush_cache()` beyond the surrounding internal usage.

## Exact diff review

Compared with upstream base `53e442154c97b872b529a9f61e335d150ad0f742`, the branch is exactly one commit ahead and modifies only `libblkid/src/save.c`.

The semantic paths are now:

### Existing regular destination

- serialization fails: temp file is unlinked; cache stays dirty;
- close/final write fails: return becomes `-BLKID_ERR_IO`, temp file is unlinked, old destination is preserved, cache stays dirty;
- close succeeds but rename fails: destination is not marked clean in memory; cache stays dirty;
- close and rename succeed: cache dirty flag is cleared.

### Direct-write destination

- close/final write fails: return becomes `-BLKID_ERR_IO`; cache stays dirty;
- close succeeds: cache dirty flag is cleared.

## Review caveat

This is not yet a validated upstream-ready patch. No compiler, util-linux test suite, or synthetic close-failure fixture has executed against `3fddc9e317ff9b2f25e6973bde42d7c04a8e8ab6` in this interaction.

The branch commit is also unsigned. util-linux's contribution guide requires a `Signed-off-by` trailer. Repository policy forbids inferring or synthesizing contributor identity, so the candidate must be signed locally with the contributor's configured Git identity before any upstream submission is considered.

## Next distinguishing gate

Run a disposable local fault-injection fixture against the exact candidate and its upstream base:

1. seed an existing regular cache path with sentinel content;
2. force the final stream flush/close to fail after serialization;
3. on the upstream base, record whether the temp file is renamed over the sentinel and whether the cache becomes clean;
4. on candidate `3fddc9e3...`, require the sentinel to remain, the temporary file to be removed, a negative return, and `BLKID_BIC_FL_CHANGED` to remain set;
5. remove fault injection and retry using the same cache handle; require successful publication and dirty-state clearing;
6. repeat for the direct-write path;
7. run the existing blkid cache test and relevant build/style gates.

## Stop / reopen rule

Do not describe the runtime consequence as confirmed until the fault-injection gate executes. If the base cannot be made to produce a genuine `close_stream()` failure with a realistic local fixture, retain the candidate as source reasoning rather than promoting it. If the candidate passes the discriminator, the next step is to add the smallest maintainable regression test and re-review the exact signed head.
