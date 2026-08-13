# Split resident bridge runtime experiment

## TL;DR

A new candidate architecture now has executed evidence on both GitHub-hosted x86-64 and AArch64:

> Keep only the generic callable bridge adapter in a process-resident runtime, while allowing the library-specific guest wrapper DSO to unload and reinitialize normally.

This is a middle ground between making all of `libvulkan-guest.so` `NODELETE` and implementing full generation-aware retirement for every piece of bridge code.

A standalone loader model passed on both hosted architectures after fixing one harness-only SONAME error. The model demonstrated:

- resident bridge DSO carries `DF_1_NODELETE`;
- ordinary wrapper DSO physically unloads;
- wrapper static state resets on reopen;
- bridge adapter address remains stable across wrapper generations;
- calls through the stable adapter succeed with a newly reacquired generation-specific target;
- 1,000 wrapper open/close cycles leave the wrapper unmapped and do not multiply the resident bridge mapping;
- resident bridge state persists exactly as intended.

This is diagnostic design evidence. FEX source integration remains to be implemented and tested in the owned fork.

## Why this is interesting for the Vulkan failure

The dead Vulkan address in the real reproducer resolves inside a generated `CallHostFunction<...>` body.

At FEX-2608 that body is mostly generic ABI-adapter logic:

```text
read native host function address from guest r11
pack guest arguments
invoke the generated host thunk
unpack/return the result
```

The dangerous lifetime coupling comes from where the adapter is emitted: the template instantiation currently lives inside `libvulkan-guest.so`.

FEX then stores:

```text
native host PFN H -> CallHostFunction adapter T
```

in process-owned CustomIR state.

If `T` instead lived in a small process-resident bridge runtime, guest Vulkan wrapper unload would no longer invalidate that executable destination.

The library-specific Vulkan wrapper could still unload and reset its own constructors, destructors, static state, TLS, and mappings.

## FEX-specific pieces that would need to move

A real implementation needs more than moving one C++ template body.

### Dynamic host-PFN path

`CallHostFunction<signature>` depends on the generated special thunk referenced by `fexthunks_invoke_callback<signature>`.

For the adapter to survive Vulkan-wrapper unload, both of these executable pieces must be owned by the resident bridge runtime:

```text
stable CallHostFunction<signature> body
stable generated hostcall special thunk for that signature
```

The current Vulkan `HostPtrInvokers` table would then map names to the stable runtime adapters rather than template instantiations emitted into the Vulkan guest DSO.

### Host-to-guest callback path

FEX's host callback trampoline metadata can retain `GuestUnpacker` and `GuestTarget`.

For callbacks whose unpacker is fixed/generated glue, that unpacker is another candidate for the resident bridge runtime.

The actual application callback target should remain owned by the application/library that supplied it. Its lifetime contract needs separate handling; moving fixed unpacker code does not make an arbitrary application callback safe after its owner is unloaded.

For the Vulkan X11 setup in this investigation, the stale-address concern is the generated `CallbackUnpack<...>::Unpack` that currently lives in the Vulkan guest image. Moving that fixed unpacker to stable runtime code would remove one more Vulkan-wrapper lifetime dependency.

## Hosted model

Disposable Fieldwork branch:

- branch: `probe/fex-nodelete-gha`
- workflow: `.github/workflows/split-bridge-runtime-semantics.yml`

Initial run failed before the experiment because the wrapper's `DT_NEEDED` referenced SONAME `libfexbridge.so.1`, while the test build only created filename `libfexbridge.so`. Adding the normal SONAME symlink fixed the harness without changing the architecture.

Canonical successful probe:

- commit: `47680b8c3b437cbc84951ee7b132451403e8561d`
- workflow run: `31735254303`
- hosted x86-64 job: success
- hosted AArch64 job: success

The ARM64 output included:

```text
SPLIT_BRIDGE_PASS adapter=<stable-address> bridge_maps=4 wrapper_resets=1 bridge_calls=2
```

The test sequence was:

