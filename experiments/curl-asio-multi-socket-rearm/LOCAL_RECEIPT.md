# Local receipt — curl Asio re-arm discriminator

- Date: 2026-08-03
- Fixture source carrier: `experiments/curl-asio-multi-socket-rearm/fixture.cpp`
- Source commit before receipt: `8a947680c394e58d55934157c77bc7058e779d6f`
- Compiler: `g++ (Debian 14.2.0-19) 14.2.0`
- libcurl: `8.10.1`
- Boost.System mode: header-only via `BOOST_ERROR_CODE_HEADER_ONLY`
- Network: loopback only; no public endpoint
- Privileges: unprivileged

## Command

```sh
g++ -std=c++20 -O2 -Wall -Wextra -Werror \
    -DBOOST_ERROR_CODE_HEADER_ONLY \
    fixture.cpp -o fixture \
    $(pkg-config --cflags --libs libcurl) -lpthread
./fixture
```

## Output

```text
one-shot: completed=0 timed_out=1 reads=1 body='hello '
rearm: completed=1 timed_out=0 reads=2 result=No error body='hello world!'
curl multi-socket Asio re-arm discriminator: PASS
```

## Classification

`PASS`

The focused runtime behavior agrees with the source-contract analysis:

- one-shot Asio monitoring consumes one read completion and stalls while curl's unchanged read interest remains active;
- re-arming the current-generation watch receives the second split-response chunk and reaches `CURLMSG_DONE`;
- the test does not depend on DNS, TLS, HTTP/2, Ceph, or a public server.

## Evidence boundary

This receipt proves the local HTTP/1.1 split-response discriminator only. Remove handling, deliberate cancellation, concurrent read/write waits, TLS, HTTP/2, connection reuse, and fd-number reuse remain separate gates.