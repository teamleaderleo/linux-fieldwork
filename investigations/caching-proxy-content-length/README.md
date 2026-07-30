# caching_proxy premature upstream EOF

## In simple words

The proxy reads upstream responses in fixed 64 KiB chunks and treats an empty read as successful completion. Python can return empty at premature EOF without raising even when the upstream declared more bytes in `Content-Length`.

That lets a transient short response become a persistent short cache.

## Canonical records

- Focused issue: #101
- Atomic-publication prerequisite: #95 / merged PR #96
- Imported source: `upstream/mmdebstrap/caching_proxy.py`
- Candidate patch: `0001-reject-short-upstream-responses.patch`
- Regression: `tests/test_caching_proxy_content_length.py`
- Reusable note: `notes/reliability/cache-fills-must-verify-declared-length.md`

## Negative control

The regression first applies the validated atomic-publication patch and uses that source as the baseline for this separate boundary.

A local upstream declares a 128 KiB response. On request one it sends only the first 64 KiB and closes. On request two it can send the complete object.

Atomic-only behavior:

1. client one receives HTTP 200 with the declared 128 KiB length and detects an incomplete body;
2. the proxy's fixed-size upstream read returns EOF without raising;
3. the proxy atomically publishes a 64 KiB cache file;
4. client two receives HTTP 200 with `Content-Length: 65536` and the short body;
5. the upstream request count remains one, so the recoverable complete second response is never requested.

## Candidate

For fresh upstream responses, the candidate records an integer `Content-Length` when present and counts every byte written. Before the atomic cache-writer context exits, it requires the received count to match the declared count.

A mismatch raises `http.client.IncompleteRead`. The atomic writer then removes its temporary file and does not publish the final name.

Responses without `Content-Length` retain their existing EOF-framed behavior.

## Candidate recovery matrix

With the same upstream:

- client one still detects an incomplete response;
- no final cache file survives;
- no temporary cache file survives;
- client two reaches the upstream, increasing the request count to two;
- client two receives the full 128 KiB body;
- the final cache contains the complete object;
- a response without `Content-Length` is still cached and returned successfully.

## Evidence boundary

The first client has already received HTTP 200 headers before a later length mismatch is known. This candidate protects cache integrity and retry behavior; it does not redesign downstream error signaling after response streaming has begun.

Only explicit `Content-Length` responses are byte-count validated. Chunked or connection-framed responses continue to rely on `http.client` framing behavior.

The candidate composes after atomic publication because length failure must occur before final-name publication. It does not include path containment or downstream framing changes.

## Cleanup and safety

All proxy and upstream servers use ephemeral loopback ports and are shut down, closed, and joined. Cache files live below a `TemporaryDirectory`. No external network, root privilege, package operation, or persistent state is used.

## Disposition

Retain the cache-integrity candidate. No Debian or external upstream contact is included or authorized.
