# URL cache keys must preserve origin distinctions and stay contained

## In simple words

A URL path is attacker-controlled protocol text. A filesystem path is an authority to read or write local storage. Joining the first to a cache directory does not automatically confine the second, and decoding the first before choosing a cache key can make two different origin paths share one object.

Containment and cache-key identity are separate requirements:

- the selected filesystem path must remain below the cache root;
- two request targets the origin may distinguish must not silently collapse to one cache entry.

## Failure patterns

This is unsafe:

```python
relative = urllib.parse.unquote(request_path)
cache_file = cache_root / relative
cache_file.parent.mkdir(parents=True, exist_ok=True)
cache_file.write_bytes(payload)
```

On POSIX, `pathlib.Path("/cache") / "/tmp/file"` becomes `/tmp/file`. Decoded `../` components are resolved by the kernel during open. A symlink under `/cache` can redirect the operation elsewhere.

The same problem affects reads. A cache-hit branch that checks `candidate.exists()` and then opens it can disclose an outside file before any extension or content policy is evaluated.

Decoding can also corrupt cache identity. `/pool/a%3Bb.deb` and `/pool/a;b.deb` are distinct origin request targets because semicolon is reserved, but decode to one filename. Invalid UTF-8 percent bytes can collapse through replacement decoding as well. The first response can poison the shared cache entry for the second request.

Path libraries may erase evidence before validation. `PurePosixPath("a/./b/")` exposes normalized parts `("a", "b")`; checking only those parts cannot distinguish literal-dot or trailing-separator request targets from their canonical spellings.

## Choose an explicit cache-key policy

Do not casually decode every path byte. Pick one policy and test it against the origin contract:

1. preserve a canonical escaped representation that remains injective for all accepted request targets; or
2. for a narrow helper, reject percent escapes entirely and accept only the raw safe subset actually needed.

A partial decoder that handles some escapes but collapses reserved or invalid byte sequences is not a safe middle ground.

For the mmdebstrap development proxy, the bounded candidate uses the second policy: ordinary Debian archive paths are accepted, while every percent escape is rejected before origin or cache work.

## Safer sequence

1. Parse the request target as an absolute-form URL.
2. Parse `Host` independently and require exactly one field.
3. Compare hostname case-insensitively and compare effective ports.
4. Reject credentials, query, fragment, and malformed authority syntax.
5. Reject ambiguous request framing: duplicate Content-Length, nonzero length, or any Transfer-Encoding for the bodyless GET contract.
6. Apply the chosen cache-key policy before pathname normalization. Under the narrow policy, reject every `%` and every literal backslash.
7. Split the still-raw path on `/`.
8. Reject empty, `.`, and `..` components, including doubled and trailing separators, plus NULs and absolute paths.
9. Construct the relative filesystem path only after those checks.
10. Resolve the candidate against a resolved cache root.
11. Require the resolved candidate to remain a strict descendant of that root.
12. Perform all checks before `mkdir`, existence tests, reads, writes, or origin contact.
13. Bind a development proxy to loopback unless remote clients are explicitly required.
14. For hostile same-UID races, use descriptor-relative `openat`/`openat2` style APIs and no-follow constraints rather than a check-then-open pathname.

Example narrow boundary:

```python
if "%" in raw_path or "\\" in raw_path or "\0" in raw_path:
    raise ValueError("unsafe cache key")
components = raw_path.split("/")
if any(part in ("", ".", "..") for part in components):
    raise ValueError("unsafe cache key")
root = cache_root.resolve()
candidate = (root / pathlib.Path(*components)).resolve()
if candidate == root or not candidate.is_relative_to(root):
    raise ValueError("unsafe cache path")
```

This closes the demonstrated traversal, alias, and pre-existing symlink paths. It is not by itself race-proof against another process replacing a path component after validation.

## Validation shape

A useful regression should include both compatibility and adversarial identity cases:

- a normal repository URL is fetched and stored below the cache;
- hostname case plus equivalent effective-port behavior follows the authority contract;
- absolute and parent-traversing paths cannot leave the cache;
- literal and encoded dot components are rejected before contacting origin;
- doubled and trailing separators are rejected without cache mutation;
- encoded-reserved versus literal-reserved paths return different origin bodies in the negative control and cannot share one candidate cache entry;
- invalid/non-UTF-8 percent bytes are rejected rather than replacement-decoded;
- literal backslash is rejected under the POSIX narrow policy;
- duplicate Host, duplicate Content-Length, and Transfer-Encoding are rejected before origin contact;
- an existing outside file cannot be served as a cache hit;
- a symlinked cache parent cannot redirect a write;
- optimized execution cannot erase request validation;
- the listener is loopback-only when remote access is unnecessary;
- all servers, subprocesses, and temporary paths are removed after success and failure.

Keep negative controls safe by placing demonstrated outside paths inside a larger disposable test directory rather than targeting real host files.

## Source and validation

This note is derived from issues #93 and #150 and `investigations/mmdebstrap-caching-proxy-containment/README.md`. The executable regressions are:

- `tests/test_mmdebstrap_caching_proxy_containment.py`;
- `tests/test_mmdebstrap_caching_proxy_cache_key_distinctions.py`;
- `tests/test_mmdebstrap_caching_proxy_optimized_validation.py`.

No upstream contact is authorized or made by this note.
