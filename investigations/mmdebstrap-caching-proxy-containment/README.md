# mmdebstrap caching proxy request validation and cache containment

## In simple words

`caching_proxy.py` turns an HTTP proxy request target directly into a filesystem path. A client can supply an absolute path, percent-encoded traversal, or a cache-internal symlink and make the helper read or write outside its configured cache directories.

The same decode-before-cache behavior also aliases distinct origin paths. For example, an encoded reserved character and its literal spelling can populate and read one cache entry even when the origin distinguishes them. The imported handler additionally uses Python `assert` for request validation, so `python -O` removes those checks.

The helper binds port 8080 on every interface. It is development and CI mirror tooling rather than an installed mmdebstrap service, but any client that can reach it can choose the request target while it runs.

## Canonical records

- request-validation issue: #150
- original containment issue: #93
- source: `upstream/mmdebstrap/caching_proxy.py`
- imported blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- candidate: `0001-confine-cache-paths.patch`
- regressions:
  - `tests/test_mmdebstrap_caching_proxy_containment.py`
  - `tests/test_mmdebstrap_caching_proxy_cache_key_distinctions.py`
  - `tests/test_mmdebstrap_caching_proxy_optimized_validation.py`
- reusable note: `notes/filesystems/url-cache-keys-must-not-be-filesystem-paths.md`

## Exact source boundary

The unmodified handler performs:

```python
assert int(self.headers.get("Content-Length", 0)) == 0
assert self.headers["Host"]
sanitizedpath = urllib.parse.unquote(self.path.removeprefix(pathprefix))
oldpath = oldcachedir / sanitizedpath
newpath = newcachedir / sanitizedpath
```

A decoded leading slash causes `pathlib` to discard the cache root. A decoded `..` component walks out of it. An existing symlink beneath the cache can redirect the later `mkdir`, read, or write operation.

The first cache-hit branch serves any existing path before the `.deb`/`by-hash` restriction, so an absolute request target can read an arbitrary file allowed by the proxy process's credentials. The download branch can write origin-controlled bytes to an arbitrary writable path.

Decoding also loses origin-visible distinctions. A first request for `a%3Bb.deb` can be cached as `a;b.deb`; a later literal `a;b.deb` request then receives the first object without reaching an origin that treats the two paths differently. Invalid UTF-8 percent bytes can also collapse through replacement decoding.

Under `python -O`, the imported assertions disappear. An origin-form absolute host path can then become an absolute `pathlib` operand and be served as a cache hit.

`main()` creates `ThreadingHTTPServer(("", 8080), ...)`, exposing that request surface on all interfaces.

## Candidate policy

The retained patch validates the HTTP request before cache lookup, directory creation, file access, or origin contact.

`cache_path()`:

- parses the absolute-form request target and `Host` independently;
- requires HTTP, no userinfo, one matching hostname/effective port, no query or fragment, and an absolute URL path;
- compares DNS hostnames case-insensitively;
- rejects every percent escape for this Debian archive helper instead of inventing a partial URL canonicalizer;
- rejects literal backslash, NUL, empty paths, doubled or trailing separators, and `.`/`..` components;
- constructs the relative path only from the still-raw component spelling;
- resolves each candidate against the cache root and requires a strict descendant, catching existing symlink escapes.

The handler:

- requires exactly one `Host` field;
- permits at most one `Content-Length` and requires its parsed value to be zero;
- rejects every `Transfer-Encoding` field;
- returns HTTP 400 rather than relying on assertions;
- binds the standalone helper to `127.0.0.1` only.

A normal Debian pool request remains a 200 response and is cached at the same relative path. A request-target hostname and `Host` hostname that differ only by ASCII case are accepted with the same effective port.

## Executable matrix

The real loopback tests require the imported baseline to reproduce:

1. absolute write escape;
2. encoded traversal write;
3. absolute read escape;
4. existing-symlink escape;
5. encoded-reserved/literal-reserved cache poisoning;
6. optimized-Python assertion bypass.

The candidate must then prove:

- all demonstrated filesystem escapes return 400;
- encoded, invalid-byte, dot, doubled-separator, trailing-separator, and literal-backslash aliases return 400 before origin contact or cache mutation;
- the literal reserved path remains independently fetchable and cacheable;
- duplicate Host, duplicate Content-Length, and Transfer-Encoding requests return 400 before origin contact;
- legitimate pool caching and case-insensitive hostname authority still work;
- ordinary and optimized source compile;
- loopback servers, subprocesses, and temporary roots are reaped.

## Severity and exposure

**Medium-high for the helper, approximately 7/10; lower for the installed package as a whole.**

The primitive permits arbitrary read of existing files and arbitrary write of origin-controlled bytes within the helper process's permissions. Cache-key aliasing can serve one origin object for a different request target. The all-interface bind increases reachability. The helper is not installed as the default mmdebstrap command or service; it is used by mirror generation, coverage, and autopkgtest workflows.

## Evidence limits

- Linux/POSIX pathname semantics only.
- The supported candidate path subset deliberately excludes percent escapes; this is narrower than general HTTP URI syntax and matches the tested Debian archive use.
- The `resolve()` check closes the demonstrated paths but is not a same-UID adversarial race-proof `openat(2)` sandbox. A process that can replace cache path components between validation and open remains outside this candidate.
- Origin request credential/hop-header filtering is owned by merged PR #139.
- Response framing and publication are separate composed boundaries.
- The proxy intentionally permits local HTTP forwarding; SSRF policy is not changed here.

## Cleanup and authority

Every server runs on loopback with an ephemeral port. Context managers call `shutdown()`, `server_close()`, and join the serving thread. Optimized subprocesses are terminated and waited. Temporary roots are deleted by `TemporaryDirectory`. No external network, privileged port, package mutation, or persistent host path is used.

## Disposition

Retain the candidate and executable regressions for internal review. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created.
