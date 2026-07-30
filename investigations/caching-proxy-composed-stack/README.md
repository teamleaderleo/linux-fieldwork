# caching_proxy canonical composed repair stack

## In simple words

The atomic-publication, downstream-framing, and declared-length repairs each passed alone, but all three edit the same fresh-download path. This investigation builds one exact candidate source and runs their behavior together so patch overlap cannot hide a semantic conflict.

## Existing work

- atomic publication: #95 / merged PR #96;
- downstream framing: #116 / merged PR #120;
- declared-length validation: #101 / merged PR #137;
- integration owner: #145;
- request-side headers: #127 / merged PR #139, intentionally outside this core stack;
- cache-root containment: #93 / PR #94, intentionally outside this core stack;
- committed-response failures: #132 / PR #154, stacked after this core source.

## Composition

`compose.py` starts from the unchanged imported `upstream/mmdebstrap/caching_proxy.py` and requires the canonical retained patch artifacts to contain their defining mechanisms.

It then produces one source state with:

1. permission-preserving exclusive same-directory temporary cache files;
2. atomic `os.replace()` publication for old-cache promotion and fresh fills;
3. case-insensitive response hop-header and `Connection`-token filtering;
4. decoded chunked response framing with conflicting `Content-Length` removed;
5. explicit downstream connection-close delimiting;
6. byte-count validation for non-chunked responses with declared length;
7. negative declared-length rejection before downstream commitment;
8. unchanged EOF framing for responses without `Content-Length`.

## Integration finding

A mechanical combination is wrong. The framing regression intentionally supplies both:

```text
Transfer-Encoding: chunked
Content-Length: 999
```

`http.client` returns decoded body bytes. Validating those decoded bytes against the conflicting `999` would reject a valid chunked response. The composed candidate therefore gives transfer coding precedence and validates `Content-Length` only when `response.chunked` is false.

## Executable matrix

`tests/test_caching_proxy_composed_stack.py` uses real loopback origin and proxy servers and requires:

- two synchronized misses keep the final cache name absent until both complete;
- both clients receive the full object;
- effective cache mode equals normal `open("wb")` creation under the current umask;
- no temporary siblings survive;
- a short fixed-length first response publishes nothing;
- a retry reaches origin and publishes the complete response;
- a chunked response with conflicting length and hop fields is decoded, filtered, returned, and cached correctly;
- an EOF-framed response without declared length remains returnable and cacheable;
- a negative declared length returns 502 before final or temporary publication;
- the generated source compiles and contains every required mechanism;
- every server closes and its thread joins.

## Evidence boundary

This stack proves the repository's core cache-fill composition only. It does not yet include:

- origin request-header sanitization already retained in merged PR #139;
- request-target/cache-root containment in PR #94;
- committed-response error handling in PR #154;
- miss coalescing;
- descriptor-level race protection;
- fsync crash durability;
- checksums or package-signature validation.

The first client can still observe a truncated 200 after a later short-body failure because the response was already committed. PR #154 owns that downstream error boundary.

## Cleanup and authority

All state is below disposable temporary directories and all sockets use ephemeral loopback ports. No privilege, package mutation, mount, external network, or persistent path is used.

Imported source remains unchanged. No Debian or external upstream contact is included or authorized.

## Disposition

Use this exact composed source as the canonical core cache-proxy gate. Later full-stack work should add request headers, containment, and post-commit handling to this source rather than concatenating stale diffs.
