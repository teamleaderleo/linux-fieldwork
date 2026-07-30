# Complete caching-proxy composition

## In simple words

The caching proxy repairs were developed as focused candidates that overlap in one request handler. This record builds one source file from the preserved imported `caching_proxy.py`, composes every active request, cache, response, and lifecycle mechanism deliberately, and runs them through one real loopback matrix.

The composed source remains generated evidence. The imported upstream file stays unchanged.

## Owners and routing

- push packet: issue #194, Packet D
- integration owner: issue #188
- helper: D
- first repository candidate commit: `1efaaece6bf58e78753978a1ef3c06bfa2c1d9ed`
- current integration branch: `integration/caching-proxy-complete-stack`
- external-contact authority: internal repository work only

## Source boundary

- base repository commit: `d344c942af4b55b5b0c71c8a66a8870fbf0db7bf`
- imported source: `upstream/mmdebstrap/caching_proxy.py`
- imported blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- composer: `compose.py`
- optimized-interpreter runner: `run_case.py`
- full gate: `../../tests/test_caching_proxy_complete_stack.py`

## Canonical inputs

The composer verifies defining markers in all eight retained repair artifacts before generating a candidate:

1. atomic, permission-compatible cache publication;
2. downstream hop-header removal and close framing;
3. declared-length completion checks;
4. origin request credential and hop-header removal;
5. request authority, path, and cache-root confinement;
6. strict bodyless request `Content-Length` grammar;
7. post-commit log-and-close behavior;
8. explicit origin status validation under ordinary and optimized Python.

Focused carriers remain mechanism records: PRs #118, #139, #147, #162, and #169.

## Composition decisions

The generated handler performs the checks in this order:

1. reject unsupported methods and ambiguous/body-bearing request framing;
2. validate absolute HTTP authority against the single `Host` field;
3. derive strict-descendant cache paths from the accepted raw path subset;
4. remove proxy credentials, standard hop fields, and `Connection`-nominated request fields;
5. connect to the validated authority and require origin status 200 at runtime;
6. accept only an exactly chunked transfer coding or no transfer coding;
7. validate non-chunked declared length as non-empty ASCII decimal before commitment;
8. remove response hop fields, commit one downstream 200, stream into an exclusive temporary, and publish with one rename;
9. on a pre-commit error, send one 502; after commitment, log the original exception and close without appending another response;
10. close the origin connection in every path and bind the standalone helper to loopback.

The chunked path deliberately ignores a conflicting origin `Content-Length` because `http.client` returns decoded entity bytes. Non-chunked responses retain strict declared-byte validation.

## Executed gate

Local command:

```text
python3 -m unittest -v tests/test_caching_proxy_complete_stack.py
```

Observed before repository publication:

```text
Ran 7 tests in 16.425s
OK
```

The matrix covers:

- method, authority, userinfo, query/fragment, traversal, absolute-path, percent, separator, backslash, duplicate-header, body-length, and transfer-coding request rejection before origin/cache activity;
- ordinary and real `python -O` request validation and origin-status behavior;
- proxy credential, standard hop-header, and `Connection` token removal while preserving repeated end-to-end fields;
- successful custom-reason 200, exact chunked decoding, malformed/unsupported transfer coding, malformed and negative declared lengths, premature EOF, immediate retry, and final cache bytes;
- pre-commit failure, post-header/body-prefix origin failure, cache-writer failure, and downstream disconnect with one status line and no failed publication;
- synchronized concurrent misses, hidden final name until completion, complete client bytes, ordinary creation mode, temporary cleanup, and server/thread shutdown.

Exact-head Linux Fieldwork CI is required after the pull request is opened. Its run and final head belong in the issue/PR receipt.

## Complete-diff review

The intended branch diff contains only this investigation record, its composer and runner, and the executable regression. It does not edit the imported source or any focused repair artifact.

The composer uses the merged atomic-publication patch as the executable base and verifies the remaining focused artifacts as preserved inputs. Their overlapping source changes are integrated by named anchors rather than mechanically applying stale hunks.

## Cleanup and rerun

Every loopback server calls `shutdown()` and `server_close()` and joins its serving thread. Temporary roots use `TemporaryDirectory`. Origin connections are closed in `finally`. Tests wait for completed atomic publication before cache-hit controls and require temporary sibling removal after success and failure.

The local full matrix completed once cleanly. Exact-head CI supplies the repository rerun receipt.

## Evidence boundary

This composition closes the demonstrated lexical path, request framing, header forwarding, origin-status, response framing, transfer-coding, declared-length, atomic publication, post-commit, and ordinary concurrency/lifecycle cases.

The retained limits are:

- same-UID component replacement between path validation and file open;
- request miss coalescing;
- crash-durable directory/file synchronization;
- checksums or content authentication;
- remote-network and installed-service exposure;
- broader URI syntax beyond the deliberately narrow Debian archive path subset.

## Current disposition

`REPAIR` until exact-head CI executes the full repository suite. A green exact-head run plus complete diff review promotes this composed unit to `READY FOR FINAL HUMAN CHECK`.

No Debian or other external issue, email, patch, merge request, comment, or review is included or authorized.
