# Proxies must normalize framing after decoding

## In simple words

An HTTP client library can remove transfer framing before returning body bytes. A proxy must not forward the old framing headers unchanged after that transformation. The downstream headers must describe the bytes the proxy actually sends.

## What I learned

`Transfer-Encoding: chunked` describes a wire representation, not the logical payload. A client such as Python's `http.client.HTTPResponse` consumes the chunk sizes, separators, terminal chunk, and trailers. Its `read()` method returns decoded payload bytes.

If a proxy forwards the upstream `Transfer-Encoding: chunked` header but writes those decoded bytes directly, the downstream client tries to parse ordinary payload as chunk sizes. The cache may still contain the correct decoded object, so later cache hits can appear healthy while the first streamed response was malformed.

Hop-by-hop headers are also connection-specific. They must not be copied as ordinary end-to-end metadata. Header names are case-insensitive, and a `Connection` field can name additional fields that apply only to that hop.

## Do

- Determine whether the HTTP library returns framed bytes or decoded payload bytes.
- Remove `Transfer-Encoding` after de-chunking.
- Treat header names case-insensitively.
- Remove standard hop-by-hop fields.
- Parse `Connection` tokens and remove the fields they name.
- Suppress a conflicting `Content-Length` when chunk framing owned the upstream message.
- Choose valid downstream framing: a correct length, new chunk framing, or explicit connection-close delimiting.
- Test exact raw headers and bytes, not only cache contents.
- Include a real protocol client as a control.

## Do not

- Do not assume `getheaders()` and `read()` describe the same representation.
- Do not compare header names with case-sensitive string equality.
- Do not forward `Connection: keep-alive` while intending to close the response.
- Do not treat a correct cache file as proof that the first client received a valid response.
- Do not forward a `Content-Length` that belongs to a different framing interpretation.
- Do not claim trailer preservation when the client library consumed or discarded trailers.

## 🍩 Donut to avoid

**Correct cache, malformed first response:** the proxy stores the decoded payload correctly, but the downstream response still advertises the removed transfer framing. The outside looks successful because the cache and later requests work; the hole is the first client's wire contract.

## Example

Upstream wire response:

```text
HTTP/1.1 200 OK
Transfer-Encoding: chunked

7
payload
0

```

Decoded body returned by the client library:

```text
payload
```

Invalid downstream combination:

```text
Transfer-Encoding: chunked

payload
```

Valid downstream choices include re-chunking the payload or removing `Transfer-Encoding` and using a correct length or connection-close framing.

## Validation

The Linux Fieldwork regression under `tests/test_caching_proxy_hop_by_hop_framing.py` uses a real local chunked upstream, a raw downstream capture, a real `http.client` downstream control, fixed-length behavior, cache verification, and clean server shutdown.

## Environment and assumptions

The retained example concerns Python `http.client` behavior and the imported `mmdebstrap` cache proxy. The general rule applies to any proxy, gateway, middleware, or cache that changes a message representation between hops.

## Limits

This lesson does not choose one universal downstream framing strategy. Buffering, re-chunking, known-length streaming, and close delimiting have different latency, memory, retry, and error-signaling properties. It also does not solve errors discovered after headers have already been sent.

## Related work

- Related issue: #116.
- Related investigations: `investigations/caching-proxy-hop-by-hop-framing/`.
- Adjacent cache work: containment, atomic publication, and declared-length validation remain separate boundaries.
