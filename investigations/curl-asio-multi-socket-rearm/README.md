# Asio and libcurl multi-socket readiness re-arming

## TL;DR

The hang reported in `curl/curl#22327` is reproduced by a reduced loopback fixture. A Boost.Asio adapter that consumes one `async_wait()` completion and does not re-arm stalls after the first response chunk while libcurl's unchanged `CURL_POLL_IN` interest remains active. The same transfer completes when the adapter keeps per-socket interest and starts another current-generation wait after each completion.

The demonstrated repair owner is the event-loop adapter, not libcurl. This record does **not** claim that the full Ceph integration is fixed, nor that remove, cancellation, simultaneous read/write, TLS, HTTP/2, connection reuse, or fd-number reuse are already correct.

## Explain like I'm five

curl says, “keep watching this door for deliveries.” Boost.Asio watches once per request. After the first delivery, the adapter must ask Asio to watch again. curl does not repeat its instruction because its requested interest never changed.

Literal sequence:

`CURL_POLL_IN` → one Asio read wait completes → adapter calls `curl_multi_socket_action()` → curl still wants `CURL_POLL_IN` → no changed-interest callback → no second Asio wait → second body chunk is never processed.

## Why care

This failure happens after DNS, connect, TLS, and request writing can all appear successful. It is easy to blame curl, HTTP/2, TLS, or the kernel when the missing operation is in the integration layer. Getting ownership right avoids changing a foundational library to compensate for an event-loop adapter bug.

## Current state

- State: `REVIEW`
- Exact curl head reviewed: `c59b06c99ce1663560caf0147a11eb05c4b30689`
- Exact Ceph adapter carrier reviewed: PR `58094`, head `e88ba9657b7b8e9692d0bb1d20eb25b8dde6ee55`
- Reduced fixture source carrier: `experiments/curl-asio-multi-socket-rearm/fixture.cpp`
- Retained local receipt: `experiments/curl-asio-multi-socket-rearm/LOCAL_RECEIPT.md`
- First hosted run: success at Linux Fieldwork head `a27240f35d2e08f42204d83119115d5f61cf65ee`
- Workflow-hardening head: `9cf6decbc7d296cc65dc993c22320cb972e382b9`
- First incomplete technical step: add focused lifecycle controls for remove, deliberate cancellation, `INOUT`, and stale completions
- Cleanup state: loopback-only fixture; no public endpoint; no persistent local process; hosted workflow now builds outside the checkout and proves cleanup
- External-contact state: none authorized or made

## Question

Does a one-shot Asio readiness operation require explicit re-arming while libcurl's desired socket mask remains unchanged, and what lifecycle rules are needed to make that re-arm safe?

## Source identities

### curl

- Issue: `curl/curl#22327`
- Commit: `c59b06c99ce1663560caf0147a11eb05c4b30689`
- Socket callback documentation blob: `2774ccbfc7f48bd3a3492d9fb701024b58a1e357`
- libuv example blob: `2671556ba0c3d633e190d550b4e557ab67f4073f`
- `lib/multi_ev.c` blob: `3b7eeb0dc3a6914e46c08f368d6f561b15f48de7`

### Ceph adapter

- Pull request: `ceph/ceph#58094`
- Observed head: `e88ba9657b7b8e9692d0bb1d20eb25b8dde6ee55`
- Files reviewed:
  - `src/rgw/curl/client.cc`
  - `src/test/rgw/test_rgw_curl_client.cc`

### Linux Fieldwork fixture

- Source: `experiments/curl-asio-multi-socket-rearm/fixture.cpp`
- Local receipt source head: `8a947680c394e58d55934157c77bc7058e779d6f`
- First hosted receipt carrier: `a27240f35d2e08f42204d83119115d5f61cf65ee`

## API contract and historical context

`CURLMOPT_SOCKETFUNCTION` reports changes in desired monitoring. It is not a request to create a fresh one-event subscription after every readiness completion.

curl's current event-interest implementation avoids callbacks when the effective mask for a socket is unchanged. That behavior keeps the API independent of a particular event-loop model:

- persistent watcher APIs can leave the watcher active;
- level-triggered poll loops can continue polling the registered fd;
- one-shot operation APIs must submit another operation after completion.

curl's own libuv example uses a persistent `uv_poll` watcher. Its readiness callback calls `curl_multi_socket_action()` while the watcher remains active until the requested mask is changed or removed.

Boost.Asio `async_wait()` represents one asynchronous operation with one completion. A completed operation does not remain registered. An Asio adapter must therefore translate curl's persistent desired interest into a sequence of one-shot waits.

This division of responsibility is longstanding and useful. Making curl repeat unchanged masks merely to re-arm one specific event-loop style would create duplicate watcher churn for integrations that already maintain persistent interest correctly.

## Reviewed baseline

The Ceph adapter:

1. installs curl timer and socket callbacks;
2. starts an Asio read or write wait when curl announces interest;
3. calls `curl_multi_socket_action()` from the completion handler;
4. returns without issuing another wait.

The reported HTTPS trace is consistent with the first read wait being consumed during TLS or HTTP/2 progress. curl continues to want reads but has no reason to emit another unchanged `CURL_POLL_IN` update. Plain HTTP can appear healthy when one readable completion is enough to finish the small response.

