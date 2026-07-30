# mmdebstrap caching proxy cache-root containment

## In simple words

`caching_proxy.py` turns an HTTP proxy request target directly into a filesystem path. A client can supply an absolute path, percent-encoded `..`, or a cache-internal symlink and make the helper read or write outside its configured cache directories.

The helper also binds port 8080 on every interface. It is development and CI mirror tooling rather than an installed mmdebstrap service, but any client that can reach it can choose the request target while it runs.

## Canonical records

- issue: #42
- source: `upstream/mmdebstrap/caching_proxy.py`
- imported blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- candidate: `0001-confine-cache-paths.patch`
- regression: `tests/test_mmdebstrap_caching_proxy_containment.py`
- reusable note: `notes/filesystems/url-cache-keys-must-not-be-filesystem-paths.md`

## Exact source boundary

The unmodified handler performs:

```python
sanitizedpath = urllib.parse.unquote(self.path.removeprefix(pathprefix))
oldpath = oldcachedir / sanitizedpath
newpath = newcachedir / sanitizedpath
```

A decoded leading slash causes `pathlib` to discard the cache root. A decoded `..` component walks out of it. An existing symlink beneath the cache can redirect the later `mkdir`, read, or write operation.

The first cache-hit branch serves any existing path before the `.deb`/`by-hash` restriction, so an absolute request target can read an arbitrary file allowed by the proxy process's credentials. The download branch can write origin-controlled bytes to an arbitrary writable path.

`main()` creates `ThreadingHTTPServer(("", 8080), ...)`, exposing that request surface on all interfaces.

## End-to-end negative controls

The regression imports the exact unmodified helper and runs real loopback origin and proxy servers on ephemeral ports.

It requires the baseline to reproduce:

1. **absolute write escape** — an origin response is written to an absolute path outside `newcachedir`;
2. **encoded traversal write** — `%2e%2e/escaped` writes beside the cache root;
3. **absolute read escape** — an existing outside file is returned as an HTTP 200 cache hit;
4. **symlink escape** — `newcachedir/link -> outside` redirects the downloaded file.

All outside paths remain inside a disposable `TemporaryDirectory`; the test never targets a persistent host path.

## Candidate

The retained patch:

- parses the absolute request URI with `urllib.parse.urlsplit()`;
- compares normalized DNS hostname plus effective HTTP port with the `Host` authority, while rejecting credentials or extra authority syntax;
- inspects decoded slash-separated components before `PurePosixPath` can normalize them;
- rejects queries, fragments, empty paths, encoded slash/backslash, NULs, doubled or trailing separators, and literal or encoded `.`/`..` components;
- resolves each candidate against the cache root and requires `candidate.is_relative_to(root)`;
- rejects an existing symlink that resolves outside the cache;
- returns HTTP 400 rather than relying on assertions for malformed request structure;
- binds the standalone helper to `127.0.0.1` only.

A normal Debian pool request remains a 200 response and is cached at the same relative path. A request-target hostname and `Host` hostname that differ only by ASCII case are accepted with the same effective port.

The regression also requires literal dot, encoded dot, doubled-separator, and trailing-separator aliases to be rejected before any origin request or cache descendant is created.

## Severity and exposure

**Medium-high for the helper, approximately 7/10; lower for the installed package as a whole.**

The primitive permits arbitrary read of existing files and arbitrary write of origin-controlled bytes within the helper process's permissions. The all-interface bind increases reachability. The helper is not installed as the default mmdebstrap command or service; it is used by mirror generation, coverage, and autopkgtest workflows.

## Evidence limits

- Linux/POSIX pathname semantics only.
- The regression covers literal absolute paths, encoded dot segments, cache-key alias components, and an existing symlink escape.
- The `resolve()` check closes the demonstrated paths but is not a same-UID adversarial race-proof `openat(2)` sandbox. A process that can replace cache path components between validation and open remains outside this candidate.
- The proxy intentionally permits local HTTP forwarding; SSRF policy is not changed here.
- No external network or privileged port is used by the regression.

## Cleanup and rerun

Every server runs on loopback with an ephemeral port. Context managers call `shutdown()`, `server_close()`, and join the serving thread. Temporary roots are deleted by `TemporaryDirectory`. A legitimate request is executed through both baseline and candidate as a compatibility control.

## Disposition

Retain the candidate and executable regression for internal review. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created.
