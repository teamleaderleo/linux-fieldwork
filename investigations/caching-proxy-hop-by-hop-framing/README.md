# caching_proxy downstream framing and hop-by-hop headers

## In simple words

The cache proxy reads upstream HTTP through Python's `http.client`. That library removes chunk framing before returning body bytes. The imported proxy forwards the upstream `Transfer-Encoding: chunked` header anyway, so the downstream response can advertise chunk framing while sending plain decoded bytes.

This investigation retains a local real-HTTP negative control and a candidate that removes hop-by-hop framing headers, preserves end-to-end headers, and close-delimits fresh responses when no valid length remains.

## Existing work and duplicate search

- cache-root containment: issue #93 / PR #94;
- atomic final-name publication: issue #95 / PR #96;
- premature declared-length EOF: issue #101 / PR #103;
- canonical framing issue: #116;
- no existing issue or pull request covered de-chunked bodies with forwarded chunk headers or `Connection` token fields.

## Question

Can `caching_proxy.py` return a fresh chunked upstream response with downstream headers that match the actual decoded body bytes, while preserving fixed-length and end-to-end header behavior?

## Source

- Project: imported `mmdebstrap`;
- File: `upstream/mmdebstrap/caching_proxy.py`;
- Imported source remains unchanged;
- Candidate: `0001-normalize-downstream-framing.patch`;
- Exact candidate head and workflow receipt are recorded in the pull request after execution.

## Source and test map

Fresh-download flow:

1. create `http.client.HTTPConnection`;
2. receive `HTTPResponse`;
3. forward almost every result of `getheaders()`;
4. read the body through `HTTPResponse.read()`;
5. send those bytes to the first client and cache file.

`HTTPResponse.read()` decodes HTTP chunk framing. `getheaders()` still exposes the upstream `Transfer-Encoding` and ordinary case-preserved `Connection` fields. The imported comparison `if k == "connection"` does not match ordinary `Connection`.

The regression starts:

- a real local raw upstream server;
- the real imported or temporarily patched proxy handler on an ephemeral loopback port;
- a raw downstream client for exact header/body capture;
- Python `http.client` as a downstream protocol client for the candidate.

## Baseline negative control

The upstream sends:

- `Transfer-Encoding: chunked`;
- a conflicting `Content-Length`;
- `Connection: close, X-Hop`;
- `Keep-Alive`, `Trailer`, and `X-Hop` fields;
- a valid two-chunk body and trailer.

The imported proxy is required to reproduce:

- forwarded `Transfer-Encoding: chunked`;
- forwarded conflicting `Content-Length`;
- forwarded case-preserved `Connection` and other hop-by-hop fields;
- plain decoded payload bytes rather than chunk frames;
- a cache file containing the decoded payload.

The complete cache demonstrates why a later cache hit can hide the first-client framing failure.

## Candidate

The candidate:

- treats header names case-insensitively;
- removes `Connection`, `Keep-Alive`, proxy authentication fields, `Proxy-Connection`, `TE`, `Trailer`, `Transfer-Encoding`, and `Upgrade`;
- removes every field named by `Connection` tokens;
- suppresses `Content-Length` when upstream chunk framing owned the message;
- sends `Connection: close` and marks the handler connection for closure;
- preserves fixed-length `Content-Length` and end-to-end headers;
- leaves the decoded cache representation unchanged.

## Assertions

The candidate matrix requires:

- no downstream `Transfer-Encoding` for the decoded chunked body;
- no conflicting `Content-Length` for the chunked case;
- no forwarded standard or token-named hop-by-hop headers;
- explicit downstream close framing;
- byte-exact payload through a raw client and Python `http.client`;
- byte-exact cache contents;
- retained fixed-length `Content-Length` and end-to-end headers;
- clean shutdown and joined threads for every local server;
- exact patch application to the imported source.

## Interpretation boundary

This candidate repairs downstream framing and hop-by-hop header handling for fresh responses after `http.client` decoding. It does not:

- provide cache-root descriptor-level race protection;
- coalesce concurrent misses;
- preserve or forward upstream trailers;
- redesign error signaling after response headers have already been sent;
- add fsync durability;
- replace the independent atomic-publication or declared-length candidates.

## Cleanup and rerun

All servers bind to loopback ephemeral ports, run in disposable temporary directories, shut down explicitly, close their sockets, and join their threads. No external network, package, mount, privilege, or persistent host state is used.

## Reusable note

See `notes/reliability/proxies-must-normalize-framing-after-decoding.md`.

## Authority

Internal Linux Fieldwork candidate only. No external issue, email, merge request, patch submission, comment, or review is authorized or included.

## Next step

Run exact-head repository CI. If the baseline mismatch and candidate matrix pass, retain the fix as the canonical carrier for issue #116 and review composition with PRs #94, #96, and #103.