```text
load ordinary wrapper generation G1
  -> wrapper static state initializes to 100
  -> obtain process-resident adapter S
  -> call S(new generation target) -> 42
close G1
  -> wrapper mapping must disappear
  -> bridge mapping must remain
reopen wrapper generation G2
  -> wrapper state must reset to 100
  -> adapter address S must be unchanged
  -> reacquire G2 target
  -> call S(G2 target) -> 42
close G2
repeat wrapper open/close 1000 times
  -> wrapper ends unmapped
  -> bridge mapping count unchanged
```

## What the model proves

It proves the lifetime split is coherent under glibc on both hosted architectures:

- process-long executable adapter code can coexist with physically unloadable/reloadable wrapper state;
- adapter identity can remain stable while generation-specific state resets;
- repeated wrapper lifecycle does not require repeated allocation of the stable executable image.

It also demonstrates an important design discipline for FEX:

> The stable adapter must never retain the old generation-specific target after unload. Reacquire or rebind any generation-specific target before use.

The Vulkan dynamic-PFN adapter is especially attractive because its native target `H` is already supplied dynamically through guest `r11` on each call. The stable adapter therefore does not need to retain a Vulkan guest-image address to invoke the native function.

## What it does not prove

The model does not yet prove:

- FEX's generated hostcall thunks can be separated cleanly from each guest thunk DSO;
- every Vulkan dynamic signature can be deduplicated into a common resident runtime;
- current function-pointer identity assumptions tolerate the move;
- callback targets have correct lifetime after moving only the unpacker;
- the real exit-139 immediately enters the dead adapter via CustomIR;
- performance cost of the split is negligible;
- build/install packaging of an extra guest bridge runtime is desirable.

## Comparison with whole-Vulkan NODELETE

### Whole `libvulkan-guest.so` NODELETE

Pros:

- three-line source experiment;
- protects every executable address in the Vulkan guest image at once;
- directly matches the existing pinned-thunk real-target control;
- no generation race involving guest thunk bytes.

Costs:

- Vulkan guest wrapper static/TLS state persists across logical close/reopen;
- wrapper constructors do not get a fresh physical generation;
- wrapper destructors/finalization are deferred to process exit;
- retained code/data footprint is the whole generated Vulkan guest thunk.

### Split bridge runtime

Pros:

- persistent lifetime is attached to code that FEX itself stores in process-owned bridge state;
- library wrapper can retain ordinary physical unload/reload semantics;
- wrapper static/TLS state can reset normally;
- smaller retained executable/data footprint;
- gives the architecture an explicit place for diagnostics, ownership labels, and future generation metadata.

Costs:

- generator/build changes are larger;
- generated signature-specific hostcall thunks need relocation into the stable runtime;
- callback split needs careful ownership analysis;
- may require an extra DSO or an equivalent process-owned executable arena;
- performance and code-size effects need measurement.

## Current ranking

For the Vulkan reproducer alone, whole-wrapper `NODELETE` remains the smallest product experiment and should still be run first against llvmpipe and Venus.

For a general FEX design, the split bridge runtime is now the most interesting compromise to prototype before committing to full generation-aware unloading:

1. **Vulkan `DF_1_NODELETE`** — cheapest causal/product policy test.
2. **Split resident bridge runtime** — strongest current candidate for preserving wrapper physical unload while making FEX-owned executable bridges safe.
3. **Full generation + execution lease** — strongest full-reclamation model when every bridge and wrapper must be physically retireable.

The choice should be driven by measured compatibility and performance rather than by assuming ordinary DSO reclamation is always required for synthetic thunk implementation code.

## Next FEX experiment

Use the existing `libfex_thunk_test` machinery in the owned FEX fork.

Create a diagnostic indirect-host-call entry whose stable native host pointer is reusable across guest-wrapper generations. Compare two variants:

```text
A: current generated adapter lives in libfex_thunk_test-guest.so
B: adapter/special-thunk pair lives in a NODELETE bridge-runtime guest DSO
```

Force wrapper reload at a changed guest base.

Require:

```text
A baseline: determine whether stale H -> old T appears
B split runtime: wrapper unmaps, stable adapter remains, new generation call succeeds
```

Then measure a tight host-PFN call loop to quantify any steady-state overhead before attempting Vulkan integration.

## External-contact state

FEX upstream remains read-only. This experiment and any implementation prototypes belong only in owned repositories/forks unless a human later authorizes a separate upstream interaction and independently derives contribution-compliant code.
