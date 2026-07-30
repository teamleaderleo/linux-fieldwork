# caching_proxy errors after downstream response commitment

## In simple words

The fresh-download path writes `HTTP/1.1 200 OK`, forwards headers, and may stream part of the object before a later origin, downstream, or cache-write exception occurs. The imported handler catches every exception by calling `send_error(502)`.

After a response has started, that does not change the status. It appends a second HTTP response to the first response's body and can corrupt or ambiguate the bytes seen by the client.

## Canonical records

- Focused issue: #132
- Imported source: `upstream/mmdebstrap/caching_proxy.py`
- Atomic-publication prerequisite: merged PR #96
- Candidate patch: `0001-close-after-committed-response-errors.patch`
- Regression: `tests/test_caching_proxy_post_commit_errors.py`
- Reusable note: `notes/reliability/http-errors-cannot-replace-a-committed-response.md`

## Negative control

The executable regression first applies the retained atomic-publication patch and uses that source as the baseline. A scripted origin returns one body prefix and then raises.

A real raw downstream socket receives:

```text
HTTP/1.1 200 OK
...
BODY-PREFIX
HTTP/1.0 502 Bad Gateway
...
```

The cache temporary is removed, so cache integrity is preserved, but the first client's representation is still corrupted by a second status and HTML error body.

## Candidate

The candidate records whether downstream commitment has begun before writing the first 200 response byte.

- failures before commitment retain a normal 502 response;
- failures after commitment are logged to stderr;
- the connection is marked for close;
- no second status or error body is written;
- atomic-publication cleanup removes failed cache candidates.

The flag is set before the first status write. That is deliberately conservative: if the status write itself raises after writing an unknown prefix, the handler must not risk appending another response.

## Regression matrix

The raw-socket regression covers:

1. atomic-only baseline appending a second response after a body-prefix failure;
2. pre-commit connection failure returning one ordinary 502;
3. post-header origin-read failure returning only the committed 200 framing;
4. failure after a body prefix without a second status;
5. cache-writer open failure with no final or temporary cache object;
6. deterministic downstream disconnect after status and headers with no cache publication;
7. stderr retention of every injected failure and complete server/thread cleanup.

## Interpretation

A server cannot replace an HTTP response after bytes from that response may have reached the client. Once committed, the only safe generic recovery is to stop producing body bytes, close the connection, retain the failure in logs, and avoid publishing incomplete cache state.

The first client can still receive an incomplete 200 response. This candidate makes that limitation explicit; it does not claim to invent a new status after commitment.

## Evidence boundary

- The candidate composes after atomic publication so failed fills do not become final cache entries.
- Downstream framing normalization, declared-length validation, request-header filtering, and cache-path containment remain separate patches.
- The test uses scripted origin behavior but a real threaded proxy and raw downstream TCP sockets.
- No external network, privilege, package mutation, or persistent path is used.

## Disposition

Retain the committed-response boundary and compose it with the other cache-proxy repairs before a consolidated product patch. No Debian or external upstream contact is included or authorized.
