# URL-derived paths must be contained before cache I/O

## Principle

URL decoding is not path sanitization. A decoded request component can become:

- an absolute filesystem path;
- a parent traversal using `..`;
- a path through an existing symlink that leaves the intended root.

Joining untrusted text with `root / value` is unsafe when `value` can be absolute: `pathlib` and ordinary path libraries discard the root in that case.

## Safe boundary

Before any directory creation, existence check, open, cache lookup, or upstream request:

1. decode exactly once;
2. parse with the URL's path semantics rather than the host platform's user-input assumptions;
3. reject empty, absolute, and parent-traversing paths;
4. resolve the candidate against the resolved root;
5. require the candidate to remain below that root;
6. reject the request with a client error when containment fails.

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
- an existing cache symlink cannot escape the root;
- invalid requests do not reach the upstream;
- valid cache hits still work;
- readonly mode applies the same guard;
- the production server binds only to loopback.

## mmdebstrap example

`caching_proxy.py` historically decoded the request suffix and joined it directly to `oldcachedir` and `newcachedir`, while listening on every interface. Issue #93 records confirmed outside-file read and write reproducers and the bounded containment candidate.
