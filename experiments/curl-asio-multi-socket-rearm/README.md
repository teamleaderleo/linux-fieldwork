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
    fixture.cpp -o fixture \
    -lcurl -lboost_system -lpthread
./fixture
```

## Boundary

This is a focused API-contract experiment, not Ceph product code and not a libcurl conformance suite. A passing result proves the missing re-arm mechanism under a local split response. It does not prove that every remove, cancellation, `INOUT`, TLS, HTTP/2, or fd-reuse path is correct.