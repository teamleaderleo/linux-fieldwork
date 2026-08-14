# FEX thunk lifetime: in-flight concurrency boundary — 2026-08-14

## Existing FEX in-flight translated-target race recovered

Two retained ARM64 Actions runs already force an in-flight target selection during thunk-owner teardown:

- `teamleaderleo/FEX` branch `ci/thunk-inflight-selection-race-20260814`, run `31770286056`, product `71afe476751deac24adabd1adb575fd2337b6e0a`;
- `ci/thunk-inflight-selection-race-f3ab-20260814`, run `31770635557`, product `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

The diagnostic barrier is in `Arm64JITCore::ExitFunctionLink` after FEX has selected `HostCode` for guest `T1` and after the lookup/code-invalidation guards have been released. The worker is therefore paused with a real translated host block already selected for `T1`.

Observed on both product revisions:

```text
pin=0
unmap=139
```

Unmap case, current-main receipt:

```text
inflight target                  T1=0x00007ffff7da21b0 H=0x00007ffff7d80860 pin=0
inflight selected                T1=0x00007ffff7da21b0
inflight old invoker after dlclose 0x00007ffff7da21b0 -> unmapped
inflight owner unmapped before resume
DIAG_INFLIGHT_SELECTED guest=0x7ffff7da21b0 host=0x80006c1c46b4
DIAG_MT_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=...
DIAG_MT_THREAD H=0x7ffff7d80860 thread=...
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
DIAG_MT_RETIRE_ALL H=0x7ffff7d80860 thread=...
DIAG_INFLIGHT_RESUME guest=0x7ffff7da21b0 host=0x80006c1c46b4
timeout: the monitored command dumped core
```

Pin control:

```text
inflight selected                T1=0x00007ffff7da21b0
inflight pin keeps owner mapped before resume
DIAG_INFLIGHT_RESUME guest=0x7ffff7da21b0 host=...
inflight worker returned         rv=1023 want-old=1023 owner-was-mapped
```

This proves exact cache eviction and handler retirement cannot retract a translated block pointer that another thread already selected.

## Native control: raw DSO pointer selected before dlclose

Carrier: `teamleaderleo/FEX` branch `ci/native-dlclose-inflight-baseline-20260814`

Run: `31785390500`

Artifacts:

- `native-dlclose-inflight-amd64-31785390500`
- `native-dlclose-inflight-arm64-31785390500`

Standalone native fixture timeline:

1. `dlopen` a trivial owner DSO;
2. `dlsym` a function returning `1023`;
3. worker captures the function pointer and announces `selected` immediately before the call;
4. controller either pins the DSO or calls `dlclose`;
5. unmap case verifies `/proc/self/maps` no longer covers the selected function pointer;
6. worker resumes and calls the captured pointer.

Observed on native x86-64:

```text
arch=amd64
pin=0
unmap=139
```

Observed on native ARM64:

```text
arch=arm64
pin=0
unmap=139
```

Both unmap receipts reach:

```text
NATIVE_INFLIGHT selected target=...
NATIVE_INFLIGHT owner-closed mapped=0
NATIVE_INFLIGHT resume target=...
timeout: the monitored command dumped core
```

Both pin receipts return `1023` and exit 0.

## Interpretation

The forced sequence "thread has already selected a raw code target; another thread destroys the target's DSO mapping; first thread resumes the stale target" has the same failure mode on native Linux and under FEX.

Therefore FEX should not acquire a global stop-the-world guarantee merely to keep an already-entered or already-selected raw DSO function pointer alive after application teardown. Doing so would extend pointer lifetime beyond the native baseline and add synchronization to a sequence whose native result is already a stale-code fault.

The FEX-specific lifetime work remains focused on associations FEX creates or retains itself:

- `H -> T` dynamic thunk claims must retire when their guest owner generation dies;
- future lookups of H must lose old-owner associations;
- destructive same-address reuse must never make an old claim silently bind to a new mapping generation;
- multiple guest owners for the same H require active-claim retirement and promotion of still-live claims;
- failed destructive syscalls require rollback of prepared retirement.

## Distinct pending race: FEX-selected H across owner-generation reuse

A separate carrier, `ci/thunk-inflight-selected-race-20260814`, pauses the ARM64 dispatcher after it has loaded the compiled host block for synthetic `H = 0x700000020000`, then performs owner-aware destructive `MAP_FIXED` over T and installs generation-2 code returning `222` before resuming that already-selected H block.

This test asks a narrower FEX-specific question: can an already-selected compiled H, whose custom IR embeds numeric T, silently cross from owner generation 1 into owner generation 2 after retirement and exact eviction?

The first Actions attempt, run `31785024613`, failed during probe compilation before candidate application or execution. The retained harness errors were:

```text
common/Guest.h:99:22: error: missing initializer ... [-Werror=missing-field-initializers]
thunk_inflight_race.cpp:38:16: error: ignoring return value of write ... [-Werror=unused-result]
```

Base FEX built successfully. Candidate application and race execution were skipped. The carrier was repaired by checking the barrier `write` result and locally suppressing the unrelated FEX guest-header warning around `common/Guest.h`. A rerun is queued from commit `ff3389adc389967da9e334e739d86e1b71706b67`.

## Decision boundary

If the selected-H ABA lane returns `222` with no explicit re-registration, that remains a FEX-specific generation-crossing bug even though the raw-DLO function-pointer race matches native behavior. The reason is that FEX itself created and retained H's compiled redirection, then allowed it to target a different mapping lifetime at the same numeric T.

A repair for that case can stay local to dynamic thunk-claim validity. It does not need to guarantee arbitrary guest code survival after concurrent `dlclose`.
