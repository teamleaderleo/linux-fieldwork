# Complete caching-proxy composition

## Explain it like I am five

Imagine a mailroom that also keeps a copy of every parcel it delivers.

The old helper trusted the address written by the customer, used that same text as a shelf location, copied nearly every delivery instruction to the supplier, and wrote a new parcel directly onto the public shelf while it was still arriving.

That creates several ways to get the wrong result:

- a strange address can point outside the cache cabinet;
- a private proxy instruction can reach the supplier;
- a supplier's `404 Not Found` parcel can be relabelled as `200 OK` and cached;
- half a parcel can become visible as though it were complete;
- a broken response can contain one `200` followed by a second `502` status line.

This work makes the mailroom check the address, remove private delivery instructions, verify the supplier's answer, receive the full parcel into a hidden temporary location, and reveal it only after completion.

## Why should anyone care?

This helper sits in mmdebstrap development and CI workflows that fetch and cache Debian archive files. A bad cache entry can be served repeatedly, so one transient failure can become a persistent wrong answer. The demonstrated paths also let request text influence local file reads and writes within the helper process's permissions.

The exposure is bounded: this is a development/CI helper, and the candidate binds its standalone listener to loopback. The consequences inside that boundary remain concrete: incorrect package bytes, cached error pages, truncated downloads, leaked proxy credentials, confusing HTTP streams, and misleading test results.

## What happens if we leave it alone?

The focused fixes can each pass while the combined handler still fails. The overlaps occur in the same request path, so patch order can silently remove or bypass another repair.

Without one composed gate:

1. optimized Python can erase `assert` checks and accept requests or origin failures that ordinary Python rejects;
2. malformed or conflicting message lengths can reach downstream clients or the cache;
3. concurrent misses can observe a final cache name before the file is complete;
4. late failures can append a second HTTP response after the first one already began;
5. a retry can reuse corrupted cache state instead of recovering from the origin.

## Was the old behavior intentional?

The original file reads like a compact workflow helper written around friendly inputs: well-formed APT requests, a trusted local caller, ordinary Python, and a cooperative origin. Several individual choices were useful shortcuts in that setting.

The unsafe combination does not form a coherent product requirement. HTTP has long treated proxies as trust boundaries, Python documents that optimized mode removes assertions, and pathname-containment guidance treats canonicalization plus descendant checks as standard defensive practice.

A few restrictions in the candidate are deliberate design choices:

- the accepted URL-path language is narrower than general HTTP and rejects percent escapes because this Debian archive helper does not need them and decoding would create cache-key aliases;
- misses remain uncoalesced, so two clients may fetch the same object concurrently;
- the imported source remains preserved; the repository generates a candidate source for evidence and review.

## The proposed fix in plain terms

The generated handler follows one receiving checklist:

1. accept only the supported request method and bodyless request framing;
2. confirm that the absolute request URL and `Host` describe the same origin;
3. turn the accepted raw URL path into a cache path that remains below the cache root;
4. remove proxy credentials and connection-specific fields before contacting the origin;
5. require an origin status code of `200` with an ordinary runtime check;
6. understand the response framing before sending a downstream success status;
7. write response bytes to an exclusive hidden temporary file;
8. publish the final cache name with one rename after complete receipt;
9. send one `502` for failures before response commitment;
10. after commitment, log the original error and close the connection without writing a second response.

The result is still a small caching proxy. The fix adds checks at each boundary where text changes authority: URL to origin, URL to filesystem, origin response to downstream response, and incomplete file to shared cache entry.

## Historical and standards precedent

- HTTP/1.1 has required proxy requests to use an absolute-form target for decades. The current standard also requires a forwarding proxy to derive `Host` from that target: https://www.rfc-editor.org/rfc/rfc9112.html#name-absolute-form
- HTTP message framing rules require a proxy to reject an invalid upstream `Content-Length`, discard that response, and send `502`; an early close before the declared byte count makes the message incomplete: https://www.rfc-editor.org/rfc/rfc9112.html#name-message-body-length
- HTTP marks connection-specific fields as hop-by-hop and treats authority as critical routing data: https://www.rfc-editor.org/rfc/rfc9110.html#name-message-forwarding
- Python specifies that `python -O` emits no code for `assert` statements: https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement
- CWE-22 records the recurring pathname-traversal pattern and recommends canonicalization plus containment checks: https://cwe.mitre.org/data/definitions/22.html

These references show a long-running design lesson: proxies, caches, and filesystem adapters must validate again at their own boundary, even when an earlier caller usually supplies clean input.

## Owners and routing

- push packet: issue #194, Packet D
- integration owner: issue #188
- helper: D
- current integration branch: `integration/caching-proxy-complete-stack`
- pull request: #198
- exact validated head: `00caba3d753536dd9a3a68fc6f110c75e338ec08`
- external-contact authority: internal repository work only

## Source boundary

- imported source: `upstream/mmdebstrap/caching_proxy.py`
- imported blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- routing composer: `compose.py`
- retained implementation: `compose_impl.py`
- focused snapshots: `inputs/`
- optimized-interpreter runner: `run_case.py`
- full gate: `../../tests/test_caching_proxy_complete_stack.py`

The imported upstream file stays unchanged. Inputs already present on `main` are referenced directly. Reviewed mechanisms that still live on open focused branches are snapshotted under `inputs/` so the exact PR checkout carries every composition input.

## Executed gates

Local full-matrix runs:

```text
python3 -m unittest -v tests/test_caching_proxy_complete_stack.py
Ran 7 tests in 16.425s
OK

snapshot-packaging rerun:
Ran 7 tests in 15.297s
OK
```

Final current-main-aligned repository gate:

```text
head: 00caba3d753536dd9a3a68fc6f110c75e338ec08
workflow: Linux Fieldwork CI
run: 30578916643 / 572
result: success
```

The matrix covers rejected request inputs with zero origin/cache activity, request-header sanitization, ordinary and optimized Python, status and framing failures, complete fixed/chunked/EOF responses, premature EOF and retry, post-commit failures, cache-writer and downstream failures, concurrent misses, file mode, temporary cleanup, and server/thread/socket shutdown.

## Why this fix is narrow

The candidate preserves successful fixed-length, exactly chunked, and EOF-delimited downloads. It accepts a `200` with a custom reason phrase because the status code carries the protocol meaning. It rejects unsupported transfer-coding combinations before downstream commitment because Python's HTTP client does not supply a safely decoded representation for them.

The candidate intentionally leaves these separate questions open:

- pathname replacement between validation and file open by another same-UID process;
- miss coalescing;
- crash-durable file and directory synchronization;
- content checksums or authentication;
- remote deployment policy;
- broader URI syntax.

## Current disposition

`READY FOR FINAL HUMAN CHECK` at `00caba3d753536dd9a3a68fc6f110c75e338ec08`, with Linux Fieldwork CI run 572 successful.

The human decision is whether this nine-file internal evidence unit explains and proves the combined behavior well enough to merge. External submission remains a separate decision. No Debian or other external contact is included or authorized.