# FEX thunk lifetime decision brief

Date: 2026-08-14
Audience: someone deciding what to propose, implement, or ask FEX maintainers
Status: research decision packet

## The decision in one page

FEX has a demonstrated lifetime mismatch: generated executable guest helper addresses can be retained by FEX/native state after the guest wrapper generation that owns them is physically unloaded.

The evidence now supports a two-step recommendation.

### Immediate product correction

Use selective `DF_1_NODELETE` for guest thunk wrappers whose generated executable helpers escape into persistent state.

Current owned-FEX candidate:

```text
candidate/selective-nodelete-guest-thunks-20260814
cee502da1867531621f3f8af8483c31ea22776a0
```

Why this is a credible small patch:

- the product diff is small and localized to guest-thunk build policy;
- real Vulkan PFNs survive ordinary guest `dlclose` when the wrapper remains resident;
- real Vulkan/X11 host->guest callback paths survive for the same reason;
- the measured Vulkan retained mapping delta is exactly 311,296 bytes / 304 KiB;
- the change leaves FEXCore/JIT lifetime behavior alone.

Main caveat: loader namespaces. `NODELETE` in repeated NEWLM namespaces can retain namespace instances, and a base-namespace-only runtime promotion experiment failed to cover NEWLM callback publication.

### Preferred unload-preserving direction

Generate a resident companion per thunk family and bitness. Put only executable helpers whose addresses escape into that companion. Keep ordinary public wrapper code unloadable.

This is now demonstrated across more than one API family:

- Vulkan dynamic PFNs and Vulkan/X11 callback unpackers;
- GL dynamic PFNs and helper unpackers;
- DRM retained callback-unpacker tests;
- thunkgen-generated nested callbacks inside `drmEventContext` for current-main `drmHandleEvent`.

A real Ubuntu amd64 `vulkaninfo --summary` also completes through the generated Vulkan split bridge under hosted ARM64 FEX.

## The ownership rule

Use this sentence when explaining the design:

> Executable guest code that escapes a wrapper generation needs the lifetime of the state that retains it.

Then split the implementation into three owners:

```text
ordinary API wrapper code
  -> wrapper/load generation

generated escaping adapter or unpacker
  -> resident per-library bridge

actual guest callback target
  -> the guest mapping/load generation that supplied it
```

The third case is the remaining hard one. A resident unpacker keeps the generated bridge executable alive; it cannot keep an arbitrary guest callback target alive after that target's DSO unloads.

## What has been disproven

Several simpler stories have executable counterexamples now.

### "Invalidate T's range and unload"

The compiled native-H path can be keyed elsewhere and retain T as an embedded dependency.

### "Retire H and clear every cache, then unload"

A two-thread test stops one thread after it has already selected T. Another thread retires the registry/cache state and unmaps T. The first thread resumes into stale code and faults.

Result:

```text
pin=0
unmap=139
```

### "The address identifies the owner"

`MAP_FIXED` can replace executable generation 1 with generation 2 at the same numeric address. The research now has successful pre-retirement and rollback transactions around that boundary, and a VMA owner-ID prototype is validating non-reusable generation identity.

### "Promote only the base namespace"

A NEWLM Vulkan generation can publish generation-owned callback unpackers into persistent host state and then unload, so base-namespace-only promotion misses a real retained edge.

### "Combine all libraries into one shared bridge immediately"

FEX has already fixed a real GL/Vulkan helper symbol collision. Shared signature identity may also omit generator annotations that affect marshalling semantics. Per-library companions are the safer first generic design.

## New results since the earlier handoff

### MAP_FIXED rollback works as a transaction

The serial research transaction now demonstrates all three required outcomes:

```text
failed replacement      -> rollback restores old H -> old T, exit 0
successful replacement  -> commit keeps old H revoked, exit 139 control
successful + new claim  -> fresh claim activates generation 2, exit 0
```

This separates mapping-generation identity from transaction integrity and from the independent in-flight execution race.

See [`MAP_FIXED_ROLLBACK_LOG.md`](./MAP_FIXED_ROLLBACK_LOG.md).

### VMA owner-ID propagation is the active identity experiment

The new prototype adds non-reusable owner IDs to FEX VMA tracking and tests these rules:

```text
successful same-address MAP_FIXED -> owner ID changes
failed MAP_FIXED                  -> old owner ID remains
mprotect split/permission cycle   -> owner ID remains
mremap preserving generation      -> owner ID carries forward
```

Once green, thunk claims can become `{T, OwnerID}` instead of plain T values.

See [`VMA_OWNER_ID_LOG.md`](./VMA_OWNER_ID_LOG.md).

### Nested DRM callbacks can be generated

A research thunkgen `callback_member` annotation fixes current-main `drmHandleEvent` without handwritten DRM callback wrappers:

```text
native=0
pristine_reference=132
generated_candidate=0
```

This proves the generator can classify callbacks hidden inside structures and reuse existing typed trampoline machinery.

See [`DRM_NESTED_CALLBACK_GENERATOR_PROTOTYPE.md`](./DRM_NESTED_CALLBACK_GENERATOR_PROTOTYPE.md).

### Real vulkaninfo works through the split bridge

