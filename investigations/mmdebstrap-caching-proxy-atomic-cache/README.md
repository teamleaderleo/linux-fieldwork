# mmdebstrap caching proxy atomic publication

## In simple words

`caching_proxy.py` writes an origin response straight into its final cache filename. If the origin closes early, the short file remains and later requests serve it as a valid cache hit.

The local candidate writes to a temporary sibling, validates `Content-Length` when present, and atomically promotes the file only after complete success.

## Canonical records

- issue: #123
- source: `upstream/mmdebstrap/caching_proxy.py`
- imported blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- candidate: `0001-publish-cache-files-atomically.patch`
- regression: `tests/test_mmdebstrap_caching_proxy_atomic_cache.py`
- reusable note: `notes/filesystems/cache-files-need-an-atomic-publication-boundary.md`

## Exact baseline behavior

The download path opens `newpath` before the first response byte is read:

```python
with newpath.open(mode="wb") as f:
    while True:
        buf = res.read(64 * 1024)
        if not buf:
            break
        self.wfile.write(buf)
        f.write(buf)
```

`HTTPResponse.read(amt)` does not guarantee an exception when a fixed-length response closes early. It can return the short prefix and then `b""`. The loop treats that as completion.

The next request checks only `newpath.exists()`, advertises the short file's current size, and serves it as HTTP 200. The transport failure has become persistent cache state.

The old-cache copy branch also writes directly to the final path. A client disconnect or local I/O error can therefore publish an empty or partial promoted file.

## Negative control

The regression runs the exact imported handler against a loopback origin that:

1. advertises `len(short_body) + 1024`;
2. writes only `short_body`;
3. closes the connection.

The baseline must:

- return a 200 response whose body is shorter than its advertised length;
- leave the short bytes at the final cache path;
- serve that short file on a later request as a clean 200 response with the shorter length.

## Candidate

The retained patch adds `atomic_cache_writer()`:

- creates a named temporary sibling in the final directory;
- writes, flushes, and `fsync()`s the temporary file;
- uses `os.replace()` to publish it atomically;
- removes the temporary path in `finally` after success or failure;
- preserves `/dev/null` behavior for readonly runs.

The origin download path records the received byte count. If `Content-Length` is present and the count differs, it raises before the atomic writer exits, so no final path is published.

The same writer wraps old-cache copies. If a response has already started, the exception path closes the client connection instead of appending a second HTTP error response after the 200 headers.

## Regression matrix

- unmodified proxy promotes and reuses a truncated origin body;
- candidate leaves neither a final file nor a temporary sibling after the same short response;
- complete candidate response is cached and served successfully after the origin stops;
- direct interruption inside the atomic writer removes the temporary file;
- old-cache copy still produces complete bytes through the atomic path;
- source-level control requires both write sites to call the helper.

All servers use loopback ephemeral ports. All roots live in `TemporaryDirectory` and every server thread is shut down, closed, and joined.

## Severity

**Medium integrity/availability, approximately 6/10.**

This helper belongs to development, mirror-generation, coverage, and autopkgtest workflows rather than the installed mmdebstrap command. A transient origin failure can nevertheless poison a shared cache and make later package tests fail repeatedly until the cache is rebuilt.

Package and index hash verification should prevent silent installation of changed bytes, but it does not prevent persistent mirror/test failure or loss of the original transport diagnosis.

## Evidence limits

- The short fixed-length response is reproduced with Python's loopback HTTP server.
- Close-delimited responses without `Content-Length` are complete at EOF by protocol and cannot be distinguished from truncation with this boundary alone.
- A hard process kill can leave a dot-prefixed temporary sibling; the final cache name remains unpublished.
- Concurrent complete requests may race to `os.replace()` the same URL. They should carry identical bytes; cross-process locking is outside this candidate.
- The path-containment defect is tracked separately in #42 / PR #118.

## Disposition

Retain the candidate and regression for internal review. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created.
