# Asio remove/reuse stale-completion receipt

## TL;DR

The existing re-arm investigation now has an executed lifecycle discriminator for stale readiness completions.

At Ceph PR `58094` head `e88ba9657b7b8e9692d0bb1d20eb25b8dde6ee55`, `socket_wait_handler` stores only `Impl`, integer `fd`, and mask. Any Asio completion error is converted into `CURL_CSELECT_ERR` and passed to `curl_multi_socket_action(fd, mask)`. For curl-owned descriptors, `CURL_POLL_REMOVE` calls Asio `release()` and erases the wrapper.

A reduced local fixture proves the canceled wait can complete with `operation_aborted` after that same integer fd has already been reused by an unrelated socket. The stale completion therefore cannot be made safe by checking the integer fd alone.

There is a sibling remove problem for client-managed sockets: the `sockets.find(fd)` branch returns before the `CURL_POLL_REMOVE` handling used for curl-owned descriptors. A remove update starts no new waits, but it also does not cancel or invalidate waits that are already pending.

## Explain like I'm five

A watcher is told to stop watching door number 3. Door 3 is then reused for a different room. The old watcher wakes up late and still says “something happened at door 3.” The number matches, but the door now belongs to somebody else.

The adapter needs an identity or generation for the watch, not only the number.

## Why care

curl documents `CURL_POLL_REMOVE` as a monitoring-lifecycle event: the descriptor may be closed, may stay open, and may soon be monitored again. An adapter that leaves an old wait active or lets a canceled old wait call back by integer fd can report an event after curl removed interest and can confuse an old descriptor generation with a new one.

This is adjacent to the already-proven one-shot re-arm stall. The same per-socket watch object that preserves persistent interest also needs remove/re-add invalidation.

## Exact source boundary

### Ceph carrier

- Project: `ceph/ceph`
- PR: `58094`
- Exact head reviewed: `e88ba9657b7b8e9692d0bb1d20eb25b8dde6ee55`
- File: `src/rgw/curl/client.cc`
- Relevant behavior:
  - `socket_wait_handler` retains only integer `fd` and `mask`;
  - any completion error adds `CURL_CSELECT_ERR` and calls `socket_action(fd, mask)`;
  - client-managed sockets are matched before `CURL_POLL_REMOVE` handling;
  - curl-owned remove calls `release()` and erases the Asio wrapper.

### curl contract

- Project: `curl/curl`
- File: `docs/libcurl/opts/CURLMOPT_SOCKETFUNCTION.md`
- Exact blob reviewed: `2774ccbfc7f48bd3a3492d9fb701024b58a1e357`
- Contract used by this receipt:
  - socket callback updates are changes in desired monitoring;
  - `CURL_POLL_REMOVE` means the descriptor is no longer needed for monitoring at that moment;
  - remove does not imply close;
  - the same descriptor may soon be requested again.

### Fieldwork fixture

- File: `experiments/curl-asio-multi-socket-rearm/asio-release-fd-reuse.cpp`
- Commit adding fixture: `33f3333230d47606daad7e5f8d075b345add2f36`
- Source SHA-256 from executed copy: `65f665ec68a1abe840e4f85bb545c9dfaa63c9839d27d4411ffff0aad08e4ba4`

## Environment

Executed 2026-08-11 in the available Linux research container:

```text
Linux 6.18.35 x86_64
g++ 14.2.0
Boost 1.83.0
libcurl 8.10.1 installed (fixture itself does not link libcurl)
```

The fixture exercises Boost.Asio descriptor lifecycle only. It uses local Unix socket pairs and no network endpoint.

## Command

```sh
g++ -std=c++20 -O2 -Wall -Wextra -pthread \
  experiments/curl-asio-multi-socket-rearm/asio-release-fd-reuse.cpp \
  -o /tmp/asio-release-fd-reuse
/tmp/asio-release-fd-reuse
```

## Observed result

```text
released=3 watched_fd=3
new pair before force=3,4
new unrelated socket now occupies fd=3
callback ec=125 ('Operation canceled') fd=3 fd_valid_now=1
summary callback=1 operation_aborted=1 fd_reused_and_valid=1
```

The fixture exits 0 only when all three conditions hold:

1. the canceled wait handler runs;
2. its error is Asio `operation_aborted`;
3. the old integer fd is valid again by callback time because a different socket now occupies that number.

## Source interpretation

For the curl-owned path, Ceph currently treats this deliberate lifecycle cancellation as `CURL_CSELECT_ERR` and calls `curl_multi_socket_action()` with the saved integer fd. The executed fixture proves that fd identity can already have changed before the canceled completion is delivered.

For the client-owned path, `CURL_POLL_REMOVE` reaches the early `sockets.find(fd)` branch and returns without invalidating pending waits. curl's contract allows remove without immediate close, so close ownership cannot substitute for monitor removal.

These two paths point to the same repair boundary: a per-socket watch generation whose desired mask, pending operations, remove state, and descriptor identity are separate from descriptor close ownership.

## Candidate invariant

After a curl socket update removes or replaces monitoring interest:

- no completion from an older watch generation may call `curl_multi_socket_action()`;
- deliberate `operation_aborted` caused by replacement/removal is consumed as adapter lifecycle, not translated to `CURL_CSELECT_ERR`;
- remove stops monitoring even when the descriptor remains open;
- re-add creates a fresh current generation;
- a reused integer fd cannot make an old completion current again.

## Negative control / what this receipt does not establish

- The fixture does not execute the complete Ceph adapter.
- It does not prove a user-visible Ceph failure from fd reuse.
- It does not claim libcurl closes descriptors on `CURL_POLL_REMOVE`.
- It does not cover simultaneous read/write waits, TLS, HTTP/2, resolver backends, Happy Eyeballs, connection-cache reuse, or multi cleanup.
- It does not prove that every `operation_aborted` should be ignored; the claim is limited to cancellation caused by deliberate watch replacement/removal.

## Next discriminators

1. Extend the existing reduced curl+Asio fixture with explicit `REMOVE -> re-add` generation handling and a broken control that lets the old completion call `socket_action()`.
2. Add a client-managed `CURL_POLL_REMOVE` case where the fd stays open long enough to prove an old pending wait remains live in the current model.
3. Add `INOUT` with independently completing read/write waits and replacement of one direction.
4. Only after those pass, transplant the watch-generation model into a Ceph-compatible test carrier.

## External-contact state

No curl or Ceph issue, pull request, comment, review, email, patch submission, or other external interaction was made by this fieldwork pass.
