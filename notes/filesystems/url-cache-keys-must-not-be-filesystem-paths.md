# URL cache keys must not become filesystem paths without containment

## In simple words

A URL path is attacker-controlled text. A filesystem path is an authority to read or write local storage. Joining the first to a cache directory does not automatically confine the second.

Percent decoding, absolute paths, `..` components, repeated or trailing separators, normalization aliases, and symlinks can all change where a later open lands. Validate the decoded component stream before pathname normalization or file I/O, and still keep the network listener as narrow as possible.

## Failure pattern

This is unsafe:

```python
relative = urllib.parse.unquote(request_path)
cache_file = cache_root / relative
cache_file.parent.mkdir(parents=True, exist_ok=True)
cache_file.write_bytes(payload)
```

On POSIX, `pathlib.Path("/cache") / "/tmp/file"` becomes `/tmp/file`. Decoded `../` components are resolved by the kernel during open. A symlink under `/cache` can also redirect the operation elsewhere.

The same problem affects reads. A cache-hit branch that checks `candidate.exists()` and then opens it can disclose an outside file before any extension or content policy is evaluated.

Path libraries may erase evidence before validation. `PurePosixPath("a/./b/")` exposes the normalized parts `("a", "b")`; checking only those parts cannot distinguish literal-dot or trailing-separator request targets from their canonical spellings. If those targets are not guaranteed equivalent by the origin contract, accepting both creates cache-key aliases.

## Safer sequence

1. Parse the request target as a URL, not by string prefix removal alone.
2. Verify scheme and authority against the protocol contract. Compare hostname case-insensitively and effective ports rather than requiring byte-identical DNS authority spelling.
3. Reject credentials and unexpected query or fragment data.
4. Reject encoded path separators, then decode exactly once.
5. Split the decoded path on `/` before pathname normalization.
6. Reject empty, `.`, and `..` components, including doubled and trailing separators, plus NULs and absolute paths.
7. Construct the relative filesystem path only after those checks.
8. Resolve the candidate against a resolved cache root.
9. Require the resolved candidate to remain below that root.
10. Perform the check before `mkdir`, existence tests, reads, and writes.
11. Bind a development proxy to loopback unless remote clients are explicitly required.
12. For hostile same-UID races, use descriptor-relative `openat`/`openat2` style APIs and no-follow constraints rather than a check-then-open pathname.

Example boundary:

```python
components = decoded_path.split("/")
if any(part in ("", ".", "..") for part in components):
    raise ValueError("unsafe cache key")
root = cache_root.resolve()
candidate = (root / pathlib.Path(*components)).resolve()
if candidate == root or not candidate.is_relative_to(root):
    raise ValueError("unsafe cache path")
```

This closes ordinary traversal, cache-key aliases covered by the component policy, and pre-existing symlink escapes. It is not by itself race-proof against another process replacing a path component after validation.

## Validation shape

A useful regression should include both compatibility and escape cases:

- a normal repository URL is fetched and stored below the cache;
- hostname case plus equivalent explicit/default port behavior follows the authority contract;
- a doubled-slash absolute path cannot write outside;
- percent-encoded `..` cannot escape;
- literal and encoded `.` components are rejected before contacting origin;
- doubled and trailing separators are rejected without cache mutation;
- an existing outside file cannot be served as a cache hit;
- a symlinked cache parent cannot redirect a write;
- the listener is loopback-only when remote access is unnecessary;
- all servers and temporary paths are removed after success and failure.

Keep negative controls safe by placing the demonstrated outside path inside a larger disposable test directory rather than targeting a real host file.

## Source and validation

This note was derived from issue #42 and `investigations/mmdebstrap-caching-proxy-containment/README.md`. The executable regression is `tests/test_mmdebstrap_caching_proxy_containment.py`.

No upstream contact is authorized or made by this note.
