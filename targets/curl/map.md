# curl Target Map

## In simple words

curl and libcurl move data across network protocols. Their multi-socket API lets an application use its own event loop, but that means curl and the application must agree exactly about who keeps watching each file descriptor, who closes it, and when a readiness request changes.

## Source identity

- Canonical repository: `https://github.com/curl/curl.git`
- Canonical branch: `master`
- Current research revision: `c59b06c99ce1663560caf0147a11eb05c4b30689`
- Controlled fork: `https://github.com/teamleaderleo/curl.git`
- Fork default branch observed: `master`
- Fork and canonical current heads observed at the same commit above.
- Imported source tree: not yet present under `upstream/`; repository reads in this round are pinned to the canonical commit above.

## Why it recurs

libcurl crosses sockets, DNS, TLS, HTTP versions, connection reuse, timers, callbacks, file-descriptor ownership, cancellation, and application event loops. Small adapter mistakes can look like protocol or TLS failures even when the underlying transfer state machine is behaving as documented.

## Relevant programmes

- [`Services, processes, and resources`](../../programmes/services-resources/STATUS.md)
- [`Security and networking boundaries`](../../programmes/security-networking/STATUS.md)
- [`Ecosystem contributions and upstream fixes`](../../programmes/ecosystem-contributions/STATUS.md)

## Mapped lanes

- LF-23 — cancellation, subprocess, and file-descriptor cleanup
- LF-27 — network namespaces and DNS ownership
- LF-29 — netlink compatibility and fallback, as a related event/API compatibility discipline
- LF-39 — foundational-library boundary corpus

## Current investigation

- [Asio and libcurl multi-socket readiness re-arming](../../investigations/curl-asio-multi-socket-rearm/README.md)

## Source and test surfaces

Begin with:

- `docs/libcurl/opts/CURLMOPT_SOCKETFUNCTION.md`
- `docs/libcurl/opts/CURLMOPT_TIMERFUNCTION.md`
- `docs/libcurl/curl_multi_socket_action.md`
- `lib/multi.c`
- `lib/multi_ev.c`
- `docs/examples/multi-uv.c`
- `tests/libtest/` multi-socket fixtures

The current external adapter under study is Ceph pull request `ceph/ceph#58094`, exact observed head `e88ba9657b7b8e9692d0bb1d20eb25b8dde6ee55`.

## Review discriminators

For each adapter, identify:

1. whether readiness registration is persistent or one-shot;
2. how unchanged curl interest is kept armed;
3. how `CURL_POLL_REMOVE` cancels or invalidates outstanding waits;
4. whether deliberate cancellation is incorrectly reported as socket error;
5. whether simultaneous read and write waits can produce stale callbacks;
6. who owns and closes curl-managed versus application-managed descriptors.

## Policy boundary

This map authorizes reading and controlled-fork research only. The current evidence points first to an adapter contract problem, not a demonstrated curl defect. No curl or Ceph issue comment, pull request, review, email, or other external interaction is authorized.