# FEX thunk-lifetime investigation: current leads and provenance map — 2026-08-14

Status: housekeeping snapshot for the owned Fieldwork/FEX investigation.

Snapshot base:

- `teamleaderleo/linux-fieldwork`
- `investigation/fex-vulkan-thunk-lifecycle`
- `5a4833a817218e0bee8cf6797cbad47916561bba`

This note is a navigation aid over the experiment set. Every existing branch, receipt, failed carrier, and older proposal remains useful provenance and stays recoverable. Labels here are provisional: they describe which evidence is carrying the argument today and which experiments now feed that evidence indirectly.

Upstream contact remains outside this checkpoint.

## Current best leads

### 1. Immediate containment: selective guest-wrapper `NODELETE`

The narrow containment policy remains strong: keep a guest thunk wrapper resident when that wrapper publishes executable guest addresses into FEX/native state whose lifetime can exceed the wrapper's ordinary loader reference.

The FEX-2608 source audit identifies the current selective set as:

```text
NODELETE: vulkan, GL, cuda, wayland-client
normal:   EGL, drm, asound, VDSO
```

That audit should remain a source-surface snapshot, because generator capabilities are evolving during this investigation. In particular, generated nested callback mediation now reaches DRM and CUDA aggregate members in experimental paths. As those paths become production candidates, their lifetime classification should be re-audited from the generated escape set rather than inherited permanently from an older wrapper configuration.

Current role: **small review-surface containment and useful A/B control.**

### 2. Unload-preserving design: first-class per-library resident thunkgen companion

The strongest long-term lead is now the first-class thunkgen resident output produced from the same semantic analysis as the ordinary guest wrapper.

The current generator direction is:

1. run normal interface analysis once;
2. deduplicate runtime function-pointer signatures once;
3. emit the ordinary unloadable wrapper;
4. emit resident guest-to-host invokers for the runtime function-pointer set;
5. emit resident host-to-guest unpackers only for signatures thunkgen identifies semantically as callbacks;
6. have the wrapper use typed generated accessors into the resident companion;
7. keep custom raw escape points explicit where ordinary analysis cannot see them.

GL is the strongest first-class generator/runtime carrier. Its ordinary wrapper physically unmaps while the resident companion remains executable, retained PFNs survive close and moved reload, and the retained GLX/X11 path remains callable. Direction-aware generation reduced the resident GL product substantially while preserving the full guest-to-host signature set.

The dedicated positive callback-direction control generates exactly one resident unpacker for one ordinary generated callback parameter. Together with GL/Vulkan zero-callback cases, this supports semantic direction analysis over the temporary arity heuristic.

Current role: **primary unload-preserving implementation direction.**

### 3. CUDA: now positive resident-lifetime evidence after an isolated A/B

The earlier CUDA `139/139` comparison used an invalid runtime scope: both arms could resolve the same rootfs-local wrapper, so it is retained as a carrier-hygiene lesson rather than a resident-bridge verdict.

The replacement run `31787821035` isolates local and resident arms on fresh matrix runners.

Local arm:

```text
wrapper physically unmapped after close
forced reload moved=1
deferred native launch entered
FEX exit=139
retained guest callback was not delivered
```

Resident arm:

```text
wrapper physically unmapped after close
forced reload moved=1
wrapper has NEEDED libfex-cuda-bridge.so
bridge has NODELETE
normal_unique_signatures=364
bridge_unique_signatures=364
CUDA_RETAINED_CALLBACK count=1 user=0x12345678
launch2-return rc=0 callbacks=1
FEX exit=0
```

This is a useful independent API-family confirmation because the callback is carried inside CUDA host-node state and invoked later by the synthetic native endpoint. The earlier DRM result remains the first generated nested aggregate proof; CUDA now adds a moved-reload retained-callback lifetime A/B.

Current role: **strong positive cross-library evidence for the resident companion.**

### 4. Generated nested callback members: DRM + CUDA

The `callback_member` work has moved from a one-library experiment into a reusable generator rule.

DRM demonstrated generated nested callback conversion and resident callback signatures with real guest callback delivery. CUDA then applied the same semantic member annotation to `CUDA_HOST_NODE_PARAMS_st` and produced:

```text
native=0
pristine_reference=132
generated_candidate=0
```

The generated guest path copies caller-owned aggregate input and replaces only the annotated callback field; the host side finalizes the corresponding trampoline. This pairs naturally with first-class resident output: the aggregate conversion can remain generated while executable callback adapters receive the lifetime appropriate to their escape behavior.

Current role: **generator capability feeding the resident-companion design.**

