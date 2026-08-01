# Draft upstream issue — caching_proxy request, response, and cache lifecycle

> Use only if the maintainer requests issue-first discussion. A pull request with tests is the preferred delivery because the source mechanisms must be reviewed together.

## Title

`caching_proxy.py can publish incomplete/error responses and trusts proxy input across request, origin, and cache boundaries`

## Body

`caching_proxy.py` currently relies on assertions and direct path/header forwarding across several boundaries in one request handler. The combined behavior permits these reproducible failures in local loopback tests:

- optimized Python removes request and origin-status assertions;
- distinct or unsafe request targets can select an unintended cache path or collapse to one cache key;
- proxy credentials and hop-by-hop request fields are forwarded to the selected origin;
- origin errors, invalid framing, or premature EOF can be exposed as downstream success or persistent cache content;
- a final cache pathname becomes visible before receipt is complete;
- an exception after the downstream `200` begins attempts to append a second `502` response.

A composed candidate addresses the complete lifecycle in one handler:

1. accept only bodyless GET requests;
2. validate absolute-form target and `Host` authority;
3. map the accepted raw path to strict cache descendants;
4. remove proxy-only and hop-by-hop request fields;
5. validate origin status, transfer coding, and declared length before downstream commitment;
6. normalize downstream hop-by-hop framing;
7. stream through an exclusive hidden temporary file;
8. replace the final pathname only after complete receipt;
9. return one 502 before commitment;
10. log and close after commitment without writing another status;
11. bind the standalone development helper to loopback.

The regression matrix uses real loopback servers and raw clients. It covers ordinary and optimized Python, zero side effects for rejected requests, request-header capture, fixed/chunked/EOF success, origin errors, malformed and short lengths, unsupported transfer coding, premature EOF and retry, late failures, concurrent misses, file mode, temporary cleanup, and server/thread/socket cleanup.

The proposed scope leaves same-UID pathname replacement races, miss coalescing, crash-durable synchronization, checksums, remote deployment policy, and broader URI syntax for separate work.

Would a pull request containing the complete source repair and focused Python regression matrix fit the project’s preferred test organization?

## Pre-send verification

- [ ] exact upstream base and `caching_proxy.py` blob recorded;
- [ ] current issue/PR overlap search repeated;
- [ ] patch applies cleanly;
- [ ] focused matrix passes under ordinary and optimized Python;
- [ ] cleanup/rerun passes;
- [ ] explicit authorization recorded.

## Authority

Draft only. No public issue has been created.