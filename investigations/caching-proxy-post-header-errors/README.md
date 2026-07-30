# caching_proxy post-header error handling

## In simple words

The proxy can start a `200 OK` response, encounter a later stream or cache error, and then call `send_error(502)`. HTTP cannot replace a status after it has been sent, so the second status line and HTML error body are appended to the first response instead.

This candidate records whether the fresh response has started. Before commitment, failures still produce one normal 502. After commitment, failures are logged and the connection is closed without writing a second response.

## Canonical records

- Issue: #132
- Base integration stack: #145 / PR #162
- Imported source: `upstream/mmdebstrap/caching_proxy.py`
- Candidate composer: `compose.py`
- Regression: `tests/test_caching_proxy_post_header_errors.py`

## Source boundary

The fresh-download path currently has one broad exception handler around:

1. origin connection and status validation;
2. downstream status/header commitment;
3. body streaming;
4. atomic cache writing;
5. declared-length validation.

The composed base still ends that block with:

```python
except Exception:
    self.send_error(502)
```

That is correct only before any downstream response bytes have been committed.

## Candidate

The stacked source adds a local `response_started` state:

```python
response_started = False
...
response_started = True
self.wfile.write(b"HTTP/1.1 200 OK\r\n")
```

The exception path always records the original exception. It then:

- calls `send_error(502)` when the failure occurred before commitment;
- sets `close_connection` and returns when the 200 response had already started.

The flag is set before the first status-line write. A partial or failed status write is already unsafe to replace with another response, so the conservative action is connection close.

## Negative and candidate matrix

The raw-socket regression requires:

- the composed base to emit `200 OK` followed by a second `502 Bad Gateway` after a short declared upstream body;
- the candidate to emit only the original 200 response bytes for the same failure;
- atomic cleanup to leave no final or temporary cache object;
- a connection failure before commitment to produce exactly one normal 502;
- an injected cache-writer failure after headers to close without appending 502;
- stderr to retain the original `IncompleteRead`, connection refusal, or injected writer exception.

Raw capture is required because high-level clients can hide the second status line inside an incomplete body or raise before exposing it.

## Cleanup and safety

All origins and proxies bind loopback ephemeral ports. Every server is shut down, closed, and joined. Source copies, cache roots, and logs live under `TemporaryDirectory`. No external network, root privilege, package mutation, or persistent cache is used.

## Evidence boundary

Once a streaming response has begun, the proxy cannot truthfully communicate a new status code to that client. Closing the connection is the only remaining protocol signal. This candidate does not add trailers, resumable transfer, retry signaling to the first client, request coalescing, or application-level checksums.

The candidate is stacked on the atomic/framing/declared-length composition because cache cleanup and short-body detection are part of the failure path. It remains a separate semantic repair and should be added to the canonical stack only after this carrier is green.

## Disposition

Retain the candidate and raw regression. No Debian or external upstream contact is included or authorized.
