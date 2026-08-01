# Draft upstream pull request

## Title

`caching_proxy: validate requests and publish complete responses atomically`

## Body

### Summary

This change repairs the complete `caching_proxy.py` request-to-cache lifecycle.

The handler now validates bodyless absolute-form GET requests and authority before cache or origin work, confines accepted cache paths, removes proxy-only and hop-by-hop request fields, validates the origin response before downstream commitment, publishes cache entries through exclusive hidden temporary files, and closes cleanly after late streaming failures.

### Problem

The previous handler combined several friendly-input assumptions:

- request and origin-status checks used `assert`, which disappears under `python -O`;
- the decoded request path became a filesystem path and cache key;
- downstream headers were converted to a dictionary and sent to the origin;
- the final cache name was opened before receipt completed;
- any exception called `send_error(502)`, even after a `200` had started.

Together, those behaviors could select an unintended cache path, alias distinct request targets, disclose proxy credentials to the origin, cache an origin error under optimized Python, expose a partial final cache entry, or append a second status inside a committed response.

### Changes

- reject unsupported methods and request bodies;
- require one `Host` and matching absolute-form authority;
- reject ambiguous targets and a narrow unsafe path set before side effects;
- require cache destinations to remain strict descendants of the configured roots;
- bind the standalone helper to `127.0.0.1`;
- preserve repeated end-to-end request fields while removing proxy and hop-by-hop fields;
- send one explicit origin-hop `Connection: close`;
- require origin status 200 with an ordinary runtime check;
- accept only supported response transfer coding;
- validate non-chunked declared length and exact receipt;
- remove downstream hop-by-hop response fields;
- create cache candidates with `O_EXCL` under hidden names and replace the final path after complete receipt;
- close origin connections in `finally`;
- send 502 only before downstream commitment;
- log and close after commitment without writing another response.

### Compatibility

The repair preserves successful fixed-length, exact chunked, and EOF-delimited downloads. It accepts case-insensitive hostnames with equivalent effective ports, decimal length spellings, repeated safe request fields, and 200 responses with custom reason phrases.

The accepted request-path subset deliberately rejects percent escapes, query, fragment, userinfo, backslash, NUL, empty components, dot components, doubled separators, and trailing separators. This keeps the cache key injective for the Debian archive paths covered by the helper’s tests.

### Tests

The focused loopback matrix covers:

- rejected request inputs with zero origin/cache activity;
- ordinary and optimized Python;
- absolute, traversal, symlink, and cache-key alias controls;
- exact origin request-header capture;
- origin non-200 responses;
- fixed-length, exact chunked, and EOF-delimited success;
- malformed, negative, and short declared lengths;
- unsupported transfer coding;
- atomic visibility under synchronized concurrent misses;
- premature EOF cleanup and retry;
- cache-writer, downstream, and origin-read failures;
- one-status behavior after commitment;
- file mode, temporary residue, connection, server, thread, socket, and process cleanup;
- clean rerun.

Exact commands and receipts will be inserted after the upstream candidate branch is built.

### Scope

This change leaves same-UID pathname replacement races, miss coalescing, crash-durable synchronization, checksums, remote deployment policy, and broader URI syntax for separate discussion.

## Receipt placeholders

```text
upstream base: 77ec9be5417ee44c96343d2347145585da1b1f94
candidate head: TO BE FILLED
caching_proxy.py baseline blob: TO BE VERIFIED
patch sha256: TO BE FILLED
focused test command: TO BE FILLED
focused test result: TO BE FILLED
optimized test result: TO BE FILLED
cleanup/rerun result: TO BE FILLED
```

## Pre-send checklist

- [ ] controlled fork and candidate branch recorded;
- [ ] exact upstream source blob verified;
- [ ] current overlap search repeated;
- [ ] generated patch retained and reviewed;
- [ ] upstream-native tests committed;
- [ ] exact-candidate gates and clean rerun passed;
- [ ] PR text updated with accomplished results;
- [ ] explicit external authorization recorded.

## Authority

Draft only. No public pull request, fork, branch, comment, review, email, or other upstream contact has been made.