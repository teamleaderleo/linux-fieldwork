# HTTP errors after headers require connection close

## In simple words

An HTTP server can choose a status code only before it sends the response status line and headers. If streaming fails later, writing a second status line does not change the first response. It corrupts or extends the body.

## Stable rule

Track response commitment explicitly.

```text
before status/headers: send a normal error response
status/headers started: stop body output and close the connection
```

Do not call a generic `send_error()` helper after a successful response has started unless that helper is specifically designed for trailers or an application protocol layered above HTTP.

## Why a second response is wrong

A byte stream like this:

```text
HTTP/1.1 200 OK
Content-Length: 100

partial-object
HTTP/1.0 502 Bad Gateway
Content-Type: text/html

...
```

is not a 502 response. The client already accepted 200. Depending on framing, the later bytes may be:

- treated as object data;
- hidden behind an incomplete-read exception;
- parsed as a pipelined response even though no second request exists;
- discarded after a connection/protocol error.

None of those communicates the intended status reliably.

## Design checklist

1. Set a commitment flag immediately before the first status-line write.
2. Keep origin/setup errors separate from streaming errors where practical.
3. Before commitment, generate one complete error response.
4. After commitment, log the original exception and close.
5. Ensure cache or file publication is transactional so partial state is not retained.
6. Test raw bytes, not only a high-level client result.
7. Cover failures before headers, after headers, after a body prefix, and in local storage writes.

## Limits

Connection close can tell a client that the message ended abnormally only when framing or the client detects truncation. It cannot retroactively provide a new status. Stronger recovery needs a higher-level protocol, trailers understood by both sides, checksums, retries, or resumable transfer.

## Related record

- `investigations/caching-proxy-post-header-errors/README.md`
- Issue #132
