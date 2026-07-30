# URL-derived paths must be contained before cache I/O

## Principle

URL decoding is not path sanitization. A decoded request component can become:

- an absolute filesystem path;
- a parent traversal using `..`;
- a path through an existing symlink that leaves the intended root;
- a cache-key alias after a path library removes `.` or trailing separators.

Joining untrusted text with `root / value` is unsafe when `value` can be absolute: `pathlib` and ordinary path libraries discard the root in that case.

## Safe boundary

Before any directory creation, existence check, open, cache lookup, or upstream request:

1. parse the request target as a URL and validate its scheme and authority;
2. compare DNS hostnames case-insensitively and effective ports rather than requiring byte-identical authority spelling;
3. reject credentials and unexpected query or fragment data;
4. reject encoded separators, then decode exactly once;
5. split the decoded path on `/` before constructing a normalized path object;
6. reject empty, `.`, and `..` components, including doubled and trailing separators;
7. construct the relative path only after those checks;
8. resolve the candidate against the resolved root;
9. require the candidate to remain below that root;
10. reject the request with a client error when validation fails.

Path libraries may erase evidence before validation. For example, `PurePosixPath("a/./b/").parts` no longer contains the literal dot or trailing separator. If the origin does not guarantee those request targets are equivalent, validating only normalized parts allows cache-key aliasing.

Resolving the candidate also catches existing symlinks below the cache that point outside. It does not eliminate every time-of-check/time-of-use race against a same-user attacker who can replace path components concurrently; stronger adversarial environments need descriptor-relative opens and no-follow controls.

## Read and write must share the same guard

Apply containment before both cache roots are consulted. A readonly mode is not safe when it checks an escaped path for existence and serves it before redirecting later writes to `/dev/null`.

Similarly, reject invalid paths before contacting an upstream server. Otherwise an attacker can use a successful upstream response as the bytes for an arbitrary file write under the proxy account.

## Exposure reduction

A helper intended only for local package tooling should bind to loopback unless remote clients are a stated requirement. Loopback binding is defense in depth; it does not replace path containment because local untrusted processes may still reach the service.

## Regression shape

Use a real local proxy and upstream server to prove:

- an encoded absolute path cannot disclose an outside file;
- an encoded absolute destination cannot create an outside file;
- plain and encoded `..` are rejected;
- literal and encoded `.` components are rejected;
- doubled and trailing separators do not reach origin or create cache descendants;
- an existing cache symlink cannot escape the root;
- invalid requests do not reach the upstream;
- equivalent hostname case and effective port remain compatible;
- valid cache hits still work;
- readonly mode applies the same guard;
- the production server binds only to loopback.

## mmdebstrap example

`caching_proxy.py` historically decoded the request suffix and joined it directly to `oldcachedir` and `newcachedir`, while listening on every interface. Issue #93 records confirmed outside-file read and write reproducers and the bounded containment candidate.
