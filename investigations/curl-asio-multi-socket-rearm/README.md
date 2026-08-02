# Asio and libcurl multi-socket readiness re-arming

## TL;DR

The HTTPS hang reported in `curl/curl#22327` is most strongly explained by the event-loop adapter in Ceph pull request `ceph/ceph#58094`, not by a demonstrated libcurl failure. The adapter starts a one-shot Boost.Asio `async_wait()` when libcurl announces read or write interest. After that wait completes, its handler calls `curl_multi_socket_action()` but does not re-arm the wait. libcurl's socket callback announces **changes** in desired monitoring and does not have to repeat an unchanged `CURL_POLL_IN`, so the application stops watching after the first readiness event. Plain HTTP can finish in one read; TLS and HTTP/2 commonly need later readiness events.

## Explain like I'm five

curl says, “keep watching this door for deliveries.” The adapter watches once, sees one delivery, and then walks away. curl does not repeat the instruction because it never changed. The next delivery arrives with nobody watching.

Literal example: libcurl requests `CURL_POLL_IN` → Asio completes one `async_wait(wait_read)` → adapter calls `curl_multi_socket_action()` once → curl still wants `CURL_POLL_IN` and emits no changed-status callback → adapter has no outstanding read wait → transfer hangs.

## Why care

A networking adapter can hang indefinitely after a successful DNS lookup, TCP connection, TLS handshake, and request write. The failure can be misclassified as a curl, TLS, HTTP/2, or kernel readiness bug even though the missing operation belongs to the adapter. Correct ownership is essential before changing a foundational library.

## Current state

- State: `REVIEW`
- Exact curl head: `c59b06c99ce1663560caf0147a11eb05c4b30689`
- Exact adapter carrier: Ceph PR `58094`, observed head `e88ba9657b7b8e9692d0bb1d20eb25b8dde6ee55`
- Latest authoritative gate or artifact: source-contract comparison between Ceph's adapter, curl's socket callback documentation, curl's libuv example, curl's current event-interest implementation, and Boost.Asio one-shot wait semantics
- First incomplete step: run a reduced local fixture that requires at least two read-ready completions without a curl interest-mask change
- Cleanup state: no sockets, server, branch, or external comments created in this round
- Next safe action: build a standalone adapter fixture in a controlled branch or Linux Fieldwork test carrier, then prove one-shot failure and persistent re-arm success
- External-contact state: none authorized or made

## Intent and precedent

curl documents `CURLMOPT_SOCKETFUNCTION` as a callback that reports socket-status **updates with changes since the previous call**. The application is expected to monitor the requested activities and call `curl_multi_socket_action()` whenever one occurs.

curl's current `multi_ev.c` returns early when an individual transfer's action is unchanged and also avoids invoking the application callback when the combined action for a socket has not changed. This is expected behavior: the callback communicates desired-interest changes, not a fresh readiness subscription after every event-loop completion.

curl's libuv example uses `uv_poll_start()`, which keeps polling until stopped or changed. Its readiness callback calls `curl_multi_socket_action()` and leaves the poll watcher active. That is the event-loop contract an Asio adapter must reproduce explicitly.

Boost.Asio's `async_wait()` is one asynchronous operation with one completion handler. Completion does not create another wait. Persistent monitoring therefore requires another `async_wait()` after each completion while the desired mask remains active.

## Question

Does the Ceph adapter stop monitoring a socket after one Asio readiness completion while libcurl still requests the same readiness mask, and can a generation-safe re-arm loop resolve that without stale callbacks or descriptor-ownership errors?

## Source

- Library project: curl
- curl issue: `curl/curl#22327`
- curl requested revision: current canonical `master` observed 2026-08-03
- curl resolved commit: `c59b06c99ce1663560caf0147a11eb05c4b30689`
- curl socket-function documentation blob: `2774ccbfc7f48bd3a3492d9fb701024b58a1e357`
- curl libuv example blob: `2671556ba0c3d633e190d550b4e557ab67f4073f`
- curl `lib/multi_ev.c` blob: `3b7eeb0dc3a6914e46c08f368d6f561b15f48de7`
- Adapter project: Ceph
- Adapter pull request: `ceph/ceph#58094`
- Adapter observed head: `e88ba9657b7b8e9692d0bb1d20eb25b8dde6ee55`
- Adapter files reviewed: `src/rgw/curl/client.cc`, `src/test/rgw/test_rgw_curl_client.cc`
- Candidate source commit: none
- Controlled curl fork: `teamleaderleo/curl`
- Local source path: not imported yet
- Import metadata: not present

