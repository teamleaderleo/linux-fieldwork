# curl + Boost.Asio multi-socket re-arm discriminator

## Purpose

Demonstrate the contract identified in [`curl-asio-multi-socket-rearm`](../../investigations/curl-asio-multi-socket-rearm/README.md) without using a public network endpoint or Ceph's full build.

## Fixture

`fixture.cpp` starts a local HTTP/1.1 server twice. For each connection the server:

1. reads one request;
2. sends response headers and the first body chunk;
3. waits 350 ms;
4. sends the second body chunk and closes.

The libcurl multi-socket client runs in two modes:

- `one-shot`: an Asio readiness completion calls `curl_multi_socket_action()` and does not create another wait;
- `rearm`: after each current-generation completion, the adapter re-arms every direction curl still requests.

Both modes use the same curl callbacks, local server, timeout, and response body.

## Expected result

- `one-shot` times out after receiving only the first chunk because curl's desired `CURL_POLL_IN` mask remains unchanged and no second Asio read wait exists.
- `rearm` receives `hello world!`, observes `CURLMSG_DONE`, and exits successfully.

The executable exits nonzero unless both expectations hold.

## Build

```sh
g++ -std=c++20 -O2 -Wall -Wextra -Werror \
    -DBOOST_ERROR_CODE_HEADER_ONLY \
    fixture.cpp -o fixture \
    $(pkg-config --cflags --libs libcurl) -lpthread
./fixture
```

The header-only Boost.System define keeps this fixture dependent on Boost headers rather than a separately linked `libboost_system` binary.

## Retained local run

Before upload, the fixture was compiled with GCC 14.2.0 and libcurl 8.10.1 in the available Linux execution container. It produced:

```text
one-shot: completed=0 timed_out=1 reads=1 body='hello '
rearm: completed=1 timed_out=0 reads=2 result=No error body='hello world!'
curl multi-socket Asio re-arm discriminator: PASS
```

The branch workflow recompiles the repository copy independently on GitHub Actions.

## Boundary

This is a focused API-contract experiment, not Ceph product code and not a libcurl conformance suite. A passing result proves the missing re-arm mechanism under a local split response. It does not prove that every remove, cancellation, `INOUT`, TLS, HTTP/2, or fd-reuse path is correct.