# HTTP errors cannot replace a committed response

## Principle

An HTTP status is meaningful only before response bytes are committed. After a server has written a status line or headers, calling a generic `send_error()` routine cannot change the response already seen by the client.

At best, the extra bytes are ignored. At worst, a second status line and error document become part of the first response body or create ambiguous framing on a persistent connection.

## Safe error boundary

Track whether commitment may have begun.

- Before commitment, send the intended error status and body normally.
- Mark commitment before the first response write, not after it, because a failed write may have transmitted an unknown prefix.
- After commitment, log the original exception, stop writing body data, and close the downstream connection.
- Do not append another status line or HTML error response.
- Independently ensure partial cache or output state is not published as complete.

This is conservative by design. Losing a pre-commit 502 when the first status write failed before transmitting any bytes is less harmful than risking a second response after a partial write.

## Cache-proxy example

A streaming proxy can commit `200 OK`, then fail while:

- reading the origin;
- writing a cache candidate;
- writing the downstream body;
- validating a declared length;
- flushing final bytes.

Cache integrity and first-client signaling are different contracts. Atomic publication can correctly remove the failed cache candidate while the handler still corrupts the first response by appending `502 Bad Gateway` after a body prefix.

## Regression shape

Use raw downstream sockets because high-level clients may hide a second status line or reinterpret body framing.

A useful matrix proves:

1. a pre-commit failure produces one error response;
2. a post-header failure produces no second status;
3. a post-prefix failure preserves only the original committed response bytes;
4. downstream disconnect does not trigger a second response attempt;
5. cache-writer failure leaves no final or temporary object;
6. the original exception remains visible in stderr or structured logs;
7. every server, socket, and temporary path is reaped.

## Limits

Closing after commitment cannot tell the first client a new status. The client observes truncation, a framing error, or connection close according to the original response metadata. Avoiding early commitment or buffering the complete object is a separate design choice with different latency and memory tradeoffs.

## Source

Issue #132 and `investigations/caching-proxy-post-commit-errors/README.md` retain the mmdebstrap helper example. No upstream contact is authorized or made by this note.
