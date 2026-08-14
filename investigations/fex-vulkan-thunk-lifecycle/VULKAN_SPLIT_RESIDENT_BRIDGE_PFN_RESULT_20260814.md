# Vulkan split-resident bridge PFN lifetime result — 2026-08-14

This checkpoint records a clean exact-FEX-2608 result for a narrower alternative to keeping the entire guest Vulkan wrapper process-resident.

## Question

Dynamic Vulkan proc-address bridging currently links a native host function address `H` to guest generated `CallHostFunction` code `T`. The historical failure class appears when `T` lives in `libvulkan-guest.so` and the wrapper unloads while FEX or application-visible state can still reach `H` or has already selected `T`.

Whole-wrapper self-pin / `DF_1_NODELETE` fixes this by retaining all of `libvulkan-guest.so`, but that changes wrapper unload/reload semantics for state that does not itself need to escape.

The split-bridge candidate instead moves only FEX-owned executable targets that intentionally escape wrapper lifetime into a separate process-resident DSO:

```text
libvulkan-guest.so          ordinary unloadable wrapper
libfex-vulkan-bridge.so     DF_1_NODELETE resident executable bridge
```

The resident bridge contains the generated dynamic-PFN invokers and Vulkan X11 guest unpackers. The ordinary wrapper references that bridge and remains unloadable.

## Exact FEX-2608 run

Owned-fork workflow:

- repository: `teamleaderleo/FEX`
- branch: `ci/fex2608-nodelete-vulkaninfo-ab-clean-20260814`
- run: `31785811418`
- historical base: `e869aa644a16e4332cdc15c1ea0b4d13d482385d`

The workflow proves committed product source is exact FEX-2608 apart from fork policy/workflow files, then applies the split transform only in the runner.

ELF policy assertions:

- `libvulkan-guest.so`: **no** `DF_1_NODELETE`
- `libfex-vulkan-bridge.so`: **has** `DF_1_NODELETE`

## Probe

The x86-64 guest probe:

1. `dlopen("libvulkan.so.1")`;
2. obtains `vkGetInstanceProcAddr` from the ordinary wrapper;
3. dynamically obtains `vkEnumerateInstanceVersion`;
4. invokes that PFN successfully;
5. final-`dlclose`s the ordinary wrapper;
6. verifies the wrapper's `vkGetInstanceProcAddr` address is unmapped while the bridge remains mapped;
7. invokes the previously saved dynamic Vulkan PFN again;
8. reopens the ordinary wrapper, obtains a fresh PFN, invokes it;
9. closes again and verifies the bridge remains resident.

Observed:

```text
Linking address 0x7ffff76c80f4 to resident host invoker 0x7ffff7e7bcc0
SPLIT before-close rc=0 version=4206867 gipa-mapped=1 bridge=1
SPLIT after-close gipa-mapped=0 bridge=1
SPLIT saved-pfn-after-close rc=0 version=4206867
Linking address 0x7ffff76c80f4 to resident host invoker 0x7ffff7e7bcc0
SPLIT reopen rc=0 version=4206867 old-pfn=0x7ffff76c80f4 new-pfn=0x7ffff76c80f4 bridge=1
SPLIT final bridge=1 wrapper-gipa-mapped=0
SPLIT PFN_PASS
```

## Interpretation

The application-visible dynamic PFN is the native Vulkan function address `H`. FEX's H-keyed CustomIR bridge redirects execution to a guest target `T`.

With the ordinary design, `T` is generated code inside `libvulkan-guest.so`; wrapper unload can therefore invalidate the bridge target even though `H` remains a valid host address.

With the split candidate, `T` lives in the resident bridge DSO instead. Final application `dlclose` can genuinely unmap the ordinary guest Vulkan wrapper while the H→T bridge stays executable. The saved PFN remains callable after close and through wrapper reload.

This avoids the difficult H→T execution-lease problem for FEX-owned generated PFN targets: FEX makes the code it publishes process-resident instead of trying to retire/drain every dynamic PFN transfer.

## Comparison with whole-wrapper `NODELETE`

Whole-wrapper residency remains a valid conservative containment mechanism, but the split candidate is narrower:

- wrapper constructors/statics and ordinary wrapper text may unload/reinitialize normally;
- only FEX-owned executable bridge code whose address intentionally escapes is process-resident;
- the historical stale-target class is removed because H→T points to stable resident T;
- callback targets owned by arbitrary guest DSOs are **not** solved by this and still require stable descriptor identity, revocation, and execution drain.

## Remaining audit before treating the split as complete

The bridge DSO must contain every FEX-owned executable address whose lifetime may escape the ordinary wrapper. For Vulkan this currently includes:

- generated dynamic-PFN `GetCallerForHostFunction(...)` invokers;
- the X11 callback `GuestUnpacker`s published during Vulkan guest initialization.

One corner case remains: `stub_unknown_functions` is currently `false`, but if that mode is ever enabled, its generated `CallHostFunction<FatalError>` target also needs resident ownership.

The split build also still needs explicit 32-bit validation and a full combined routing + real Vulkan application gate before promotion as the preferred fork repair.
