# caching_proxy origin status validation under optimized Python

## In simple words

The proxy used `assert` to require an origin `200 OK`. Python removes assertions under `-O` or `PYTHONOPTIMIZE`, so an origin 404 could become downstream 200 and be stored in the shared cache.

This candidate replaces the assertion with an explicit status-code check that survives optimization.

## Canonical records

- Issue: #168
- Imported source: `upstream/mmdebstrap/caching_proxy.py`
- Candidate patch: `0001-check-origin-status-at-runtime.patch`
- Subprocess probe: `run_case.py`
- Regression: `tests/test_caching_proxy_origin_status.py`

## Source boundary

The fresh-download path currently does:

```python
res = conn.getresponse()
assert (res.status, res.reason) == (200, "OK"), (res.status, res.reason)
self.wfile.write(b"HTTP/1.1 200 OK\r\n")
```

With ordinary bytecode, a non-200 response raises and reaches the existing 502 path. With optimized bytecode, execution continues, sends a fresh 200 status, streams the error body, and writes that body to the cache.

## Candidate

```python
if res.status != 200:
    raise http.client.HTTPException(
        f"unexpected upstream response: {res.status} {res.reason}"
    )
```

Only the status code is normative here. A 200 response with a custom reason phrase remains successful; requiring the English text `OK` is unnecessarily strict.

## Negative and candidate matrix

The regression creates exact temporary baseline and candidate source copies, then launches the complete origin/proxy/client case in a separate interpreter. Optimized cases use the real `python -O` switch so the negative control actually executes assertion-free bytecode.

Two requests are sent to one URL:

- optimized baseline + origin 404: origin is contacted once, both downstream responses are 200, and the 404 body is retained in cache;
- candidate + origin 404, normal and optimized: origin is contacted twice, both responses are 502, and no final or temporary cache object exists;
- non-optimized baseline + origin 404: remains the 502 control;
- candidate + origin 200 with reason `Mirror Success`, normal and optimized: origin is contacted once, both downstream bodies and the cache match exactly.

The repeated 404 request proves the rejected response was not silently retained for a later cache hit.

## Cleanup and safety

Every case runs below `TemporaryDirectory`. Origin and proxy bind loopback ephemeral ports, shut down, close, and join inside the subprocess before JSON is returned. No external network, root privilege, package mutation, mount, or persistent cache is used.

## Composition boundary

The explicit status check occurs before downstream commitment and belongs in the canonical cache stack. It should compose with atomic publication, response framing, declared-length validation, and post-header error handling. The stack gate should eventually assert that no canonical source state contains the origin-status assertion.

This issue is distinct from request-side assertion removal in #150 / PR #94: #168 validates the response received from the origin.

## Disposition

Retain the focused patch and optimized-interpreter regression. No Debian or external upstream contact is included or authorized.
