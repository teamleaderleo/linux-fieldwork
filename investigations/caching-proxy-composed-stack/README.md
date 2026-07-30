# caching_proxy canonical repair stack

## In simple words

The repository had three independently green fixes for the same `caching_proxy.py` fresh-download path: atomic cache publication, downstream framing cleanup, and declared-length validation. They did not compose automatically because their retained diffs overlap. This investigation defines one exact composed source state and runs the important behaviors together.

## Canonical records

- Integration issue: #145
- Atomic publication: #95 / merged PR #96
- Downstream framing: #116 / merged PR #120
- Declared-length validation: #101 / merged PR #137
- Unsupported transfer codings: #173
- Imported source: `upstream/mmdebstrap/caching_proxy.py`
- Composer: `compose.py`
- Regressions:
  - `tests/test_caching_proxy_composed_stack.py`
  - `tests/test_caching_proxy_composed_stack_extended.py`
  - `tests/test_caching_proxy_content_length_grammar_stack.py`
  - `tests/test_caching_proxy_transfer_coding_rejection.py`

## Composition order

1. Apply the permission-preserving atomic publication patch from PR #96.
2. Add the downstream hop-by-hop/framing helper from PR #120 to that source.
3. Add declared-length validation from PR #137 to the same fresh-download loop.
4. Resolve one semantic integration point: an upstream `Content-Length` that accompanies `Transfer-Encoding: chunked` does not describe the decoded bytes returned by `http.client`, so the composed source validates declared length only for non-chunked responses.
5. Require a non-empty ASCII-decimal `Content-Length` before integer conversion. Python `http.client` accepts spellings such as `+5`; the composed gate rejects them before downstream commitment while retaining valid decimal spellings such as `05`.
6. Validate transfer codings before downstream commitment. Python `http.client` safely removes the ordinary, exactly-`chunked` framing used by the candidate; it does not decode arbitrary codings such as `gzip`, and compound chains such as `gzip, chunked` cannot be made correct by merely deleting the header. The composer rejects every unsupported or compound coding before cache publication.

The composer verifies that all three canonical patch artifacts still contain their defining mechanisms before producing the candidate. Exact replacement anchors make source drift fail loudly instead of silently dropping a repair.

## Combined behavior

The composed candidate requires:

- both old-cache-copy and fresh-download fills to use atomic temporary destinations;
- cache files to retain the baseline `0666 & umask` creation contract;
- fixed-length bodies and end-to-end headers to survive;
- hop-by-hop and connection-token headers to be removed;
- an exactly chunked body to be dechunked and close-delimited without a conflicting length;
- unsupported `gzip` and compound `gzip, chunked` transfer codings to fail with one pre-commit 502 and no cache state;
- malformed declared lengths such as `+5` to fail before commitment while ordinary ASCII decimal remains accepted;
- premature EOF under a real declared length to publish neither final nor temporary cache state;
- a retry after the failed fill to reach upstream and publish a complete object;
- EOF-framed responses without a declared length to remain supported.

## Negative integration findings

### Conflicting chunked length

The isolated declared-length candidate reads `Content-Length` unconditionally. The isolated framing candidate intentionally permits a chunked response with conflicting `Content-Length` by removing that field after dechunking. Directly combining those mechanisms would reject a response that the framing repair was designed to normalize. The composed source therefore sets the expected byte count to `None` when `HTTPResponse.chunked` is true.

### Unsupported transfer codings

The framing helper removes `Transfer-Encoding` because hop-by-hop metadata cannot be forwarded unchanged after a proxy transforms the message. That is correct only when the bytes have actually been decoded. `http.client` handles ordinary chunk framing, not arbitrary transfer codings. Stripping `gzip` from still-gzip bytes would silently misdescribe the representation, and a compound chain may leave framing or coding bytes intact. The composed source therefore accepts only the exact transfer-coding sequence it can prove was decoded: `chunked`.

### Raw-response assertion boundary

A raw-response regression originally counted every `HTTP/` substring and therefore treated the ordinary `Server: BaseHTTP/0.6 Python/...` header as a second status line. The corrected gate accepts one leading status and rejects only a later CRLF-prefixed `HTTP/` status line. Its source-order assertion also starts at the fresh-download `conn.getresponse()` anchor, so earlier cache-hit response writes do not create a false ordering failure.

These are semantic or evidence-composition conflicts, not only patch-hunk conflicts.

## Validation

Run:

```sh
python3 -m unittest \
  tests.test_caching_proxy_composed_stack \
  tests.test_caching_proxy_composed_stack_extended \
  tests.test_caching_proxy_content_length_grammar_stack \
  tests.test_caching_proxy_transfer_coding_rejection -v
```

The repository CI discovery command also runs these tests.

## Cleanup and safety

All servers bind loopback ephemeral ports. Candidate source, cache roots, origin state, and temporary files live below `TemporaryDirectory`. Every HTTP server is shut down, closed, and joined. No package installation, root privilege, mount, external network, or persistent cache is used.

## Evidence boundary

This stack composes only atomic publication, response framing, declared-length validation, and the transfer-coding acceptance boundary needed to make those three mechanisms correct together. Cache-root containment/request-target validation (#150 / PR #118), request-header sanitization (#127 / merged PR #139), post-header error behavior (#132 / PR #147), origin-status validation (#168 / PR #169), descriptor-level path-race protection, request coalescing, fsync durability, and checksum validation remain separate boundaries until their own carriers are proven and added deliberately.

## Disposition

Use this composer and regression as the merge gate for the canonical core repairs. Issue #188 owns the later full request/cache/response composition with the retained focused carriers. A later upstream packet should be generated from that deliberate composed source state rather than concatenating isolated diffs. No Debian or external upstream contact is included or authorized.
