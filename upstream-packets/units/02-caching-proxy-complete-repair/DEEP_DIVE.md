# Deep dive

## Baseline mechanism

The imported handler trusts several protocol and filesystem transitions inside one `do_GET()` path:

1. Python assertions validate request body length, `Host`, and target prefix.
2. `urllib.parse.unquote()` turns the request path into a local pathname.
3. `pathlib` joins that result to old and new cache roots.
4. `dict(self.headers)` forwards the downstream header mapping to the origin.
5. A second assertion requires `(200, "OK")` from the origin.
6. Origin headers are copied downstream with only a lowercase-exact `connection` check.
7. The final cache filename is opened directly before receipt is complete.
8. Every exception calls `send_error(502)`, including exceptions after downstream success started.
9. The standalone server binds all interfaces.

Each shortcut becomes unsafe at a boundary where authority changes: client text to filesystem path, client headers to origin request, origin response to downstream response, and incomplete bytes to a shared cache entry.

## Demonstrated failures

### Request and path boundary

- `python -O` removes the request assertions.
- Absolute and traversal-like request paths can escape lexical cache joining.
- Decoding before selecting a cache key aliases request targets the origin can distinguish.
- Existing symlink components can redirect a resolved candidate outside the cache root.
- Duplicate or malformed framing fields can bypass the intended bodyless request contract.

### Origin request boundary

- `Proxy-Authorization` and `Proxy-Connection` cross to the selected origin.
- Standard hop-by-hop fields and fields nominated by `Connection` cross the hop.
- `dict(self.headers)` collapses repeated end-to-end fields.

### Origin response boundary

- `python -O` removes the origin status assertion, so an origin 404 can become downstream 200 and a persistent cache entry.
- Invalid or short declared lengths can become successful cache entries without explicit validation.
- Arbitrary transfer codings cannot safely be forwarded after Python's HTTP client handling.
- Hop-by-hop response fields can cross downstream.

### Publication and late-error boundary

- Direct final-name writes expose a partial cache object to concurrent readers.
- Premature EOF can leave a short final entry.
- A post-commit exception calls `send_error(502)`, appending a second response inside the first response stream.

## Selected composition

The PR #198 composer uses semantic anchors instead of applying every focused patch mechanically. This is required because the focused diffs overlap and one interaction changes behavior:

- Python `http.client` dechunks exact chunked responses.
- Downstream framing normalization removes a conflicting origin `Content-Length` for chunked responses.
- Declared-length validation therefore runs only when `HTTPResponse.chunked` is false.
- Non-chunked responses retain strict ASCII-decimal length parsing and exact byte-count validation.
- Transfer coding accepts only exact `chunked` when the client reports a decoded chunked response; compound or other codings fail before downstream commitment.

The final ordering is:

1. reject unsupported methods;
2. reject ambiguous or non-bodyless request framing;
3. parse absolute target and `Host` independently;
4. require matching host and effective port;
5. validate the raw path and resolve strict cache descendants;
6. sanitize origin request headers;
7. choose cache-hit or fresh-download path;
8. contact the origin and validate status/framing;
9. prepare normalized downstream headers;
10. mark response commitment before the first success write;
11. stream to downstream and an exclusive hidden cache temporary;
12. require complete receipt when a length exists;
13. atomically replace the final pathname;
14. close origin connection in `finally`;
15. send 502 before commitment or log-and-close after commitment.

## Alternatives rejected

### Mechanical patch stacking

Rejected because the focused patches replace adjacent or identical anchors. It also mishandles chunked responses by combining mutually incompatible assumptions about `Content-Length`.

### Keep assertions and add tests

Rejected because optimized Python removes assertion bytecode. Runtime input and protocol checks require ordinary conditional code.

### Decode percent escapes and normalize

Rejected for this narrow helper because partial decoding creates cache-key aliases and invalid-byte ambiguities. The selected policy rejects all percent escapes and accepts only the raw Debian archive path subset proven by tests.

### Write directly to the final cache name

Rejected because concurrent readers can observe incomplete bytes and interrupted fills can persist as valid-looking entries.