## Environment

- Distribution and release: not executed in this round
- Kernel and architecture: issue report used Linux x86-64; reduced fixture should run on ordinary Linux CI
- Shell: test harness dependent
- Privileges: unprivileged
- Context: local TCP/TLS server and Boost.Asio event loop
- Relevant tool versions: record curl, OpenSSL or selected TLS backend, nghttp2, Boost, compiler, and CMake versions at execution time

## Baseline behavior

### Adapter registration

The Ceph adapter configures:

- `CURLMOPT_TIMERFUNCTION` and timer data;
- `CURLMOPT_SOCKETFUNCTION` and socket data;
- custom open- and close-socket callbacks for easy handles.

For a client-managed socket, its socket callback starts an Asio wait for each requested direction. The wait handler stores the fd and event mask.

### One-shot completion

When an Asio wait completes, the handler:

1. adds `CURL_CSELECT_ERR` for any Asio error;
2. calls `curl_multi_socket_action(fd, mask)`;
3. returns.

It does not issue another `async_wait()`.

### Why curl does not rescue it

After processing the first readable event, libcurl may still need `CURL_POLL_IN`. Because the desired interest did not change, curl's event code does not invoke the socket callback again. The adapter therefore has no read wait left.

The reported trace fits this sequence:

1. DNS and IPv6-to-IPv4 connection fallback complete;
2. TLS handshake completes;
3. HTTP/2 request is sent;
4. the first read wait has already been consumed by handshake progress;
5. curl still wants reads but does not emit a changed-interest callback;
6. no Asio wait is outstanding for the response.

The plain HTTP control can succeed because a single readable completion may contain enough data to finish the response.

## Additional adapter risks found during review

### `CURL_POLL_REMOVE` asymmetry

The adapter explicitly handles `CURL_POLL_REMOVE` for curl-managed external descriptors, but the client-managed-socket branch returns before a corresponding remove path. The custom close callback erases client-owned sockets when curl closes them, but curl documents that `CURL_POLL_REMOVE` does not necessarily mean close and that the same descriptor may be announced again. Monitoring lifecycle and descriptor lifetime must remain separate.

### Deliberate cancellation versus socket error

The wait handler maps every nonzero Asio completion error to `CURL_CSELECT_ERR`. A wait deliberately cancelled because the interest mask changed or the descriptor was removed should generally be discarded as stale control flow, not reported to curl as a network error.

### Concurrent read and write waits

`CURL_POLL_INOUT` can schedule two waits on one descriptor. A later mask change or remove can leave completions from an earlier generation. Without generation checks, stale callbacks can call `curl_multi_socket_action()` using an obsolete mask or a descriptor whose ownership has changed.

### Descriptor reuse

The map is keyed by integer fd. When one socket is removed and another later receives the same fd number, an old wait completion must not act on the new socket. The adapter needs identity beyond the integer, normally an object/generation pair.

## Hypothesis or candidate

Use a per-socket watch object that separates curl's desired interest from individual Asio operations.

Each watch should carry:

- the socket object or explicit ownership class;
- current desired read/write mask;
- monotonically increasing generation;
- at most one outstanding read wait and one outstanding write wait;
- removal/closing state.

### On socket callback update

1. Look up or create the watch for the exact socket object.
2. Increment generation when replacing or removing interest.
3. Store the new desired mask.
4. Start missing read/write waits for active directions.
5. On `CURL_POLL_REMOVE`, clear interest and invalidate outstanding callbacks without assuming curl will close the descriptor.

### On wait completion

1. Verify the watch object and generation still match.
2. Ignore `operation_aborted` caused by deliberate cancellation or mask replacement.
3. Convert genuine readiness/error to curl select bits.
4. Call `curl_multi_socket_action()`.
5. Re-read the current desired mask, because curl may have changed it synchronously through the socket callback.
6. Re-arm any still-active direction that does not already have a wait.

### Ownership requirement

Client-managed sockets and curl-managed descriptors should share readiness semantics but retain separate close behavior. A poll-remove operation removes monitoring; a close callback or owner destructor releases the descriptor.

## Reproduction

The first fixture should avoid public endpoints and HTTP/2 complexity.

### Two-read local server

Build a local server that:

