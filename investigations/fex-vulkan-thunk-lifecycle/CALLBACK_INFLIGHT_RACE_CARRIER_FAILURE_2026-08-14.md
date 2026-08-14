# Callback in-flight race carrier failure — 2026-08-14

## Scope

Carrier: `teamleaderleo/FEX` branch `ci/callback-inflight-unmap-race-20260814`, head `b8d10d0455f2ad05bb37daba7d5169184145ba13`.

Exact FEX product under test: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Retained fixture source: `teamleaderleo/linux-fieldwork` commit `9eca19ac8743567ce2af7b4c82f2483d97c19b09`, archive SHA-256 `0582bf8832699cfb2614c1781473d07054ba01f03e3342735a45ea04735c2a01`.

GitHub Actions run: `31785292383` (`Callback in-flight unmap race ARM64`).

## Intended discriminator

Pause an already-entered host-to-guest callback inside FEX `ThunkHandler_impl::CallCallback`, after the raw guest unpacker/target values have been selected, then either:

- keep the guest DSO pinned and resume, expecting a normal callback return; or
- `dlclose` the guest DSO, allow the existing callback-tombstone diagnostic to retire future entries, prove the target/unpacker mappings disappeared, and resume the already-entered call.

This would distinguish future-entry retirement from an execution lease needed by an in-flight callback.

## Actual result

Both arms failed before reaching the intended barrier:

```
pin=81
unmap=81
```

Both produced:

```
pre-unload host->guest callback  rv=10053 want=10053
FAIL: callback worker never reached FEX in-flight barrier
```

The FEX patch applied cleanly, FEX and the fixture compiled, and the ordinary pre-unload callback path remained healthy. The failure is therefore carrier/trigger placement, not evidence for or against the execution-lease hypothesis.

## Interpretation

The worker callback did not execute the patched `CallCallback` barrier path under the race mode. The experiment cannot classify the in-flight unmap race yet.

The likely causes to discriminate are:

1. the worker thread enters a callback path without the file-based arm condition visible where expected;
2. the pause patch landed in a `CallCallback` site that the fixture's callback trampoline does not use at runtime;
3. FEX thread/TLS registration or callback-thread routing diverts the worker before the instrumented line;
4. the fixture's worker call never reaches the retained host trampoline because the race-mode synchronization is earlier than assumed.

## Next step

Instrument successive boundaries with unique one-shot markers: guest worker before thunk call, host thunk `host_call_first_callback`, host trampoline packer, and FEX `CallCallback` entry. Use the first missing marker to place the barrier exactly. Preserve the tombstone machine-template ABI unchanged.
