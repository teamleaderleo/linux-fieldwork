# curl multi-socket event-loop integration conventions

## Scope

This note records the API history, current contract, and adapter conventions relevant to event-loop integrations such as Boost.Asio. It supports the focused investigation in `investigations/curl-asio-multi-socket-rearm/README.md` and does not propose a curl API change.

## API timeline

The current documentation records a deliberately layered introduction:

| API | Added | Role |
|---|---:|---|
| `CURLMOPT_SOCKETFUNCTION` | 7.15.4 | report changes in desired socket monitoring |
| `curl_multi_assign()` | 7.15.5 | associate application watch state with a curl socket |
| `CURLMOPT_TIMERFUNCTION` | 7.16.0 | replace or delete one non-repeating application timer |
| `curl_multi_socket_action()` | 7.16.3 | tell curl which socket activity occurred |

This sequence reflects an ownership split that remains present in current curl:

- curl owns protocol state and tells the application what readiness it currently needs;
- the application owns event-loop registration and tells curl when readiness or timeout occurs;
- application watch state may be attached to curl's socket entry with `curl_multi_assign()`;
- timer updates replace the previous timer rather than stacking new independent timers.

## Current exact sources

Reviewed at curl commit `c59b06c99ce1663560caf0147a11eb05c4b30689`:

- `docs/libcurl/opts/CURLMOPT_SOCKETFUNCTION.md`, blob `2774ccbfc7f48bd3a3492d9fb701024b58a1e357`
- `docs/libcurl/curl_multi_assign.md`, blob `784f5ad9a9cc4a6396a6ee0581ecd7222be6d8d4`
- `docs/libcurl/opts/CURLMOPT_TIMERFUNCTION.md`, blob `ac55fb351bf9efe74b304d2f3d82be73fd687a81`
- `docs/libcurl/curl_multi_socket_action.md`, blob `4d690fd97d26d2cd16966a449955d76e6dbbbc9e`
- `docs/examples/multi-uv.c`, blob `2671556ba0c3d633e190d550b4e557ab67f4073f`
- `lib/multi_ev.c`, blob `3b7eeb0dc3a6914e46c08f368d6f561b15f48de7`

## Contract distilled

### Socket callback means desired state changed

The socket callback reports status updates with changes since the previous callback. The effective instruction is persistent:

> monitor this socket for this mask until curl changes or removes that instruction.

It is not:

> perform exactly one wait and expect curl to repeat the same mask afterward.

Current `multi_ev.c` reinforces this interpretation by suppressing callbacks when an individual transfer's action or the combined socket action did not change.

### Socket action means an event occurred

When the event loop detects readiness, the application calls `curl_multi_socket_action()` with the fd and event bits. That call can synchronously cause zero, one, or multiple socket callback updates.

An adapter must therefore assume its desired mask may change during the call and re-read current watch state before scheduling more work.

### Timer callback means replace one timer

`CURLMOPT_TIMERFUNCTION` asks the application to maintain one non-repeating timer:

- a new non-negative timeout replaces the old one;
- `-1` deletes it;
- `0` means schedule immediate work, but not by recursively calling curl from inside the timer callback.

Generation or cancellation identity is useful here for the same reason it is useful for socket waits: an obsolete completion must not drive current curl state.

### Assigned pointer belongs to monitoring lifetime

`curl_multi_assign()` associates one application pointer with a socket until curl sends `CURL_POLL_REMOVE`. That makes a watch object the natural unit for:

- desired mask;
- pending read/write operations;
- generation;
- ownership class;
- removal state.

The assigned pointer is not itself proof that the underlying descriptor should be closed.

## Event-loop model comparison

