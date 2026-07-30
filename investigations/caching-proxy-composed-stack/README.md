# caching_proxy canonical repair stack

## In simple words

The repository had three independently green fixes for the same `caching_proxy.py` fresh-download path: atomic cache publication, downstream framing cleanup, and declared-length validation. They did not compose automatically because their retained diffs overlap. This investigation defines one exact composed source state and runs the important behaviors together.

## Canonical records

- Integration issue: #145
- Atomic publication: #95 / merged PR #96
- Downstream framing: #116 / merged PR #120
- Declared-length validation: #101 / PR #137
- Imported source: `upstream/mmdebstrap/caching_proxy.py`
- Composer: `compose.py`
- Regression: `tests/test_caching_proxy_composed_stack.py`

## Composition order

1. Apply the permission-preserving atomic publication patch from PR #96.
2. Add the downstream hop-by-hop/framing helper from PR #120 to that source.
3. Add declared-length validation from PR #137 to the same fresh-download loop.
4. Resolve one semantic integration point: an upstream `Content-Length` that accompanies `Transfer-Encoding: chunked` does not describe the decoded bytes returned by `http.client`, so the composed source validates declared length only for non-chunked responses.

The composer verifies that all three canonical patch artifacts still contain their defining mechanisms before producing the candidate. Exact replacement anchors make source drift fail loudly instead of silently dropping a repair.

## Combined behavior

The composed candidate requires:

- both old-cache-copy and fresh-download fills to use atomic temporary destinations;
- cache files to retain the baseline `0666 & umask` creation contract;
- fixed-length bodies and end-to-end headers to survive;
- hop-by-hop and connection-token headers to be removed;
- decoded chunked bodies to be close-delimited without a conflicting length;
- premature EOF under a real declared length to publish neither final nor temporary cache state;
- a retry after the failed fill to reach upstream and publish a complete object.

## Negative integration finding

The isolated declared-length candidate reads `Content-Length` unconditionally. The isolated framing candidate intentionally permits a chunked response with conflicting `Content-Length` by removing that field after dechunking. Directly combining those mechanisms would reject a response that the framing repair was designed to normalize. The composed source therefore sets the expected byte count to `None` when `HTTPResponse.chunked` is true.

This is a real semantic conflict, not only a patch-hunk conflict.

## Validation

Run:

```sh
python3 -m unittest tests.test_caching_proxy_composed_stack -v
```

The repository CI discovery command also runs this test.

## Cleanup and safety

All servers bind loopback ephemeral ports. Candidate source, cache roots, origin state, and temporary files live below `TemporaryDirectory`. Every HTTP server is shut down, closed, and joined. No package installation, root privilege, mount, external network, or persistent cache is used.

## Evidence boundary

This stack composes only atomic publication, response framing, and declared-length validation. Cache-root containment (#93 / PR #94), request-header sanitization (#127 / PR #139), post-header error behavior (#132), descriptor-level path-race protection, request coalescing, fsync durability, and checksum validation remain separate boundaries until their own carriers are proven and added deliberately.

## Disposition

Use this composer and regression as the merge gate for the three canonical repairs. A later upstream packet should be generated from the composed source state rather than concatenating the isolated diffs. No Debian or external upstream contact is included or authorized.