The corrected hosted A/B is:

```text
unsplit=0
split=0
```

Both enumerate llvmpipe. The split trace shows real dynamic Vulkan PFNs being linked to resident guest bridge adapters throughout the tool run.

This is end-to-end compatibility evidence for the bridge design. It is not a reproduction of the historical teardown crash because the unsplit control also exits 0 in this hosted environment.

See [`HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md`](./HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md).

## What I would ask maintainers to decide

### Decision 1 — wrapper lifetime policy

Are selected generated guest thunk wrappers allowed to become process-lived once loaded?

If yes, selective NODELETE is a small, defensible correction and can ship independently of the longer design.

If physical unload/reset is important, continue to Decision 2.

### Decision 2 — ownership of escaping generated helpers

May generated PFN adapters and callback unpackers live in a private resident per-library companion while ordinary wrappers remain unloadable?

The Vulkan and GL moved-reload evidence says this works for the major proc-address shape. Vulkan/X11 and DRM evidence supports the callback-unpacker side.

### Decision 3 — loader namespace contract

Should a bridge instance follow each guest loader namespace, or should FEX own one private process-level bridge per family/bitness and partition all mutable helper state by namespace?

This is the largest unresolved semantic choice in the resident-bridge design.

### Decision 4 — callback target contract

What happens when native state retains an actual guest callback target after the guest DSO that supplied it unloads?

That case needs owner/generation retirement and safe in-flight execution handling. It should remain a separate runtime problem from generated bridge helper residency.

### Decision 5 — generator metadata

Should thunkgen gain explicit typed concepts for:

```text
callback member inside a structure
escaping executable helper
native-retained converted object
```

The DRM result says nested callback conversion belongs in the generator. `drmServerInfo` says callable conversion and retained-object lifetime must remain separate declarations.

## Proposal ordering

The clean presentation order is:

1. show the ownership failure class with one Vulkan PFN and one callback example;
2. show the 304 KiB selective-NODELETE containment and tiny patch;
3. show the generated split bridge physically unloading/moving the wrapper while retained calls keep working;
4. show GL as the independent second proc-address family;
5. show DRM as the independent nested-callback family;
6. show the in-flight race as the reason full reclamation is a separate, heavier mechanism;
7. ask maintainers which lifetime contract they actually want.

Avoid leading with the full owner-ID/transaction/quiescence machinery. That work is valuable because it defines the true-unload boundary, while the resident bridge removes most generated helper code from that difficult path.

## Recommended engineering work now

### High value / low ambiguity

- finish the active VMA owner-ID discriminator and retain the result;
- run a generated 32-bit resident-bridge PFN + callback proof;
- measure incremental mapping/RSS/PSS cost of split bridge versus whole-wrapper NODELETE;
- connect generated nested callback-member signatures to resident callback unpackers;
- build the first explicit two-NEWLM namespace bridge-state discriminator.

### Valuable after those

- define retained-object generator metadata using `drmServerInfo` as the first concrete case;
- move custom Vulkan/GL raw helper publication behind typed escape metadata;
- design `{T, OwnerID}` claim bookkeeping and atomic retiring epochs for truly reclaimable targets;
- choose quiescence / lease / hazard / entry-generation validation only after the callback-target test establishes the required runtime contract.

### Later optimization

- cross-library bridge signature deduplication;
- bridge executable reclamation during process lifetime.

## Reopen triggers

The current recommendation should change if any of these appear:

- a real intermediate wrapper reset/unload contract that NODELETE breaks;
- a resident bridge changes API-visible behavior beyond lifetime;
- a 32-bit ABI counterexample invalidates the generated split;
- loader namespace tests show a per-library resident companion cannot preserve expected namespace isolation;
- memory accounting makes bridge residency materially worse than the whole-wrapper policy;
- generator annotations produce semantically distinct helpers that the current bridge identity accidentally merges.

## Canonical supporting documents

Start here:

- [`RFC_THUNK_EXECUTABLE_LIFETIME.md`](./RFC_THUNK_EXECUTABLE_LIFETIME.md)
- [`RFC_PROCESS_RESIDENT_GUEST_BRIDGE.md`](./RFC_PROCESS_RESIDENT_GUEST_BRIDGE.md)
- [`CURRENT_MAIN_LIFETIME_AUDIT_20260814.md`](./CURRENT_MAIN_LIFETIME_AUDIT_20260814.md)
- [`MAP_FIXED_ROLLBACK_LOG.md`](./MAP_FIXED_ROLLBACK_LOG.md)
- [`VMA_OWNER_ID_LOG.md`](./VMA_OWNER_ID_LOG.md)
- [`DRM_NESTED_CALLBACK_GENERATOR_PROTOTYPE.md`](./DRM_NESTED_CALLBACK_GENERATOR_PROTOTYPE.md)
- [`HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md`](./HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md)

## Evidence boundary

This brief is for internal decision-making. It does not claim that current hosted Ubuntu reproduces the historical Apple M5 teardown edge.

The generic lifetime mechanism and the principal repair families have independent owned-fork runtime evidence. The VMA owner-ID experiment is active and should remain labeled pending until its hosted run completes.

No upstream FEX contact is authorized or performed by this record.