| Event-loop model | Registration behavior | Adapter obligation |
|---|---|---|
| persistent poll watcher | remains active until changed/stopped | update watcher only when curl mask changes |
| repeated `poll`/`select` loop | each loop examines registered fd set | retain mask in application state between loops |
| edge-triggered watcher | event may represent a state transition | drain/drive according to loop semantics and retain curl interest |
| one-shot asynchronous operation | one completion consumes one operation | submit a replacement operation while curl interest remains active |
| completion-port operation | completion corresponds to submitted work | keep enough application state to issue current replacement work safely |

curl's own libuv example uses persistent polling. A Boost.Asio `async_wait()` adapter must explicitly create persistence by re-arming.

## Required adapter invariants

### Interest invariant

For every active curl socket and requested direction, either:

- a current event-loop watch/operation exists; or
- adapter code is synchronously processing an event that will update or replace that watch before returning to the loop.

### Generation invariant

A completion may act on curl only when its watch object and generation still match current ownership.

This prevents:

- cancelled read waits reporting false socket errors;
- old `INOUT` completions using obsolete masks;
- remove/re-add races;
- integer fd reuse directing an old completion to a new socket.

### Remove invariant

`CURL_POLL_REMOVE` ends monitoring and clears curl's assigned pointer. It does not by itself prove the descriptor is closed or should be closed by the adapter.

### Close invariant

Descriptor closure follows the explicit ownership path:

- application-created socket: application close callback or owner destruction;
- curl-created/internal fd: curl closes it, and any non-owning wrapper must release its native handle;
- cleanup callback: adapter state must remain valid for callbacks curl may issue during cleanup.

### Timer invariant

At most one current timer completion may call curl. Replaced, cancelled, or stale timer completions are inert.

### Completion invariant

After every successful `curl_multi_socket_action()` call:

1. drain `curl_multi_info_read()`;
2. observe any synchronous mask updates already delivered;
3. re-arm every still-requested direction with no current operation;
4. avoid recursive immediate-timeout calls from inside curl callbacks.

## Common integration mistakes

1. Treating `CURLMOPT_SOCKETFUNCTION` as a one-event subscription API.
2. Mapping deliberate cancellation to `CURL_CSELECT_ERR`.
3. Keying lifetime only by integer fd.
4. Equating `CURL_POLL_REMOVE` with close.
5. Starting duplicate read or write operations for one watch generation.
6. Re-arming before processing synchronous curl mask changes.
7. Keeping raw owner pointers alive only by convention while callbacks remain queued.
8. Calling curl recursively when the timer callback supplies zero milliseconds.
9. Assuming the easy handle passed to a socket callback identifies the sole user of that socket.
10. Assuming a decreased running-handle count identifies the transfer associated with the fd just processed.

## Review checklist

For a new integration, answer these questions with code and tests:

- Where is persistent desired interest stored?
- What exact event creates a replacement one-shot operation?
- How are obsolete operations invalidated?
- How is `operation_aborted` distinguished from a socket error?
- Can `INOUT` create independent read and write operations without duplicates?
- What object identity survives fd-number reuse?
- What happens on remove without close?
- Which component closes each class of descriptor?
- Can curl invoke the socket callback during cleanup while adapter state still exists?
- Is a zero timeout posted rather than executed recursively?
- Are completion messages drained after every action?
- Do tests force at least two readiness completions while curl's mask remains unchanged?

## Test progression

1. Cleartext split response requiring two reads.
2. Mask replacement with stale completion.
3. Deliberate cancellation.
4. `INOUT` independent completions.
5. Remove and re-add.
6. Forced fd-number reuse where practical.
7. Keep-alive second request.
8. Local TLS HTTP/1.1.
9. Local HTTP/2.
10. Resolver/Happy Eyeballs internal descriptors.
11. Cleanup with queued callbacks.

The first gate isolates the demonstrated persistence contract. Later gates establish lifecycle safety before product integration.

## Boundary

This note describes adapter conventions from current curl documentation, implementation, and examples. It does not claim that every event loop has identical triggering semantics, and it does not authorize changes or comments in curl or Ceph.