### 5. Application callback ownership: transactional drain/commit/rollback, with wait-on-Draining

The callback-lifetime work has progressed through several useful layers:

- stable descriptor identity;
- revoke future entries;
- drain active execution before reclaiming callback target/state;
- make VM retirement transactional so a failed `munmap` restores callback liveness;
- make new callback acquisitions wait while retirement is in `Draining`, then resolve according to commit versus rollback.

The latest deterministic three-thread A/B is decisive for the waiting rule:

```text
immediate-reject baseline = 113
wait-on-Draining          = 0
```

On failed unaligned `munmap`, callback B waits for callback A to drain; rollback restores `Live`; B then acquires and executes. A later valid close commits permanent revocation.

Current state-machine lead:

```text
Live
  acquire -> Active++

BeginDrain
  Live -> Draining
  new acquisitions wait
  wait Active == 0

host VM operation

success:
  Draining -> Revoked
  wake waiters -> reject

failure:
  Draining -> Live
  wake waiters -> acquire normally
```

Remaining high-value stress areas are overlapping retirement transactions and the wider VM operation set, especially fixed replacement/move behavior.

Current role: **primary application-callback ownership model for the observed `munmap` path.**

### 6. Future dispatch and in-flight H->T redirects: owner generation has become central

Exact CustomIR/synthetic mapped-block retirement and all-thread cache eviction remain useful for future dispatch after a mapping changes.

A deeper ABA carrier established an additional boundary: an already-running compiled H redirect can pause before selecting T, the old T owner can be replaced by a new generation at the same numeric guest VA, and the old H invocation can then execute the new generation. Cache eviction cannot retract an H invocation already in progress.

That points toward owner-generation identity in the H->T transition itself, with a descriptor/claim such as:

```text
{ H, T, OwnerID, state }
```

A token/lease or equivalent validity check may be needed across the final validation-to-transfer window.

Current role: **primary lead for generation-safe H->T transitions; complementary to cache retirement.**

### 7. VM replacement operations: treat ownership and translated-code retirement together

`MREMAP_FIXED` exposed two overlapping effects at the destination address:

- the old destination owner claim can survive replacement;
- translated destination code can remain stale even after source bytes move onto that numeric VA.

The current model prepares retirement for affected old source/destination ranges, commits claim/code retirement when the kernel move succeeds, and restores prepared ownership when it fails. Source owner identity may follow the mapping to its new address, while concrete callback/thunk claims tied to old addresses still retire.

This fits naturally beside the callback transaction work. It should remain a separate VM-lifetime lane until the rules for shrink, grow, fixed move, ordinary move, and fixed mapping replacement are all explicit.

Current role: **active VM-owner semantics lane.**

### 8. Vulkan allocator work: generic const-repack fix is proven; allocator semantics remain their own lane

The allocator investigation isolated a generic thunkgen bug: repack generation stripped pointee constness, causing temporary host-layout data to be copied back over caller-owned `const T*` input. Preserving source pointee constness makes the existing repack wrapper skip that writeback.

The focused generator regression and Vulkan buffer/event runtime matrix pass with that generic correction. This is now the preferred fix for the input-corruption defect.

Allocator callback mediation still carries API ownership/identity semantics beyond this one generator bug. Keep those experiments beside the lifetime work, while avoiding folding allocator-specific rules into the resident signature-adapter policy.

Current role: **generic thunkgen bug with a proven focused repair, plus a separate allocator-semantics follow-up lane.**

### 9. Wayland: valuable open discriminator, with one carrier boundary already identified

A Wayland resident-listener carrier initially produced `local=139 / resident=139` before the first guest callback marker. The carrier invoked the retained listener from a detached native `std::thread`. FEX's host-to-guest callback path requires FEX-managed thread-local guest state, so both arms crossed the native-thread provenance boundary before unpacker lifetime became relevant.

This result is useful because it prevents a false general conclusion about the resident companion. The next Wayland lifetime carrier should invoke retained listeners through ordinary same-FEX-thread dispatch behavior, close/unmap the public wrapper between invocations, and then compare local versus resident callback machinery.

Current role: **open custom-listener discriminator; current detached-thread result retained as carrier-boundary evidence.**

## Experiments now best treated as supporting or historical provenance

### Python resident-bridge extractor

The extractor-derived GL/Vulkan/CUDA work was essential proof that splitting executable adapters from the unloadable wrapper could work. First-class `RESIDENT_BRIDGE` generation from thunkgen analysis now carries the production argument more directly.

Housekeeping label: **superseded as implementation direction; retained as mechanism/provenance proof.**

