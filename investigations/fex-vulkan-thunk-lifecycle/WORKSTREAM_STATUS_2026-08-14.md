# FEX thunk-lifetime workstream status — 2026-08-14

Status: internal readiness checkpoint. This is a dated navigation aid, not a closure document and not an upstream proposal.

Snapshot base:

- repository: `teamleaderleo/linux-fieldwork`
- active investigation branch: `investigation/fex-vulkan-thunk-lifecycle`
- snapshot commit: `a57468c3055332b5c965454eec9438ac4927f008`

Existing experiments, failed carriers, alternate hypotheses, and older notes remain retained as provenance. The labels below mean only how much additional reduction/refinement seems useful before a human tries to learn and rewrite the candidate front to back.

## At a glance

| Workstream | Current stage | Strongest evidence now | Main remaining gate |
|---|---|---|---|
| Const-preserving repack | **candidate-ready for internal human study** | minimal two-file candidate + focused generator regression + Vulkan buffer/event causal runtime proof | ordinary review/rebase polish; optional current-main confirmation |
| Selective wrapper `NODELETE` | **small candidate; evidence mature** | explicit four-library candidate + source ownership audit + extensive loader/lifetime A/B pool | one clean candidate-branch validation/footprint receipt and policy review |
| `callback_member` | **mechanism proven; candidate packaging still refining** | independent DRM and CUDA aggregate callback proofs | reduce diagnostic transforms to a minimal standalone generator patch/test set |
| Resident per-library companion | **design/evidence mature; implementation convergence active** | GL/Vulkan/CUDA/Wayland lifetime results + per-library ownership inventory + caller/unpacker role contract | finish direct role-aware thunkgen output, installed GuestThunks packaging, remaining 32-bit/custom hooks |
| Application callback lifetime | **`munmap` path semantically mature; wider generalization active** | deterministic descriptor/drain + failed-unmap rollback + wait-on-Draining three-thread A/B | overlapping transactions and wider VM-operation integration |
| H→T owner-generation lifetime | **diagnosis mature; first repair implementation not yet exercised** | deterministic old-H same-address generation-crossing ABA proof | repair carrier must compile/run; then test post-validation race window/lease need |
| VM replacement semantics | **diagnosis mature; repair rules still being decomposed** | clean `MREMAP_FIXED` split proof for stale translated code + stale owner claim | implement transaction rules and separately cover fixed map, move, shrink/grow, rollback |

The six-project mental model still holds: the two thunkgen items are subparts of the generator workstream, while H→T and VM replacement remain distinct lifetime layers even though they interact.

## 1. Guest-thunk executable lifetime / resident companion

### What is established

The central invariant has survived independent API families: executable guest adapters that escape into longer-lived FEX/native state cannot safely inherit the unload lifetime of the ordinary public guest wrapper.

Current per-library evidence includes:

- Vulkan dynamic PFN callers across real close and forced moved reload;
- Vulkan persistent X11 callback unpackers;
- GL's 736 runtime-PFN caller signatures, retained calls, and retained GLX/X11 callbacks after wrapper unmap;
- DRM generated nested callback members;
- CUDA generated nested callback members plus an isolated deferred-callback moved-reload A/B where wrapper-local executable ownership exits 139 and resident ownership exits 0;
- Wayland retained-registration-only same-thread moved-reload behavior and a generalized 41-signature 64-bit listener dispatcher build/runtime path.

The implementation-oriented ownership inventory now makes the intended granularity explicit: one private process-resident companion per affected thunk library, containing only executable families that can escape. Ordinary API packers, mutable wrapper state, loader state, and unrelated code stay in the unloadable wrapper.

Thunkgen's desired role model is also clearer than earlier prototypes:

```text
needs_caller
needs_unpacker
```

A canonical function-pointer signature can need either role or both. GL and Vulkan provide large caller-only sets; ordinary callback parameters and `callback_member` provide unpacker cases; overlap must OR the roles rather than infer them from arity.

### What is still moving

The latest direct role-output carrier is still implementation-red. Its current failure is a compiler error in a diagnostic `report_error` source-location expression, before the intended role/accessor validation runs. That is a carrier/code defect, not evidence against role separation.

Remaining production-oriented gates:

