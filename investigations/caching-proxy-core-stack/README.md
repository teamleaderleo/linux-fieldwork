# caching_proxy composed core repair stack

## In simple words

Several cache-proxy defects were proven and repaired in separate retained patches. Each patch was green by itself, but no source state carried the complete set. Their hunks overlap, and the declared-length repair conflicts semantically with chunked-response framing unless the stack explicitly gives transfer coding precedence.

This investigation provides one combined candidate and one real-HTTP matrix for atomic publication, permission compatibility, response framing, and declared-length cache integrity.

## Existing work and duplicate search

- atomic final-name publication: #95 / merged PR #96;
- downstream response framing and hop headers: #116 / merged PR #120;
- declared-length validation: #101 / PR #103;
- integration owner: #145;
- request-side headers: #127 / PR #139, not yet included;
- cache-root containment: #93 / PR #94, not yet included;
- post-header error signaling: #132, not yet included.

No existing test applied the merged atomic and response fixes plus declared-length validation to one exact imported source.

## Source and stack map

The combined candidate starts from the unchanged imported `upstream/mmdebstrap/caching_proxy.py` and carries:

1. permission-preserving exclusive sibling temporary files and atomic `os.replace()`;
2. the same atomic boundary for old-cache promotion and fresh downloads;
3. case-insensitive response hop-header and Connection-token filtering;
4. removal of upstream chunk framing after `http.client` decoding;
5. explicit downstream close delimiting;
6. received-byte validation for non-chunked responses with a declared length;
7. transfer-coding precedence: a `Content-Length` accompanying a chunked response is ignored for both downstream framing and cache-integrity counting.

## Negative integration finding

The isolated PR #103 candidate read `Content-Length` whenever present. PR #120's real chunked control deliberately includes `Transfer-Encoding: chunked` plus a conflicting `Content-Length: 999`.

A naïve composition would compare the decoded chunked payload with 999 and reject the valid response. The composed candidate validates declared length only when `HTTPResponse.chunked` is false.

## Executable matrix

`tests/test_caching_proxy_core_stack.py` applies the single combined patch to the exact imported source and starts real loopback origin and proxy servers.

It requires:

- two synchronized concurrent misses to keep the final name absent until complete;
- both clients to receive the complete object;
- final cache mode to equal the baseline `open("wb")` mode;
- no temporary siblings after success;
- a short fixed-length first response to publish no final or temporary object;
- a second request to reach the origin and recover with the complete object;
- a chunked response with conflicting length and hop headers to be accepted using transfer framing;
- no downstream chunked or conflicting length header after decoding;
- retained end-to-end response headers and exact cache bytes;
- source compilation and presence of every merged core invariant.

## Evidence boundary

This stack proves one source state for atomic visibility, effective file mode, response framing, and fixed-length cache validation. It does not yet include:

- request-side proxy credential and hop-header filtering (#127 / PR #139);
- URL/cache-root containment (#93 / PR #94);
- post-header error signaling (#132);
- miss coalescing;
- fsync crash durability;
- checksum or package-signature validation;
- descriptor-level symlink-race protection.

The first short downstream response can still be ambiguous after headers have started. This stack asserts cache integrity and retry recovery, not a repaired status code for that first client.

## Cleanup and rerun

All tests use ephemeral loopback ports and disposable temporary roots. Servers close sockets and join threads. Temporary cache files are required to disappear. No external network, package mutation, privilege, mount, or persistent host state is used.

## Reusable note

See `notes/reliability/individually-green-patches-need-a-stack-gate.md`.

## Authority

Internal Linux Fieldwork integration candidate only. Imported source remains unchanged. No external contact is authorized or included.

## Next step

Run exact-head CI. If green, use this composed source as the base for restacking #103 and for adding the separately proven request-header, containment, and post-header-error boundaries.
