# Callback in-flight race v2 marker failure — 2026-08-14

## Scope

Carrier `teamleaderleo/FEX` branch `ci/callback-inflight-unmap-race-v2-20260814`, head `e39753166a2110b0da6713ed834773a184110beb`.

Run `31787095309`, job `94725341826`, artifact `9214026305`, artifact SHA-256 `c4c19d97035429f8c8033eb3178b62147621f740676d40eb1bc12a6f3a66c3c1`.

## Result

The v2 repair replaced absolute `/tmp/...` synchronization markers with relative files under the fixture working directory. Both arms still failed before the intended barrier:

```text
pin=81
unmap=81
pre-unload host->guest callback  rv=10053 want=10053
FAIL: callback worker never reached FEX in-flight barrier
```

FEX, tombstone instrumentation, and the threaded fixture all built successfully. The ordinary pre-unload callback remained healthy.

## Interpretation

Relative pathname equality still does not provide a shared synchronization namespace between guest file syscalls and native FEX host file operations in this launch arrangement. The previous absolute-path diagnosis was directionally correct—filesystem markers are a poor cross-boundary synchronization primitive here—but changing to cwd-relative names is insufficient.

This remains a carrier failure and gives no evidence for or against survival of an already-entered callback across owner unmap.

## Next carrier

Remove filesystem synchronization entirely.

Use FEX-internal state:

1. count callback entries in `ThunkHandler_impl::CallCallback`; the fixture's known pre-unload registration call is entry 1 and the race worker is entry 2;
2. pause entry 2 inside FEX after the raw guest unpacker/target have been selected;
3. have the guest main thread begin the destructive `dlclose` after its worker has started and a conservative delay;
4. in `ThunkHandler_impl::RetireGuestRange`, release the paused callback only after the retiring range has matched the callback's target or unpacker and the stable host trampoline has been tombstoned;
5. verify log ordering `INFLIGHT_SELECTED -> TOMBSTONE -> INFLIGHT_RESUME` and verify the guest target/unpacker mappings were gone before resume.

For the pin control, allow a bounded FEX-side pause to expire without retirement and require the callback to return normally. This keeps the experiment independent of guest/host filesystem path translation.
