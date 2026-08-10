# Stale-generation negative control

## TL;DR

The stale-fd lifecycle finding now has a passing broken-versus-generation-safe discriminator.

The broken model dispatches one action from a canceled old wait after the integer fd has been reused. The generation-checked model suppresses that old completion before any action is emitted.

This does not implement a Ceph patch. It verifies the specific decision rule proposed by `STALE_COMPLETION_RECEIPT.md`: an old wait must prove that its watch generation is still current before it can call `curl_multi_socket_action()`.

## Fixture

- Source: `experiments/curl-asio-multi-socket-rearm/asio-stale-generation-control.cpp`
- Commit adding source: `78149b8ab6082a7ff641f645d9912d49d25179ec`
- Executed source SHA-256: `a3cce5669a0edc9d931205b001e3bae89f79d899c552e7eba428a5cee1d4bfd9`

The fixture runs the same remove/reuse sequence twice:

1. **broken** — callback dispatches by saved integer fd regardless of generation;
2. **generation-safe** — removal increments the current generation and the old completion returns before dispatch when its captured generation no longer matches.

## Environment

```text
Linux 6.18.35 x86_64
g++ 14.2.0
Boost 1.83.0
```

## Command

```sh
g++ -std=c++20 -O2 -Wall -Wextra -pthread \
  experiments/curl-asio-multi-socket-rearm/asio-stale-generation-control.cpp \
  -o /tmp/asio-stale-generation-control
/tmp/asio-stale-generation-control
```

## Observed result

```text
broken: actions=1 aborted=1 fd_valid=1 stale_suppressed=0
generation-safe: actions=0 aborted=0 fd_valid=0 stale_suppressed=1
stale-generation discriminator: PASS
```

The executable returns success only when the broken branch emits the stale action and the generation-safe branch suppresses it.

## Interpretation

This gives the proposed generation check a negative control: the classifier can lose. The only semantic difference between the two cases is whether callback dispatch requires `wait_generation == current_generation` after the remove event invalidates the old watch.

For the reviewed Ceph carrier, this is the missing identity dimension around `socket_wait_handler`: saved integer fd plus mask are insufficient after remove/re-add or descriptor reuse.

## Evidence boundary

The fixture models the adapter lifecycle decision with the same Boost.Asio wait/release behavior demonstrated in `STALE_COMPLETION_RECEIPT.md`. It does not call libcurl and does not prove the final Ceph watch-object design, memory ownership, simultaneous `INOUT`, or cleanup behavior.

## Next step

Move the same discriminator one layer inward: drive `REMOVE -> re-add` through the reduced libcurl+Asio fixture so the broken branch reaches a recorded `socket_action()` while the generation-safe branch suppresses the stale completion and still completes the transfer.

## External-contact state

No upstream interaction was made.