### Arity-based callback-unpacker heuristic

The temporary arity filter helped turn eager resident output into something buildable. Direction-aware semantic analysis now has both zero-case and positive-case controls.

Housekeeping label: **superseded by semantic callback-direction analysis; retained as intermediate evidence.**

### Early callback pin/revoke variants

The early pinning, revocation, tombstone, and descriptor experiments established separate failure boundaries. The current callback transaction model incorporates the useful pieces: identity, active execution accounting, draining, commit/rollback, and wait-on-Draining.

Housekeeping label: **feeding evidence for the current transaction state machine.**

### Contaminated CUDA `139/139` runtime comparison

The run exposed a rootfs/scope contamination problem and triggered the isolated-matrix repair. The isolated run now carries the runtime comparison.

Housekeeping label: **superseded as CUDA lifetime result; retained as CI/carrier hygiene evidence.**

### Repeated Vulkan retained-PFN variants

These experiments established physical unload, retained call behavior, moved reload, native-H identity, X11 callback survival, `NODELETE` behavior, and the split-companion concept. The core hypothesis has broad coverage now.

Housekeeping label: **validation/regression pool. New Vulkan PFN variants earn priority when they test a new ownership, namespace, packaging, bitness, or concurrency boundary.**

### Base-namespace promotion / self-pin / loader-policy alternatives

These controls remain useful because they map loader semantics and failure cases. The current near-term containment is selective `NODELETE`, and the current unload-preserving lead is the generated resident companion.

Housekeeping label: **alternative-policy provenance and regression controls.**

### Earlier callback-policy branches

`investigation-fex-vulkan-host-callback-lifetime`, `investigation-fex-vulkan-host-callback-lifetime-notes`, and the later `investigation/fex-host-callback-target-lifetime-v2` each capture useful steps in the ownership argument. The v2 selective `NODELETE` audit remains directly useful for immediate containment; the older callback lifetime notes feed the newer transactional owner model.

Housekeeping label: **retain all; use the newest transactional evidence for current callback implementation discussion.**

## Highest-value next experiments

1. **Production-layout resident companion packaging.** Build/install through FEX's normal GuestThunks path and prove the wrapper resolves its private companion in the installed/rootfs layout.
2. **Wayland same-thread retained-listener lifetime A/B.** Remove the detached native-thread confound and exercise close/unmap between callbacks.
3. **H owner-token/claim descriptor carrier.** Validate owner generation at the H->T transition, then pause after validation to test whether a lease/epoch is required through transfer.
4. **Overlapping callback retirement transactions.** Exercise intersecting success/failure outcomes and verify drain counters/state transitions remain coherent.
5. **Wider VM transaction semantics.** Continue `MREMAP_FIXED`, `MAP_FIXED`, move, shrink, and rollback cases with both code-cache and owner-claim assertions.
6. **Allocator identity/ownership follow-up.** Keep the proven const-repack repair as the baseline and isolate any remaining callback/trampoline lifetime semantics separately.
7. **32-bit resident output runtime where practical.** Existing 32-bit build probes are useful gates; a callback-bearing runtime carrier would give stronger behavioral coverage.

## Revisit triggers

The current ordering should change if any of these occurs:

- normal GuestThunks packaging cannot locate or retain the private companion cleanly;
- a same-thread Wayland carrier shows a resident callback failure after eliminating thread-provenance confounds;
- owner-generation validation requires substantially different machinery from the descriptor/claim model;
- measured resident companion cost becomes large enough to favor a different granularity;
- an API's custom callback semantics require ownership behavior that cannot be represented by generated signature adapters plus explicit application-callback descriptors.

## Working summary

The investigation has converged into several cooperating lanes instead of one universal lifetime switch:

- **selective wrapper `NODELETE`** for immediate containment;
- **first-class per-library resident thunkgen companion** for FEX-owned executable adapters that escape wrapper lifetime;
- **semantic `callback_member` generation** for nested callback-bearing aggregates;
- **transactional callback descriptors with drain/wait/commit/rollback** for application-owned callback targets;
- **owner-generation-aware H->T transitions plus cache retirement** for code-generation reuse;
- **transactional VM owner/code retirement** for fixed replacement and move operations;
- **separate API-semantic lanes** for allocator and custom listener behavior.

Older experiments remain valuable because they tell us why these lanes exist and which tempting shortcuts fail under specific conditions. The practical housekeeping rule from here is to spend new experiment budget on a fresh boundary, regression, or packaging question, while using the existing branches as the evidence ladder behind the current leads.