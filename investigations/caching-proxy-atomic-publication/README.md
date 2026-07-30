# caching_proxy atomic publication

## In simple words

The proxy is threaded, but a cache miss writes directly to the final cache filename. A second request can see that in-progress file, classify it as a cache hit, and return only the bytes written so far under HTTP 200.

## Canonical records

- Focused issue: #95
- Imported source: `upstream/mmdebstrap/caching_proxy.py`
- Candidate patch: `0001-publish-cache-files-atomically.patch`
- Regression: `tests/test_caching_proxy_atomic_publication.py`
- Reusable note: `notes/reliability/cache-files-must-be-published-atomically.md`
- Related containment boundary: #93 / PR #94

## Baseline source boundary

Both cache-fill paths open the final name with `wb`:

- copying an immutable `.deb` or by-hash object from the old cache;
- downloading a fresh object from the upstream server.

The earlier cache-hit branch checks only `newpath.exists()`, records its current size as `Content-Length`, and streams the bytes currently visible.

## Synchronized negative control

A local upstream sends one 64 KiB chunk and blocks before sending a second. The first proxy request opens the final cache path and writes the first chunk. While the upstream remains blocked, a second request for the same URL receives:

- HTTP 200;
- a 64 KiB `Content-Length`;
- only the first chunk;
- no second upstream request.

After the upstream is released, the first request and final cache file become complete. This proves that a later complete cache can hide the earlier partial response.

## Candidate

`cache_destination()` creates a unique temporary file in the destination directory. The caller streams to that file, closes it, and publishes the final path with `os.replace()` only after successful completion. A `finally` block removes any remaining temporary file. `/dev/null` in readonly mode remains a direct sink.

Both the old-cache-copy and fresh-download branches use the same helper.

## Candidate concurrency matrix

With the same blocked upstream:

1. request A writes its first chunk to a unique temporary file;
2. the final path remains absent;
3. request B performs its own upstream request rather than observing a cache hit;
4. both clients receive the complete two-chunk body after release;
5. the final cache path contains the complete object;
6. no temporary files remain.

Duplicate upstream work remains possible. This candidate owns complete-object visibility, not request coalescing.

## Failure control

An injected exception after writing the first chunk through `cache_destination()` must leave neither a final path nor a temporary file.

## Evidence boundary

The regression uses real threaded local HTTP servers and the imported handler. It does not require external network access, apt, package installation, root, or the full mirror builder.

Atomic replacement prevents partial final-name visibility. It does not add checksums, fsync durability guarantees, per-key locks, or protection against a malicious same-user process modifying temporary files.

## Cleanup and safety

All files live below a `TemporaryDirectory`. Both proxy and upstream servers bind ephemeral loopback ports, are shut down, closed, and joined. The blocked upstream is released during cleanup even after assertion failures.

## Disposition

Retain the atomic-publication candidate as a separate reliability/integrity fix. No Debian or external upstream contact is included or authorized.
