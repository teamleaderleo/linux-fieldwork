# Wayland resident listener native-thread boundary — 2026-08-14

## Scope

Carrier: `teamleaderleo/FEX` branch `diagnostic/wayland-resident-listener-20260814`, head `4fcfaeae9322a7abfb43e558563311b686ef03d2`.

Run `31786909159`, job `94724754019`, artifact `9213971075`, artifact SHA-256 `74629ec10ce0ad859e085bd7deae24c5dedea4804e226610a8590983471a0fff`.

The carrier compared the existing local Wayland listener unpacker with a `NODELETE` resident `u`-listener unpacker companion.

## Build result

Both variants built. The resident candidate had the intended ELF ownership split:

- ordinary `libwayland-client-guest.so` remained unloadable;
- it had `NEEDED` on `libfex-wayland-client-bridge.so`;
- the bridge had `DF_1_NODELETE`.

## Runtime result

```text
local=139
resident=139
```

Neither arm reached the first expected guest callback marker (`WAYLAND_PRE_CLOSE count=1 value=41`). The only probe marker before failure was the initial wrapper lookup/mapping line.

## Failure owner

The test hook invokes the retained listener from a detached native `std::thread` created in the host Wayland thunk:

```cpp
std::thread {[test_callback, data, proxy]() {
  std::this_thread::sleep_for(std::chrono::milliseconds(100));
  test_callback(data, proxy, 41);
  ...
}}.detach();
```

FEX's host-to-guest callback path uses thread-local `ThreadObject` state and explicitly rejects a thunked library callback on a native thread that has no registered guest/FEX thread state.

Therefore the carrier crosses a separate unsupported/native-thread callback boundary before guest unpacker lifetime becomes relevant. Moving the unpacker into a resident companion cannot supply the missing FEX thread context.

## Interpretation

This run is not evidence against resident listener unpackers. It is a discriminator for callback thread provenance.

A valid Wayland lifetime test should drive the native listener on the same FEX-managed thread that entered the host API, matching ordinary Wayland dispatch behavior, then close/unmap the guest wrapper between retained invocations without manufacturing a detached host thread.

Until such a carrier runs, Wayland stays outside the positive resident-lifetime evidence set. DRM remains the real nested callback aggregate proof.
