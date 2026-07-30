# Proxies must separate proxy and origin credentials

## In simple words

Credentials and connection controls sent to a proxy are not automatically intended for the origin server. A proxy must deliberately construct each hop's request instead of forwarding the complete downstream header set.

## What I learned

HTTP headers do not all have the same scope.

`Proxy-Authorization` authenticates the client to a proxy. Forwarding it to the origin exposes a credential to a server chosen by the request URL. `Connection`, `Keep-Alive`, `TE`, `Trailer`, `Transfer-Encoding`, `Upgrade`, and fields named by `Connection` describe one transport hop and must not cross into the next hop unchanged.

End-to-end fields such as `Host`, `Range`, conditional validators, and content negotiation often do need to reach the origin. Repeated end-to-end fields can also carry meaning, so converting a parsed header message to a dictionary can silently lose information.

## Do

- Build the origin request from an explicit header policy.
- Compare header names case-insensitively.
- Remove proxy credentials before origin contact.
- Remove standard hop-by-hop fields.
- Parse every `Connection` value and remove the fields its tokens name.
- Preserve exactly one valid Host field.
- Preserve repeated safe end-to-end fields when the client library permits it.
- Choose an explicit connection policy for the origin hop.
- Test what a real origin receives, not only what a helper returns.
- Use fake credentials and loopback-only fixtures.

## Do not

- Do not forward `dict(request.headers)` to an origin.
- Do not assume a proxy credential is harmless because the proxy itself is local.
- Do not compare `Connection` or `Proxy-Authorization` with case-sensitive spelling.
- Do not remove all authorization indiscriminately: origin `Authorization` and proxy `Proxy-Authorization` have different recipients.
- Do not preserve a field merely because it is not in a fixed standard list; `Connection` can name additional hop-specific fields.
- Do not collapse repeated safe fields without an explicit compatibility decision.

## 🍩 Donut to avoid

**Response-clean, request-leaky:** a proxy carefully normalizes origin response framing but still forwards the client's proxy credential and downstream connection controls to the origin. One direction is correct; the opposite direction has the security hole.

## Example

Downstream request to the proxy:

```text
Proxy-Authorization: Basic fake-proxy-secret
Connection: keep-alive, X-Hop
X-Hop: local-only
Range: bytes=0-1023
```

Origin request should retain the range but not the proxy credential or token-named field. It should use a connection policy selected by the proxy, not the downstream connection value.

## Validation

The Linux Fieldwork regression under `tests/test_caching_proxy_request_hop_headers.py` uses a raw downstream request and a real loopback origin that records exact mixed-case and repeated headers.

## Environment and assumptions

The retained example concerns Python `http.server`, `http.client`, and the imported `mmdebstrap` cache proxy. The principle applies to HTTP proxies, gateways, middleware, service meshes, and custom forwarding clients.

## Limits

This note does not define a complete policy for every HTTP extension, request method, request body, trailer, CONNECT tunnel, or authentication scheme. It also does not replace URL/authority validation or response-side hop normalization.

## Related work

- Canonical issue: #127.
- Investigation: `investigations/caching-proxy-request-hop-headers/`.
- Response-side framing: #116 / PR #120.
