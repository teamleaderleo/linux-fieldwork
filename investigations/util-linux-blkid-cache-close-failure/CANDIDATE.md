# libblkid cache finalization candidate

## Live checkpoint

- Unit: util-linux libblkid cache publication on finalization failure
- Worker/variant: repair plus regression candidate
- Upstream base: `util-linux/util-linux` `53e442154c97b872b529a9f61e335d150ad0f742`
- Owned fork: `teamleaderleo/util-linux`
- Candidate branch: `linux-fieldwork/libblkid-cache-finalize`
- Exact candidate head: `fd9b056063921ff887de1e49989dc5bb28ccb004`
- Controlled execution base: `linux-fieldwork/upstream-2026-08-11` at exact upstream head `53e442154...`
- Internal draft PR: `teamleaderleo/util-linux` PR 4
- Changed paths: `libblkid/src/save.c`, `tests/ts/blkid/cache`
- Diff against upstream base: 40 additions, 5 deletions across two files
- Hosted CI: Build test run `31549879575` started for exact head `fd9b056...`; multiple build/check jobs in progress when this checkpoint was written
- External-contact state: not authorized; no upstream interaction performed

## Candidate design

The source change keeps `BLKID_BIC_FL_CHANGED` set until the cache write has passed both stream finalization and, for the temporary-file path, final rename publication.

It makes three bounded control-flow changes:

1. successful serialization no longer clears the dirty flag before `close_stream()`;
2. a `close_stream()` failure becomes `-BLKID_ERR_IO`, which drives the existing temporary-file unlink path rather than rename publication;
3. the dirty flag is cleared only after successful rename, or after successful close on the direct-write path.

This also preserves dirty state when `rename()` fails, an adjacent ordering hole visible in the same original control flow.

The candidate deliberately does **not** normalize the existing positive-`errno` return convention on `fopen()` or `rename()` failure. That return-value inconsistency remains a separate question because the current investigation has not established a documented contract for `blkid_flush_cache()` beyond the surrounding internal usage.

## Regression discriminator

The existing executable `tests/ts/blkid/cache` now includes a bounded write-finalization failure case without adding test-only hooks to product code.

The test:

1. creates and caches a disposable loop-backed swap device;
2. copies the known-good regular cache file;
3. detaches the loop device so garbage collection must dirty the in-memory cache;
4. runs `blkid --garbage-collect` in a subshell with `RLIMIT_FSIZE=0` and `SIGXFSZ` ignored;
5. requires the prior cache file to remain byte-for-byte unchanged after the forced write failure;
6. removes the limit and reruns garbage collection, requiring the stale loop-device entry to disappear normally.

Why this distinguishes the bug: creating the temporary file is still allowed, but writing its buffered contents is prohibited. `close_stream()` therefore sees the final stream error. The original source leaves `ret` positive and proceeds to rename the failed temporary cache over the prior cache; the candidate converts that finalization failure into an error and unlinks the temporary file instead.

The file-size limit exists only in the `blkid` subprocess, so the parent test can continue writing its normal result files.

## Exact diff review

Compared with upstream base `53e442154c97b872b529a9f61e335d150ad0f742`, the branch is exactly two commits ahead and modifies only:

- `libblkid/src/save.c`
- `tests/ts/blkid/cache`

No workflow, generated file, carrier helper, or Fieldwork-only file is present in the source candidate.

The semantic source paths are now:

### Existing regular destination

- serialization fails: temp file is unlinked; cache stays dirty;
- close/final write fails: return becomes `-BLKID_ERR_IO`, temp file is unlinked, old destination is preserved, cache stays dirty;
- close succeeds but rename fails: cache stays dirty;
- close and rename succeed: cache dirty flag is cleared.

### Direct-write destination

- close/final write fails: return becomes `-BLKID_ERR_IO`; cache stays dirty;
- close succeeds: cache dirty flag is cleared.

## Hosted execution carrier

The fork's upstream `cibuild.yml` runs on `pull_request`, so an internal draft PR was opened only inside `teamleaderleo/util-linux` against a temporary controlled base branch pinned to the exact upstream head. This avoids upstream contact and avoids changing candidate history merely to trigger CI.

Observed run:

- workflow: `Build test`
- run id: `31549879575`
- exact head: `fd9b056063921ff887de1e49989dc5bb28ccb004`
- initial status: in progress
- matrix included gcc/clang build+check jobs, Meson, compatibility, qemu-user, macOS, and OpenWrt jobs; coveralls was skipped because the repository is the owned fork.

Do not treat the candidate as validated until the relevant jobs complete and the exact test result is inspected.

## Review caveats

The branch currently contains two logical preparation commits. If the candidate survives execution, rebuild or squash it into one clean commit before presenting it for human upstream review.

The branch commits are unsigned. util-linux's contribution guide requires a `Signed-off-by` trailer. Repository policy forbids inferring or synthesizing contributor identity, so the final candidate must be signed locally with the contributor's configured Git identity before any upstream submission is considered.

The regression currently establishes the existing-regular-cache publication boundary and a clean process-level retry. It does not directly inspect the private in-memory dirty flag in the same cache handle, and it does not yet cover the direct-write path under the same fault.

## Next gate

1. Inspect Build test run `31549879575` for the exact head `fd9b056...`.
2. If the blkid cache regression or another job fails, classify the first failure as product, fixture, platform/capability, or workflow before changing source.
3. If the candidate passes, add or run the smallest direct-write-path discriminator only if it can still change the repair decision.
4. Re-review the exact diff, then squash to one clean source/test commit and leave it unsigned for local `git commit -s` completion.

## Stop / reopen rule

Do not describe the runtime consequence as confirmed until the write-failure discriminator has actually executed on a Linux CI job. If the file-size-limit fixture proves invalid or is skipped before reaching `close_stream()`, repair the fixture rather than the product. If the candidate passes the discriminator and ordinary cache behavior, the bounded publication claim is strong enough to move to human review; broader return-value normalization remains a separate successor question.
