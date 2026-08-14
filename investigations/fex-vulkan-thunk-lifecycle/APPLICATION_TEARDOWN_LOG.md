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

### Pin-control correction

The first draft acquired a second `dlopen` handle but released it just before returning. That would test a second final unload rather than the field pin control.

The probe was corrected so `pin` intentionally leaks the extra handle through normal return. This keeps the guest Vulkan DSO mapped through the application return/C-runtime teardown boundary, matching the intended positive lifetime control more closely.

Relevant owned-fork commits:

```text
2d73f7050b97c129a436898f3eb3830715ec0183  initial application probe
53b6e02dcab3740b201d38e8b36f2ecf0745937c  keep pin alive through process return
```

## Experiment policy

All writes and Actions work stay inside repositories owned by `teamleaderleo`. No third-party/upstream comments, PRs, issues, reviews, reactions, or backlink-producing references will be created.

Harness failures are recorded separately from product results.