1. make direct role-aware thunkgen bridge/accessor generation green and remove residual prototype transforms;
2. prove normal installed `GuestThunks` packaging/rootfs discovery for the private companion;
3. finish 32-bit coverage, especially Wayland's separate `wl_array` relocation callbacks;
4. keep custom escaped targets explicit where API semantics cannot be inferred from the type system;
5. measure/record resident cost sufficiently for maintainer policy discussion.

### Readiness judgment

**Do not freeze this for human rewrite yet.** The design argument is mature enough to study, but the implementation surface is still simplifying. A later human review will be easier after the role-output and packaging work settle.

## 2. Immediate selective `NODELETE` containment

### What is established

A small concrete FEX candidate exists. `add_guest_lib(... NODELETE)` applies `LINKER:-z,nodelete` to shared guest wrappers and currently marks:

```text
vulkan
GL
cuda
wayland-client
```

The independent source audit reaches the same set for the narrow rule “wrapper-owned executable addresses escape beyond ordinary wrapper loader lifetime.” DRM, EGL, asound, and VDSO are not included by that rule.

Many surrounding experiments already establish loader behavior, physical wrapper lifetime, callback/PFN survival, namespace caveats, and why base-namespace self-pinning is weaker than ELF `NODELETE`.

### What is still moving

The candidate branch itself has no dedicated Actions run. Before treating it as a polished internal candidate, useful cleanup would be:

- run one compact build/runtime policy matrix directly from the candidate branch;
- retain an ELF assertion for the intended four wrappers and negative assertions for unaffected wrappers;
- include a concise footprint/residency receipt;
- phrase the proposal explicitly as containment, not as a replacement for the resident-companion design or application-callback ownership.

### Readiness judgment

**Near-ready for human study.** The code is tiny and the causal rationale is stable. Most remaining burden is packaging the evidence and deciding whether maintainers would want the containment independently.

## 3. Application callback lifetime

### What is established

For the observed loader `munmap` path, the state machine now has deterministic executable coverage:

```text
Live
  acquire -> Active++

BeginDrain
  Live -> Draining
  new acquisitions wait
  wait Active == 0

host munmap

success:
  Draining -> Revoked
  wake waiters -> reject

failure:
  Draining -> Live
  wake waiters -> acquire normally
```

Evidence separately demonstrates:

- revocation alone cannot reclaim an in-flight callback safely;
- active execution drain is required before target/state reclamation;
- eagerly revoking before a failed `munmap` creates a false tombstone;
- transactional rollback restores a still-mapped callback to `Live`;
- callbacks arriving during `Draining` should wait for commit/rollback rather than fail immediately;
- a later valid close commits permanent revocation and leaves escaped stale host trampolines as safe revoked tombstones.

### What is still moving

This has not yet become a general VM-lifetime implementation. High-value remaining work:

- intersecting/overlapping retirement transactions with mixed success/failure;
- interaction with `MAP_FIXED`/`mremap` replacement;
- lock ordering and wakeup rules after reducing diagnostics into production code;
- deciding the exact ownership boundary between a process-resident FEX adapter and independently unloadable application callback target/userdata.

### Readiness judgment

**Semantics mature for one important path; implementation still research-grade globally.** It is worth studying as a state-machine argument later, after overlap/wider-VM cases either confirm it or force a refinement.

## 4. H→T / CustomIR owner-generation lifetime

### What is established

Exact cache retirement/all-thread eviction fixes future dispatch after an H mapping claim changes, but a deterministic ABA carrier proves that is insufficient for an H invocation already underway.

The carrier starts an old compiled H redirect, pauses before target selection, replaces T with a new mapping owner at the same numeric guest VA, retires the old claim, performs no H re-registration, and then resumes. The old H invocation executes generation 2 (`222`).

Therefore numeric T is not enough identity for the H→T transition. The leading repair concept carries owner-generation state in the transition itself, such as a stable claim/token containing:

```text
{ H, T, OwnerID, state }
```

### What is still moving

A first owner-exit-token A/B/C branch now exists. Its baseline ABA reproduction passed, but the repair patcher failed before candidate compilation because an `IR.h` anchor did not match the composed diagnostic tree. The repair has therefore **not yet been behaviorally tested**.

After carrier integration is repaired, the key discriminator is not just whether token validation blocks the known ABA. A second pause should be inserted after validation and before target transfer. If retirement can cross that smaller gap, a narrow transition lease/epoch is required through the transfer boundary.

### Readiness judgment

