# caching_proxy composed core repair stack

## In simple words

Several cache-proxy defects were proven and repaired in separate retained patches. Each patch was green by itself, but no source state carried the complete set. Their hunks overlap, and the declared-length repair conflicts semantically with chunked-response framing unless the stack explicitly gives transfer coding precedence.

This investigation provides one combined candidate and real-HTTP matrices for request-hop filtering, atomic publication, permission compatibility, response framing, and declared-length cache integrity.

## Existing work and duplicate search

- atomic final-name publication: #95 / merged PR #96;
- downstream response framing and hop headers: #116 / merged PR #120;
- request-side proxy credential and hop-header filtering: #127 / merged PR #139;
- declared-length validation: #101 / PR #103 and clean PR #137;
- integration owner: #145;
- cache-root containment and optimized-Python validation: #150 / PR #118, not yet included;
- post-header error signaling: #132 / PR #147, not yet included.

No existing test applied the merged request, atomic, and response repairs plus declared-length validation to one exact imported source.

## Source and stack map

The combined candidate starts from the unchanged imported `upstream/mmdebstrap/caching_proxy.py` and carries:

1. case-insensitive request hop-header and `Connection`-token filtering;
2. removal of `Proxy-Authorization` and `Proxy-Connection` before origin contact;
3. preservation of repeated safe end-to-end request fields through `raw_items()`;
4. duplicate-Host and `Connection: Host` rejection before origin contact;
5. permission-preserving exclusive sibling temporary files and atomic `os.replace()`;
6. the same atomic boundary for old-cache promotion and fresh downloads;
7. case-insensitive response hop-header and `Connection`-token filtering;
8. removal of upstream chunk framing after `http.client` decoding;
9. explicit downstream close delimiting;
10. received-byte validation for non-chunked responses with a declared length;
11. rejection of negative declared lengths before downstream commitment;
12. preservation of EOF-framed responses without `Content-Length`;
13. transfer-coding precedence: a `Content-Length` accompanying a chunked response is ignored for both downstream framing and cache-integrity counting.

## Negative integration finding

The isolated PR #103 candidate read `Content-Length` whenever present. PR #120's real chunked control deliberately includes `Transfer-Encoding: chunked` plus a conflicting `Content-Length: 999`.

A naïve composition would compare the decoded chunked payload with 999 and reject the valid response. The composed candidate validates declared length only when `HTTPResponse.chunked` is false.

The later merge of PR #139 created a second stack requirement: a core stack that omitted the already-merged request credential boundary would be obsolete even if its original response/cache tests stayed green.

## Executable matrix

`tests/test_caching_proxy_core_stack.py` and `tests/test_caching_proxy_core_stack_request_headers.py` apply the same combined patch to the exact imported source and start real loopback origin and proxy servers.

They require:

- fake proxy credentials and standard/token-named hop fields never to reach the origin;
- two repeated safe request fields, Host, Range, validators, and Accept to remain distinct and present;
- exactly one origin-hop `Connection: close`;
- duplicate Host to produce HTTP 400 with zero origin contact;
- two synchronized concurrent misses to keep the final name absent until complete;
- both clients to receive the complete object;
- final cache mode to equal the baseline `open("wb")` mode;
- no temporary siblings after success;
- a short fixed-length first response to publish no final or temporary object;
- a second request to reach the origin and recover with the complete object;
- a chunked response with conflicting length and hop headers to be accepted using transfer framing;
- no downstream chunked or conflicting length header after decoding;
- an EOF-framed response without declared length to remain cacheable;
- a negative declared length to return 502 before cache publication;
- retained end-to-end response headers and exact cache bytes;
- source compilation and presence of every merged core invariant.

## Evidence boundary

This stack proves one source state for request-hop filtering, atomic visibility, effective file mode, response framing, and fixed-length cache validation. It does not yet include:

- URL/authority/cache-root containment and optimized-Python behavior (#150 / PR #118);
- post-header error signaling (#132 / PR #147);
- miss coalescing;
- fsync crash durability;
- checksum or package-signature validation;
- descriptor-level symlink-race protection.

The first short downstream response can still be ambiguous after headers have started. This stack asserts cache integrity and retry recovery, not a repaired status code for that first client.

## Cleanup and rerun

All tests use fake credentials, ephemeral loopback ports, and disposable temporary roots. Servers close sockets and join threads. Temporary cache files are required to disappear. No external network, package mutation, privilege, mount, or persistent host state is used.

## Reusable note

See `notes/reliability/individually-green-patches-need-a-stack-gate.md`.

## Authority

Internal Linux Fieldwork integration candidate only. Imported source remains unchanged. No external contact is authorized or included.

## Next step

Run exact-head CI. If green, treat this composed source as the current core cache base, close or retarget superseded standalone length carriers, and add the separately proven containment and post-header-error boundaries through a later full-stack gate.