## Reduced reproduction

The Linux Fieldwork fixture starts a local HTTP/1.1 server twice. Each server instance:

1. accepts one loopback connection;
2. reads one request;
3. sends headers and `hello `;
4. waits 350 ms;
5. sends `world!` and closes.

The client runs two modes against the same response pattern:

- `one-shot`: process one Asio readiness completion and do not re-arm;
- `rearm`: keep desired interest in a watch object and re-arm the still-current direction.

Observed local and hosted behavior:

```text
one-shot: completed=0 timed_out=1 reads=1 body='hello '
rearm: completed=1 timed_out=0 reads=2 result=No error body='hello world!'
curl multi-socket Asio re-arm discriminator: PASS
```

## What the result proves

- One-shot readiness consumption is sufficient to reproduce the stall without DNS, TLS, HTTP/2, Ceph, or a public server.
- libcurl does not need to repeat an unchanged interest callback for the transfer to be correct.
- Re-arming the current watch generation receives the second chunk and reaches `CURLMSG_DONE`.
- The first repair target is the Asio integration.

## What the result does not prove

- The complete Ceph implementation is fixed by copying the fixture verbatim.
- Every curl-managed internal fd uses the same close ownership as a client-created socket.
- `CURL_POLL_REMOVE` means close. curl explicitly does not guarantee that.
- Every Asio error should become `CURL_CSELECT_ERR`.
- Concurrent read and write completions cannot race a mask replacement.
- An old completion cannot act on a new socket that reused the same integer fd.
- TLS, HTTP/2, Happy Eyeballs, keep-alive, and connection-cache cleanup are covered.

## Candidate adapter model

Use a per-socket watch object that stores persistent curl intent separately from individual Asio operations.

Each watch needs:

- exact socket ownership class;
- current read/write desired mask;
- monotonically increasing generation;
- at most one active read wait and one active write wait;
- removed/closing state;
- identity that survives integer-fd reuse checks.

### On curl mask update

1. Find or create the exact watch object.
2. Increment generation when replacing or removing interest.
3. Store the new desired mask.
4. Cancel or invalidate obsolete operations.
5. Start any missing operation for an active direction.
6. Treat `CURL_POLL_REMOVE` as monitoring removal, not proof of descriptor closure.

### On Asio completion

1. Verify watch identity and generation.
2. Clear the matching pending-operation flag.
3. Ignore deliberate `operation_aborted` from replacement or removal.
4. Convert genuine readiness or error into curl select bits.
5. Call `curl_multi_socket_action()`.
6. Re-read current desired interest because curl may update it synchronously.
7. Re-arm every still-active direction that has no current operation.

### Close ownership

Readiness lifecycle and descriptor lifetime must be separate:

- poll remove detaches monitoring;
- a client close callback releases a client-owned socket;
- a wrapper around a curl-owned fd must release the native handle before wrapper destruction;
- stale callbacks must never act only because an integer fd value matches.

## Remaining test matrix

| Gate | Required observation |
|---|---|
| changed `IN` → `OUT` mask | old read completion is ignored; one write wait remains |
| `INOUT` | read and write can complete independently without duplicate actions |
| deliberate cancellation | `operation_aborted` is discarded, not reported as a network error |
| `CURL_POLL_REMOVE` | monitoring ends without assuming close |
| remove then re-add | new generation receives events; old generation is inert |
| fd-number reuse | old object cannot drive the new socket |
| keep-alive second request | persistent watcher continues across reuse |
| local TLS HTTP/1.1 | multiple handshake/response events complete |
| local HTTP/2 where available | multiplexed read progression completes |
| resolver and Happy Eyeballs fds | curl-owned descriptors retain correct close semantics |
| multi cleanup | late callbacks cannot access destroyed adapter state |

## Conventions for a product patch

A Ceph-side change should follow these boundaries:

- keep adapter changes in the RGW curl integration, not curl itself;
- add deterministic loopback tests before network-dependent controls;
- preserve the executor/strand assumptions documented by the client;
- keep client-managed and curl-managed close paths explicit;
- avoid callbacks that capture only an integer fd and raw owner pointer;
- make shutdown idempotent and safe against callbacks issued during curl cleanup;
- retain trace fields for mask, generation, operation start/completion, and close/remove ownership.

## Interpretation

The source contract and reduced runtime proof agree. The issue is no longer only “possible API misuse”: the exact missing re-arm mechanism has been demonstrated under controlled conditions.

The evidence is still intentionally narrower than a Ceph patch. The next useful work is lifecycle safety around the demonstrated mechanism, followed by a Ceph-compatible test carrier. Only then is it reasonable to prepare product code or communicate externally.

## Evidence boundary

This record covers exact source review plus a Linux loopback HTTP/1.1 discriminator. It does not claim a merged Ceph fix, a curl defect, a Fedora/Ceph full reproduction, or coverage of every fd lifecycle path.

## Next step

Extend the reduced fixture with deterministic mask replacement, deliberate cancellation, remove/re-add, and stale-generation controls. Keep those checks independent from TLS and HTTP/2 so lifecycle correctness is established before protocol complexity is added.

## Authority

No curl or Ceph issue, pull request, comment, review, email, patch submission, or other external interaction has been authorized or made.