**Excellent diagnosis, early implementation.** Keep refining before asking a human to learn a proposed fix; the repair mechanism itself has not yet earned evidence.

## 5. VM replacement semantics

### What is established

`MREMAP_FIXED` now has a clean green discovery carrier separating two defects that were previously conflated.

After moving source S (owner `0xf`, bytes return `222`) over destination T (owner `0xe`, bytes return `111`):

1. direct T still executes the destroyed destination translation (`111`) until an ordinary permission-cycle invalidation, after which it returns `222`;
2. the old owner-`0xe` H claim remains active, so a fresh owner-`0xf` registration becomes standby even though owner `0xf` is the live mapping owner at T.

This yields two obligations for successful fixed replacement:

- translated/code-link invalidation for the overwritten destination range;
- pointer/claim retirement for mappings destroyed or moved away from concrete guest addresses.

The source mapping's owner ID may follow it to the destination, while concrete claims to its former address still become stale.

### What is still moving

The repair transaction needs to be implemented and tested across distinct syscall semantics rather than generalized prematurely:

- `MREMAP_FIXED` source + overwritten destination;
- ordinary moved `mremap`;
- shrink/grow;
- `MAP_FIXED` replacement;
- syscall failure and rollback.

### Readiness judgment

**Diagnosis ready to teach; repair design still decomposing.** The two-defect split is stable enough for later human understanding, but code should wait for narrower VM-operation rules.

## 6. Thunkgen correctness and expressiveness

### 6a. Const-preserving repack

This is the most mature standalone candidate.

A cleaned two-file commit exists:

- `ThunkLibs/Generator/gen.cpp`: remove the helper that strips pointee constness and instantiate `make_repack_wrapper` with the original parameter type;
- `unittests/ThunkLibs/generator.cpp`: focused regression that requires `const` to remain in the generated wrapper type.

The causal chain is compact:

```text
public API has const T*
-> thunkgen strips pointee constness
-> repack_wrapper believes exit writeback is permitted
-> temporary host-layout data overwrites caller-owned input
-> later API call observes corrupted callback aggregate
```

The generic correction passes the focused generator test and independent Vulkan buffer/event allocator runtime cases, including later guest free callbacks. A packaging workflow has also reached a successful candidate artifact path.

**Readiness: candidate-ready for internal human study.** This is the first item worth learning/reimplementing front to back when a human review phase begins.

### 6b. `callback_member`

The semantic mechanism is well supported across two unrelated aggregate APIs:

- DRM `drmEventContext` nested callback fields;
- CUDA `CUDA_HOST_NODE_PARAMS_st` deferred host-node callback.

The generated rule is coherent:

- explicit function-pointer member annotation;
- copy caller-owned aggregate input;
- replace only marked callback fields in the copy;
- finalize host trampolines on the host side;
- classify the signature as needing host-to-guest unpacker role;
- avoid treating unrelated runtime PFN signatures as callback unpackers.

The missing step is mostly candidate reduction. Today the mechanism still lives through diagnostic transformer branches rather than one small standalone generator commit/test set comparable to the const-repack candidate.

**Readiness: concept mature, patch packaging still refining.** This is a good next target for reduction after the role-output work stops moving underneath it.

## Suggested internal sequence

No human review deadline is implied. For ongoing agent work, the useful sequence is:

1. keep the const-repack candidate stable; avoid piling unrelated lifetime work onto it;
2. give the selective `NODELETE` candidate one compact direct validation/footprint receipt;
3. repair and finish the direct thunkgen caller/unpacker role carrier;
4. reduce `callback_member` into a standalone candidate using that role model;
5. prove installed GuestThunks resident-companion packaging and remaining Wayland/32-bit hooks;
6. repair the owner-token carrier and test the post-validation race window;
7. extend callback/VM retirement only with deterministic overlap/replacement cases, keeping syscall-specific rules explicit.

## Human-review trigger

A useful point to invite a full front-to-back human review is when an item has all four:

1. one small candidate branch or clearly bounded design diff;
2. one causal reproducer with a negative control;
3. one focused regression that encodes the intended invariant;
4. a short note stating what the fix does **and what it deliberately does not solve**.

By that standard, const-repack is there now. Selective `NODELETE` is close. `callback_member` is approaching it. The resident companion, callback transaction generalization, H→T owner generation, and wider VM replacement work are still benefiting from active refinement.

No upstream contact is authorized or implied by this checkpoint.
