# FEX thunk lifetime: owner generation and selected-block race log — 2026-08-14

## Resume point

This checkpoint resumes after the real-Vulkan PFN repair work, hosted `vulkaninfo` teardown reconstruction, and the address-reuse owner-lifetime discriminator.

The hosted x86-64 `vulkaninfo` reconstruction on ARM64 Actions exits 0 in stock and lifetime-candidate matrices. That environment therefore does not reproduce the original field exit-139. The lifetime diagnostics still prove that the Vulkan guest thunk unload retires hundreds of registered dynamic links, while pinning the guest thunk suppresses those retirements. The original exit-139 remains environment/order-sensitive; the lower-level real-FEX stale-PFN experiments remain the causal reproductions.

## Completed owner-lifetime experiments recovered from the FEX fork

### Pre-destructive MAP_FIXED retirement

Carrier: `teamleaderleo/FEX` branch `ci/map-fixed-pre-retire-20260814`

Run: `31780286007`

Result:

- current candidate, replacement at the same numeric `T`, no new registration: stale `H` reaches generation-2 code and returns `222`;
- pre-retirement candidate, replacement at the same numeric `T`, no new registration: `H` is revoked/tombstoned and the deliberate stale call exits 139;
- pre-retirement candidate plus explicit `LinkAddressToFunction(H, T)` after replacement: `H` legitimately returns `222`.

This is the A/B/C causal discriminator for destructive address reuse.

### Transactional rollback when MAP_FIXED fails

Carrier: `ci/map-fixed-rollback-transaction-20260814`

Run: `31781459145`

Artifact: `map-fixed-rollback-transaction-31781459145`

Observed matrix:

```text
rollback-map-fixed-fail=0
rollback-map-fixed=139
rollback-map-fixed-reregister=0
```

The failed destructive request uses an invalid file-backed `MAP_FIXED` (`fd=-1` without `MAP_ANONYMOUS`) and receives `EBADF`. The candidate prepares retirement, retires `H`, sees the syscall fail, restores the saved claims/active target, and the same `H` returns `111` again. Successful replacement commits retirement. Explicit re-registration after successful replacement returns `222`.

This establishes the need for prepare/commit/rollback semantics around destructive operations whose kernel result can fail.

### VMA owner ID / generation

Carrier: `ci/vma-owner-id-20260814`

Run: `31782618792`

Result:

- permission-only `mprotect` transitions preserve the mapping owner ID;
- successful destructive `MAP_FIXED` replacement at the same VA receives a new owner ID;
- owner identity is therefore tied to a mapping lifetime, not the numeric address.

### Retained thunk claim bound to owner ID

Carrier: `ci/thunk-owner-claim-id-20260814`

Run: `31783294674`

Artifact: `thunk-owner-claim-31783294674`

Observed matrix:

```text
claim-map-fixed-fail=0
claim-map-fixed=139
claim-map-fixed-reregister=0
claim-mprotect-owner=0
```

Each retained `H -> T` claim now records `{Target, OwnerID}`. The ABA replacement test registers the same numeric H and T twice across two mapping lifetimes and captures distinct owner IDs. The `mprotect` mutation test keeps the same owner ID and the existing H remains valid after RX -> RW -> RX, returning the newly written `333` from the same mapping lifetime.

### Multi-owner promotion precedent

Carrier: `ci/thunk-multiowner-promotion-20260814`

Run: `31769613134`

A single native host address H can have claims from multiple guest owners. With A active and B retained as standby, unloading A retires the compiled H bridge, drops A, promotes B, and B continues successfully. The final B unload retires H completely.

Consequence: lifetime control must operate on a selected claim/target owner, not treat H as a single immortal association.

## New experiment: selected compiled H survives retirement

Carrier created: `ci/thunk-inflight-selected-race-20260814`

Files added:

- `.github/fieldwork/add_inflight_selected_pause.py`
- `diagnostics/thunk-inflight-race/thunk_inflight_race.cpp`
- `.github/workflows/thunk-inflight-selected-race-arm64.yml`

### Race point

The ARM64 dispatcher normally loads a compiled host block pointer from the lookup cache and branches to it. Exact eviction can erase future cache hits after that pointer has already been loaded.

The diagnostic patch adds an opt-in pause only for synthetic `H = 0x700000020000`:

1. warm H so a compiled H block exists;
2. arm the diagnostic pause;
3. worker thread looks up H and loads its compiled host block;
4. dispatcher records `DIAG_INFLIGHT_SELECTED` and pauses before `br`;
5. controller thread performs destructive `MAP_FIXED` over T;
6. owner-aware retirement revokes H and replacement T becomes generation 2 with sentinel `222`;
7. controller releases the paused worker;
8. worker branches through the already-loaded compiled H pointer.

No explicit re-registration occurs.

### Discriminator

If the worker returns `222`, future-lookup eviction is insufficient for an already-selected compiled H: the old H block can still exit toward the numeric T after T belongs to a new owner generation.

A later repair should prevent a selected old-owner claim from beginning/continuing dispatch after that owner enters retirement. Candidate semantics to test after reproduction:

- claim states `ACTIVE -> RETIRING -> REVOKED`;
- new selections rejected once `RETIRING` begins;
- selected/in-flight dispatch carries an owner/claim lease or epoch;
- destructive owner teardown waits for, cancels, or redirects in-flight selections before the guest mapping can be reused;
- promotion to a different live claim at the same H remains legal only for dispatches selected after the transition.

## Current status

The carrier branch and deterministic race fixture are pushed. Initial Actions polling immediately after the workflow-file push returned no queued run, so that is recorded as orchestration status only. The next action is to trigger/poll the new lane, retain any compile/harness failure receipt, repair the carrier as needed, and rerun until the race discriminator itself executes.
