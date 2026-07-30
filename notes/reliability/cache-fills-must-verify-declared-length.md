# Cache fills must verify declared response length

## Principle

End-of-stream is not always proof of successful completion. Some HTTP client APIs return an empty read at premature EOF when the caller requests fixed-size chunks, even if the response declared a larger `Content-Length`.

A streaming cache that treats `b""` as unconditional success can publish a short object while the original client reports an incomplete response.

## Validation boundary

When an upstream response includes `Content-Length`:

1. parse the expected nonnegative byte count;
2. count every byte written to the cache candidate;
3. compare received and expected counts before publication;
4. fail the fill when they differ;
5. let atomic-publication cleanup remove the temporary file;
6. allow a later request to retry upstream.

Responses without `Content-Length` require their protocol's own framing. Do not reject them merely because no expected count exists.

## Why client-side failure is not enough

The downstream client may detect that it received fewer bytes than the forwarded `Content-Length`, but the proxy can still believe its read loop completed successfully and retain the short cache.

The next request then receives a self-consistent short response based on the cached file's actual size. That hides the original failure and prevents recovery from an upstream that would succeed on retry.

## Composition with atomic publication

Length validation should occur while writing the temporary cache candidate and before the context publishes the final name. Raising after publication is too late.

Atomic publication without length validation can atomically publish the wrong complete state: a short file. Length validation without atomic publication can still expose partial bytes to concurrent readers. Both boundaries are required.

## Regression shape

Use an upstream that:

- declares a two-chunk `Content-Length`;
- sends only the first chunk on request one and closes;
- sends the complete object on request two.

The negative control should prove:

- client one detects incompleteness;
- a short cache file is retained;
- client two gets that short cache under HTTP 200;
- upstream request count stays at one.

The candidate should prove:

- client one remains incomplete;
- no final or temporary cache survives;
- client two reaches upstream;
- client two receives and publishes the complete object;
- responses without `Content-Length` still pass.

## mmdebstrap example

`caching_proxy.py` reads upstream responses in 64 KiB chunks. Issue #101 records that fixed-size `HTTPResponse.read()` can return EOF without raising on a short declared response, and the stacked candidate validates byte counts before the atomic writer publishes.