### Send a second 502 after a 200 begins

Rejected because the status has already committed. The only faithful response is to preserve the original error in logs, close the downstream connection, and leave no cache publication.

### Fold issue #227 into this unit

Rejected because pathname replacement after validation requires descriptor-relative traversal or an equivalent stronger primitive. That work changes the implementation boundary, compatibility review, and test model. Unit 02 retains the proven pathname-level candidate.

## Current-upstream review

Observed on 2026-08-01:

- canonical repository: `josch/mmdebstrap` on Muffin Forgejo;
- branch: `main`;
- displayed head: `77ec9be5417ee44c96343d2347145585da1b1f94`, commit subject `Take hurdfiles on hurd-amd64 as well`, dated 2025-08-24;
- repository view attributes `caching_proxy.py` to `caching_proxy.py: add comment about not using shutil.copyfileobj()`, dated 2023-06-14;
- Debian 1.5.7 source exposes `caching_proxy.py` as a 4,439-byte executable file;
- Linux Fieldwork imported baseline is blob `e57a8516a0c76167894b05fc56be0e3165535488` and contains that same comment.

Interpretation: no visible upstream edit overlaps the imported handler after the internal composition baseline. A raw byte fetch from the exact Forgejo head failed through the current connector, so the packet records this as a strong lineage/size match and leaves exact byte equality as the first incomplete identity gate.

## Upstream overlap scan

The current Forgejo issue index showed six open issues. The visible titles cover initramfs cpio output, hook variable expansion, local package caching, Ubuntu eatmydata behavior, CI tooling, and an old key failure. No visible issue or pull-request title described the complete caching-proxy repair. This is a title/index scan, not proof that no private, unindexed, or differently worded work exists.

Before contact, repeat the issue and pull-request search on the exact send date with terms covering `caching_proxy`, proxy headers, traversal, atomic cache, incomplete response, and optimized Python.

## Compatibility analysis

### Preserved

- ordinary Debian archive HTTP URLs with raw slash-separated paths;
- case-insensitive hostname matching and default port 80 equivalence;
- fixed-length origin responses;
- exact chunked responses after `http.client` decoding;
- EOF-delimited responses;
- repeated safe end-to-end request fields;
- origin 200 responses with custom reason phrases;
- existing cache file permission behavior through mode `0o666` plus process umask;
- readonly `/dev/null` sink behavior;
- uncoalesced concurrent misses where each client receives complete bytes.

### Intentionally narrowed

- only GET is supported;
- request bodies are rejected;
- percent escapes, query, fragment, userinfo, empty/dot/dot-dot path components, doubled/trailing separators, literal backslash, and NUL are rejected;
- unsupported or compound transfer codings are rejected;
- listener binds loopback.

### Still open

- same-UID path-component replacement between validation and open/replace;
- crash durability across power loss;
- duplicated origin work on concurrent misses;
- authenticity and checksum policy;
- remote-service deployment requirements.

## Exact evidence consulted

- issue #397 and its durable packet protocol;
- issues #127, #132, #145, #168, #188, and #227;
- PRs #118, #139, #147, #162, #169, and #198;
- PR #198 changed-file inventory, discussion receipts, and merged investigation README;
- imported source blob `e57a8516a0c76167894b05fc56be0e3165535488`;
- complete composer blob `00e28cc925ced0c01d9c8e300e7c94515367ca19`;
- atomic-publication patch blob `4fe75d312ebb097f1b9d5fa27f9f6e8da61235c1`;
- canonical upstream repository view and Debian Sources 1.5.7 inventory.

## Unresolved questions

1. Does the exact upstream head produce Git blob `e57a8516a0c76167894b05fc56be0e3165535488` for `caching_proxy.py`?
2. Which upstream test location and naming convention will be preferred for a focused Python loopback matrix?
3. Should the source repair and full matrix land as one commit or two commits in one pull request?
4. Does a controlled Forgejo fork already exist under the repository owner's account?
5. Will upstream accept the narrow percent-escape policy, or request an injective escaped cache-key design?
