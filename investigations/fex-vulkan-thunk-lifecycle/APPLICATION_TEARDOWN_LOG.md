# Application-level Vulkan teardown runtime log

Date: 2026-08-14

This is the running log for the next phase of the FEX Vulkan thunk-lifetime investigation. It is intentionally updated during the experiment, not only at the end.

## Starting evidence

The lifetime mechanism is already demonstrated at three levels:

1. generic model/probe: retained CustomIR registry plus translated synthetic-key state can outlive guest DSO text;
2. real-FEX LinkAddress 2x2: baseline, registry-only, and cache-only all retain stale routing; only registry retirement plus exact synthetic-key eviction permits generation-2 rebinding;
3. real generated Vulkan thunk/PFN A/B: stock FEX crashes on forced-different guest-thunk reload while the integrated lifetime candidate rebinds the same stable native Vulkan PFN to generation 2 and succeeds.

See:
- [CUSTOM_IR_RETIREMENT_2X2.md](./CUSTOM_IR_RETIREMENT_2X2.md)
- [VULKAN_PFN_LIFETIME_AB.md](./VULKAN_PFN_LIFETIME_AB.md)
- [EXACT_CUSTOMIR_RETIREMENT_AB.md](./EXACT_CUSTOMIR_RETIREMENT_AB.md)

## Current target

Carry the integrated lifetime semantics onto an application-level Vulkan teardown path close to the original field observation.

Desired controls:
- unpinned llvmpipe enumeration/teardown;
- guest Vulkan thunk pin / extra-reference control;
- bogus preload control where practical;
- Venus plus llvmpipe when the hosted environment can expose Venus;
- if a fault survives, capture host PC, `si_addr`, JIT membership, guest RIP before reconstruction, and reconstructed guest RIP.

## Candidate under test

Use the more mature owned-fork lifetime candidate rather than the early v2 sketch. The integrated candidate currently combines:
- generation-aware/multi-owner thunk claims;
- exact synthetic-key shared and per-thread eviction;
- coherent retirement lock ordering;
- revoked synthetic-key state for calls after the last owner disappears;
- callback-trampoline tombstoning / dependency retirement work from the internal lifetime branch.

The known production gap remains peer-thread quiescence and ordering retirement before destructive mapping removal.

## Application teardown probe

Owned FEX branch:

```text
ci/vulkan-app-teardown-20260814
```

Probe source:

```text
diagnostics/vulkan-app-teardown/vulkan_app_teardown_probe.c
```

The guest program deliberately follows a `vulkaninfo`-style lifetime order while staying small enough to reason about:

```text
dlopen(libvulkan.so.1)
  -> vkGetInstanceProcAddr
  -> dynamic vkCreateInstance
  -> dynamic vkEnumeratePhysicalDevices
  -> dynamic vkGetPhysicalDeviceProperties
  -> dynamic vkDestroyInstance
  -> destroy instance
  -> dlclose(libvulkan.so.1)
  -> normal process return
```

It prints guest Vulkan mapping counts and all dynamic PFN values around teardown.

### Controls

- `pin`: takes a second Vulkan `dlopen` reference and intentionally keeps it live through normal process return.
- `bogus`: loads an unrelated no-op guest DSO and keeps it live through return. This tests whether merely retaining some unrelated DSO changes teardown behavior.

### Pin-control correction

The first draft acquired a second `dlopen` handle but released it just before returning. That would test a second final unload rather than the field pin control.

The probe was corrected so `pin` intentionally leaks the extra handle through normal return. This keeps the guest Vulkan DSO mapped through the application return/C-runtime teardown boundary, matching the intended positive lifetime control more closely.

Relevant owned-fork commits:

```text
2d73f7050b97c129a436898f3eb3830715ec0183  initial application probe
53b6e02dcab3740b201d38e8b36f2ecf0745937c  keep pin alive through process return
e6f7e115f96bc55eb093b48da36df1d394f35fc9  add unrelated-DSO control
5f08232b4c7ab85c096b2a4d2c55ac64b73c5433  hosted stock/candidate A-B workflow
```

Hosted run started as Actions run `31776908562` on `ubuntu-24.04-arm`.

## Concurrency proof boundary

The existing green multithread retirement test on `ci/thunk-lifetime-race-20260814` is useful but narrower than a true in-flight race.

Its worker thread:

1. calls `H` once to populate that thread's lookup cache;
2. stops at an atomic phase barrier;
3. the main thread unloads the old guest DSO, forces a changed-base reload, and registers generation 2;
4. only then is the worker released to call `H` again.

Therefore that test proves **cross-thread cached-entry eviction and fresh lookup after retirement**. It does not prove safety for a peer thread that has already selected or entered translated `H` while retirement/unmap occurs.

This distinction is now an explicit remaining item. A future in-flight stress case should be classified carefully because unloading a DSO while another application thread is executing its code may itself be outside normal loader guarantees; the most relevant FEX case is an internally retained bridge/callback that can still be executing when its guest-code dependency retires.

## Destructive mapping-path audit

The current integrated owner retirement is hooked into guest `munmap`. FEX has several other guest memory operations that can remove, replace, move, or de-execute the guest target range without naturally touching the synthetic/native key `H`:

- `GuestMmap`: after mapping, FEX calls ordinary `InvalidateCodeRangeIfNecessary` on the new mapping range. A `MAP_FIXED` mapping can replace an existing executable range.
- `GuestMremap`: FEX tracks the move/resize and calls `InvalidateCodeRangeIfNecessaryOnRemap` on the old/shrunk range.
- `GuestMprotect`: FEX updates VMA protection and calls ordinary range invalidation.
- `GuestShmdt`: FEX tracks the detached range and calls ordinary range invalidation.

Those ordinary invalidation helpers are SMC-policy gated, and—more importantly for this investigation—the synthetic CustomIR entrypoint is keyed by `H`, while the affected page contains `T`. The earlier source/runtime work established that CustomIR-generated blocks do not have the normal guest-page reverse ownership needed for range invalidation to discover `H`.

So a production lifetime design should not treat `munmap` as the only retirement event. The more general invariant is:

```text
any operation that destroys or invalidates executable ownership of guest target T
    => retire/re-evaluate every FEX bridge that depends on T
```

A follow-up real-FEX discriminator should cover at least `MAP_FIXED` replacement and execute-permission removal. `mremap`/`shmdt` should be folded into the same dependency-retirement hook rather than each inventing separate thunk-specific logic.

## Experiment policy

All writes and Actions work stay inside repositories owned by `teamleaderleo`. No third-party/upstream comments, PRs, issues, reviews, reactions, or backlink-producing references will be created.

Harness failures are recorded separately from product results.