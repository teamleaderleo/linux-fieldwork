# Real Vulkan PFN lifetime A/B — hosted ARM64

Date: 2026-08-14

## Result

A real Vulkan dynamic-PFN probe now reproduces the unload/reload lifetime failure in stock FEX and shows successful generation-2 rebinding with the integrated lifetime candidate.

This experiment uses the actual generated Vulkan guest and host thunks from FEX `71afe476751deac24adabd1adb575fd2337b6e0a`. The guest probe loads `libvulkan.so.1`, resolves `vkEnumerateInstanceVersion` through `vkGetInstanceProcAddr`, calls the returned PFN, unloads the guest Vulkan thunk, and optionally reloads it after reserving every old generation mapping `PROT_NONE`.

The retained probe source is [`fex_vulkan_pfn_unload_probe.c`](https://github.com/teamleaderleo/linux-fieldwork/blob/probe/fex-vulkan-customir-retirement/investigations/fex-vulkan-thunk-lifecycle/fex_vulkan_pfn_unload_probe.c).

## Matrix

Hosted Actions run `31772339815` produced:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

The useful causal split is `stock_reload=139` versus `candidate_reload=0` against identical generated Vulkan thunks.

## Stock reload

Generation 1:

```text
PROBE acquired generation=1
  gipa=0x7ffff7ea22b0
  pfn=0x7ffff76c80f4
```

The returned PFN executes normally before unload.

After `dlclose`, the probe reserves all five generation-1 guest mappings so the Vulkan guest thunk cannot return at the same address. Generation 2 then reports:

```text
old-gipa=0x7ffff7ea22b0
new-gipa=0x7ffff76712b0
old-pfn=0x7ffff76c80f4
new-pfn=0x7ffff76c80f4
same-pfn=1
```

So the guest-side generated thunk/invoker moved, while the native Vulkan PFN identity remained stable.

Calling the generation-2 PFN through stock FEX exits 139 before returning. This is the Vulkan form of the same retained synthetic-key problem demonstrated by the generic LinkAddress reproducer.

## Candidate reload

The candidate uses the integrated owned-fork lifetime diagnostic: multi-owner thunk claims, exact synthetic-key cache retirement, coherent retirement locking, callback-trampoline tombstones, and revoked-H state for calls made after an owner has disappeared.

On generation-1 unload the runtime records retirement of the real Vulkan PFN:

```text
DIAG_MULTI_DROP H=0x7ffff76c80f4 T=0x7ffff7ea4400
DIAG_MULTI_RETIRE H=0x7ffff76c80f4 OLD=0x7ffff7ea4400 NEW=0
DIAG_MT_SHARED H=0x7ffff76c80f4 erased=1
DIAG_MT_THREAD H=0x7ffff76c80f4 ...
DIAG_REVOKED_H_INSTALL H=0x7ffff76c80f4
DIAG_LOCKED_RETIRE H=0x7ffff76c80f4 ...
```

After forced-different reload, the real native PFN is still exactly the same:

```text
old-pfn=0x7ffff76c80f4
new-pfn=0x7ffff76c80f4
same-pfn=1
```

but the guest target is a new generation:

```text
DIAG_REVOKED_H_ACTIVATE H=0x7ffff76c80f4 T=0x7ffff7673400
DIAG_MULTI_ACTIVE H=0x7ffff76c80f4 T=0x7ffff7673400
```

The call then succeeds:

```text
PROBE call where=after-reload-new-pfn pfn=0x7ffff76c80f4 maps=16
PROBE return where=after-reload-new-pfn result=0 version=0x403113 maps=16
```

and the candidate reload case exits 0.

This is direct real-Vulkan evidence that the stable native PFN identity must outlive individual guest-thunk load generations while the FEX-owned `H -> guest target` relationship must be retired and rebound per generation.

## Why candidate-close still exits 139

`candidate_close=139` is an intentional negative control rather than failed retirement.

The `close` mode unloads the Vulkan guest thunk and then deliberately calls the old PFN **without loading a replacement owner**. The candidate retires generation 1, installs revoked-H state, and compiles the revoked entry when the invalid post-close call is attempted:

```text
DIAG_REVOKED_H_INSTALL H=0x7ffff76c80f4
PROBE about-to-call-stale-pfn=0x7ffff76c80f4
DIAG_REVOKED_H_COMPILE H=0x7ffff76c80f4
```

A stale PFN after its owning guest code is gone has no valid guest target to execute. The lifetime repair therefore needs to prevent execution of retired generation-1 guest code, while allowing a later legitimate owner generation to reactivate the stable `H`. The `reload` result demonstrates that behavior.

## Pin control

Both stock and candidate `hold` cases exit 0. The probe takes a second `dlopen` reference before closing the first handle, so the guest Vulkan thunk stays mapped and the old PFN remains callable.

That retains the original pinning control from field observations and confirms the failure depends on actual owner-text disappearance.

## Candidate isolation

The workflow builds the stock FEX runtime plus real Vulkan guest/host thunks first, records SHA-256 hashes for the thunk DSOs, then applies the lifetime candidate and rebuilds **only** `FEX` and `FEXServer`.

The same generated Vulkan thunk binaries are used by stock and candidate phases. The observed reload split is therefore attributable to runtime lifetime handling rather than a changed Vulkan thunk build.

## Actions provenance

Owned fork:

```text
teamleaderleo/FEX
branch: ci/vulkan-pfn-lifetime-candidate-20260814
carrier: 8072665094f4efdf5d967273b4dac3c95009c6fb
```

Hosted run:

```text
31772339815
workflow: Vulkan PFN lifetime stock-candidate A-B ARM64
job: vulkan-pfn-ab
runner: ubuntu-24.04-arm
conclusion: success
```

Artifact:

```text
id:      9208693595
name:    vulkan-pfn-lifetime-ab-31772339815
sha256:  6acfb52ded50890476f2b1c459ad6d6d4d6b133fbb4a7355d58443e30fb1a942
```

The artifact retains stock/candidate stdout and stderr, all six exit receipts, the candidate source diff, build/configure receipts, rootfs receipt, and before/after Vulkan thunk hashes.

## Relationship to the CustomIR 2×2

[`CUSTOM_IR_RETIREMENT_2X2.md`](./CUSTOM_IR_RETIREMENT_2X2.md) establishes in real FEX that registry retirement alone and exact translated/cache eviction alone each fail, while both together allow clean generation-2 rebinding.

This Vulkan experiment carries that ownership model onto an actual dynamic Vulkan PFN. The Vulkan result preserves the native PFN address across generations while forcing the guest thunk to a different base, then observes stock failure versus candidate success.

## Remaining Vulkan integration work

The PFN probe isolates the lifetime mechanism more tightly than `vulkaninfo`, but the original application-level teardown case still deserves a final run with the candidate enabled:

- unpinned llvmpipe `vulkaninfo` / equivalent enumeration-and-exit path;
- pinned guest Vulkan thunk control;
- bogus preload control;
- Venus plus llvmpipe when the hosted environment can expose Venus;
- host-PC / `si_addr` / JIT-membership / reconstructed guest-RIP receipt if any teardown fault survives.

At this point a surviving `vulkaninfo` failure would indicate an additional teardown path rather than undermine the demonstrated dynamic-PFN lifetime bug.

## External-contact state

No third-party/upstream issue, pull request, comment, review, reaction, or repository write was performed. All writes and Actions execution remained inside repositories owned by `teamleaderleo`.
