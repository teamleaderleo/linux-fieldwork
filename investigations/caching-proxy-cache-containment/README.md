# caching_proxy cache-root containment

## In simple words

The cache proxy decodes the URL suffix and joins it directly to its cache directories. Encoded absolute paths, parent traversal, existing symlinks, and normalized path aliases can therefore leave the cache root or make distinct request targets share one cache key.

The proxy also listens on every interface even though `make_mirror.sh` configures only `127.0.0.1:8080` as its consumer.

## Canonical records

- Security issue: #93
- Imported source: `upstream/mmdebstrap/caching_proxy.py`
- Consumer: `upstream/mmdebstrap/make_mirror.sh`
- Candidate patch: `0001-contain-cache-paths.patch`
- Regression: `tests/test_caching_proxy_cache_containment.py`
- Reusable note: `notes/security/url-paths-must-be-contained-before-cache-io.md`

## Confirmed baseline behavior

The executable negative control starts the imported handler as a real threaded HTTP proxy on an ephemeral loopback port.

### Outside read

A file outside both cache roots contains `TOP-SECRET`. A proxy request with the percent-encoded absolute filename receives HTTP 200 and the outside bytes through the `newpath.exists()` cache-hit branch.

### Outside write

A local upstream returns `ATTACKER-CONTROLLED`. A request whose decoded cache suffix is an absolute outside filename receives the upstream body, and the imported proxy creates that outside file with the same bytes as the proxy process user.

The write is not a privilege escalation beyond that account. It is a filesystem-boundary escape within the proxy's existing permissions.

## Candidate

`cache_path()`:

1. parses the complete absolute-form proxy target and the `Host` authority;
2. compares normalized DNS hostnames and effective HTTP ports while rejecting credentials, query, and fragment data;
3. rejects encoded path separators before decoding;
4. splits the decoded path before pathname normalization and rejects empty, `.`, and `..` components, including doubled and trailing separators;
5. constructs the relative path only after those checks;
6. resolves the cache root and candidate;
7. requires the candidate to remain below the resolved root, catching existing symlink escapes.

The handler returns HTTP 400 before mkdir, open, cache lookup, or upstream contact when validation fails. The production server binds to `127.0.0.1` instead of all interfaces.

Hostname comparison remains compatible with DNS case-insensitivity: `LOCALHOST:port` and `localhost:port` are accepted when their effective ports match.

## Regression matrix

The regression requires:

- baseline encoded absolute read succeeds outside the cache;
- baseline encoded absolute write creates outside bytes;
- candidate absolute, plain `../`, encoded `../`, and symlink escapes return HTTP 400;
- literal dot, encoded dot, doubled-separator, and trailing-separator aliases return HTTP 400;
- rejected aliases make zero upstream requests and create no cache descendants;
- invalid outside-write requests make zero upstream requests and create no file;
- case-insensitive hostname authority preserves a valid fresh download and cache layout;
- valid `.deb` cache hits still return their original bytes;
- readonly mode applies the same containment check;
- candidate source compiles and the production bind is loopback-only;
- all local servers shut down and join.

## Evidence boundary

The reproducer proves the imported code's behavior locally. Network reachability varies by runner and namespace, so this record does not claim that an external client reached a historical CI instance.

The candidate closes the demonstrated lexical, absolute, alias, and existing-symlink paths. It does not claim descriptor-level protection against a same-user attacker racing symlink replacement between resolution and open.

Concurrent requests, atomic cache publication, response framing, and declared-length validation remain separate audit boundaries.

## Cleanup and safety

All HTTP servers use loopback ephemeral ports. Outside files are created only below a disposable `TemporaryDirectory`. Every server is shut down, closed, and joined. No external network, package operation, root privilege, mount, or persistent file is used.

## Disposition

Treat this as a high-priority internal security candidate. No Debian or external upstream contact is included or authorized.