1. accepts one connection;
2. reads the request;
3. writes the response headers or first body byte;
4. waits until the client processes that readiness event;
5. writes the remaining body;
6. keeps the curl interest mask unchanged between writes.

Run the current adapter against it.

Expected baseline:

- first read completion calls `curl_multi_socket_action()`;
- no second Asio read wait is present;
- second server write does not advance the transfer;
- timeout proves the hang.

Expected candidate:

- read wait is re-armed after the first completion;
- second write wakes the adapter;
- `CURLMSG_DONE` is received;
- no extra socket callback was required.

### Matrix

Then run:

- HTTP/1.1 cleartext with a split response;
- HTTPS with a local certificate and forced HTTP/1.1;
- HTTPS with HTTP/2 where available;
- IPv4 only;
- failed IPv6 followed by IPv4;
- keep-alive second request;
- `CURL_POLL_INOUT` with controlled mask changes;
- remove and re-add the same fd where feasible;
- deliberate cancellation while waits are outstanding;
- connection cache cleanup after all transfers finish.

### Trace fields

For every event record:

- monotonic sequence number;
- fd and watch generation;
- curl action (`IN`, `OUT`, `INOUT`, `REMOVE`);
- Asio wait start and completion;
- completion error category/value;
- call to `curl_multi_socket_action()` and mask;
- running-handle count;
- `CURLMSG_DONE` result;
- open/close callback and socket-object identity.

## Results

### Demonstrated by source-contract review

- curl's callback contract reports changed desired monitoring, not a new one-shot subscription after every readiness event.
- curl's current event code suppresses callbacks when interest is unchanged.
- curl's libuv example uses a persistent watcher.
- Boost.Asio `async_wait()` completes once.
- the Ceph adapter's wait completion calls curl once and does not re-arm the Asio wait.
- the source sequence is sufficient to explain why HTTP can pass while HTTPS/HTTP2 hangs.
- the adapter has additional remove, cancellation, and stale-completion questions that should be tested separately.

### Not yet demonstrated here

- A compiled reduced fixture reproducing the hang.
- The exact sequence on the reporter's Fedora and Ceph build.
- Whether current curl changes after the reported 8.18.0 release alter any secondary behavior.
- A passing generation-safe candidate.

## Interpretation

The first distinguishing owner is the adapter. Changing curl to repeat unchanged socket-interest callbacks would turn a persistent-interest API into an event-loop-specific re-arm mechanism and could create redundant watcher churn for correct adapters.

The appropriate repair target is the Asio integration: retain curl's interest until changed or removed, and translate that persistent interest into repeated one-shot Asio operations.

This conclusion is stronger than a generic “possible adapter misuse” because the exact missing re-arm is visible in the reviewed source and directly matches both APIs' documented semantics. Runtime evidence is still required before declaring the external issue resolved.

## Cross-context review

| Context | Discriminator | Required behavior |
|---|---|---|
| Persistent libuv watcher | poll remains active after callback | reference behavior |
| One-shot Asio wait | operation ends after one completion | adapter must re-arm |
| Unchanged curl mask | no new socket callback | existing watch must persist |
| Changed curl mask | callback updates direction | cancel/invalidate obsolete waits |
| `CURL_POLL_REMOVE` | monitoring ends, close not guaranteed | detach watch without assuming descriptor closure |
| Custom close callback | application owns descriptor close | release exact socket object |
| Curl-managed fd | curl owns close | wrapper must release native handle before destruction |
| `INOUT` | read and write may complete independently | no duplicate or stale actions |
| Deliberate cancellation | `operation_aborted` is expected control flow | do not report false network error |
| fd-number reuse | integer may identify a new socket later | generation/object identity blocks stale completion |

Stop this investigation at the adapter contract. Split any confirmed libcurl defect discovered by the reduced reference implementation into a new investigation.

## Evidence boundary

This record is based on exact source and public API documentation. It does not claim a runtime reproduction, a merged Ceph change, or a curl defect. It does not authorize comments on the existing curl issue or Ceph pull request.

## Next step

Create a standalone two-read fixture and retain both traces:

1. current one-shot adapter stalls after first completion;
2. persistent/generation-safe adapter completes without an additional curl interest update.

Only after that result should a candidate be prepared in a controlled Ceph-compatible carrier or described to another project.

## Authority

No curl or Ceph issue, pull request, comment, review, email, or other external interaction has been authorized or made.