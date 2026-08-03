# curl + Boost.Asio multi-socket re-arm discriminator

## Purpose

Demonstrate the contract identified in [`curl-asio-multi-socket-rearm`](../../investigations/curl-asio-multi-socket-rearm/README.md) without a public endpoint or Ceph's full build.

## Fixture

`fixture.cpp` starts a local HTTP/1.1 server twice. For each connection the server:

1. reads one request;
2. sends response headers and `hello `;
3. waits 350 ms;
4. sends `world!` and closes.

The libcurl multi-socket client runs in two modes:

- `one-shot`: an Asio readiness completion calls `curl_multi_socket_action()` and creates no replacement wait;
- `rearm`: after a current-generation completion, the adapter starts a new wait for every direction curl still requests.

Both modes use the same curl callbacks, server behavior, response, and deadline.

## Required result

- `one-shot` times out after one readable completion with body `hello `.
- `rearm` receives `hello world!`, observes `CURLMSG_DONE`, and succeeds after at least two readable completions.

The executable exits nonzero unless both conditions hold.

## Local build

```sh
g++ -std=c++20 -O2 -Wall -Wextra -Werror \
    -DBOOST_ERROR_CODE_HEADER_ONLY \
    fixture.cpp -o fixture \
    $(pkg-config --cflags --libs libcurl) -lpthread
./fixture
```

The header-only Boost.System define avoids a separate `libboost_system` link dependency.

## Retained evidence

- [`LOCAL_RECEIPT.md`](LOCAL_RECEIPT.md) records the first unprivileged loopback execution with GCC 14.2.0 and libcurl 8.10.1.
- [`HOSTED_RECEIPT.md`](HOSTED_RECEIPT.md) records the first independent GitHub Actions execution and its artifact identity.

Both produced:

```text
one-shot: completed=0 timed_out=1 reads=1 body='hello '
rearm: completed=1 timed_out=0 reads=2 result=No error body='hello world!'
curl multi-socket Asio re-arm discriminator: PASS
```

## Hosted gate

`.github/workflows/curl-asio-multi-socket-rearm.yml` now:

- pins Ubuntu 24.04;
- checks out without persisted credentials;
- compiles under `RUNNER_TEMP`, outside the source tree;
- records commit, runner, compiler, package, Boost, libcurl, source, and binary identities;
- executes the fixture twice and requires byte-identical receipts;
- requires the uploaded artifact;
- verifies a clean checkout;
- removes build staging before upload and proves post-upload staging cleanup.

## Why the comparison is meaningful

curl's socket callback communicates desired-interest changes. The split server does not require curl to change its `CURL_POLL_IN` mask between body chunks. A persistent watcher continues to observe the socket. A one-shot Asio adapter must submit another wait explicitly.

The two modes differ only in that re-arm decision, so the result isolates the integration contract without DNS, TLS, HTTP/2, or external network timing.

## Boundary

This is a focused API-contract experiment, not Ceph product code and not a libcurl conformance suite. It proves the missing re-arm mechanism under a local split response. It does not prove correctness for `CURL_POLL_REMOVE`, deliberate cancellation, simultaneous read/write waits, TLS, HTTP/2, connection reuse, curl-managed internal descriptors, cleanup callbacks, or fd-number reuse.
