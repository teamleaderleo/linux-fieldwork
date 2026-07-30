# caching_proxy cache-root containment

## In simple words

The cache proxy decodes the URL suffix and joins it directly to its cache directories. Encoded absolute paths, parent traversal, or existing symlinks can therefore leave the cache root before a read or write.

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

1. URL-decodes once into a `PurePosixPath`;
2. rejects empty, absolute, and parent-traversing paths;
3. resolves the cache root and candidate;
4. requires the candidate to remain below the resolved root, catching existing symlink escapes.

The handler returns HTTP 400 before mkdir, open, cache lookup, or upstream contact when containment fails. The production server binds to `127.0.0.1` instead of all interfaces.

## Regression matrix

The regression requires:

- baseline encoded absolute read succeeds outside the cache;
- baseline encoded absolute write creates outside bytes;
- candidate absolute, plain `../`, encoded `../`, and symlink escapes return HTTP 400;
- invalid outside-write requests make zero upstream requests and create no file;
- valid `.deb` cache hits still return their original bytes;
- readonly mode applies the same containment check;
- candidate source compiles and the production bind is loopback-only;
- all local servers shut down and join.

## Evidence boundary

The reproducer proves the imported code's behavior locally. Network reachability varies by runner and namespace, so this record does not claim that an external client reached a historical CI instance.

The candidate closes lexical, absolute, and existing-symlink escape paths. It does not claim descriptor-level protection against a same-user attacker racing symlink replacement between resolution and open.

Concurrent requests and atomic cache publication remain a separate audit boundary.

## Cleanup and safety

All HTTP servers use loopback ephemeral ports. Outside files are created only below a disposable `TemporaryDirectory`. Every server is shut down, closed, and joined. No external network, package operation, root privilege, mount, or persistent file is used.

## Disposition

Treat this as a high-priority internal security candidate. No Debian or external upstream contact is included or authorized.
