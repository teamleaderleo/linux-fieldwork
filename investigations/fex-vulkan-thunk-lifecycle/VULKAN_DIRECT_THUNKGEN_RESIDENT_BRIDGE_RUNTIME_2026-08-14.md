# Vulkan direct-thunkgen resident bridge runtime — 2026-08-14

## Result

The resident Vulkan companion can now be built from a **direct thunkgen bridge output** rather than post-processing the normal generated guest C++.

The direct-generator companion passes the same real generated Vulkan PFN lifetime matrix under stock FEX core:

```text
hold=0
close=0
reload=0
```

This closes the tooling gap between the proven split runtime architecture and a production-shaped central generator primitive.

## Owned fork identity

Branch:

```text
diagnostic/thunkgen-resident-bridge-output-20260814
```

Diagnostic generator helper:

```text
.github/fieldwork/apply_thunkgen_guest_bridge_output.py
```

Diagnostic Vulkan integration helper:

```text
.github/fieldwork/apply_vulkan_direct_thunkgen_bridge.py
```

Runtime workflow:

```text
.github/workflows/vulkan-direct-thunkgen-bridge-runtime-arm64.yml
```

Valid run:

```text
run: 31783988882
job: 94715684246
head: 7d63f276ecd2c1030afdce3b359fb976c50f7274
artifact: 9212870738
artifact digest: sha256:ec63a6031f8a8e18fad44894be983b924f57a54791b3a4c3f5e89f758c996443
```

The source branch is based on reviewed FEX source `71afe476751deac24adabd1adb575fd2337b6e0a` plus owned diagnostic files/transformers.

## Direct generator primitive

The diagnostic thunkgen mode emits:

```text
thunkgen_bridge_libvulkan.inl
```

containing only:

- unique signature-specific `MAKE_CALLBACK_THUNK` adapters;
- symbol enumerators including `FOREACH_internal_SYMBOL`.

It does not contain normal API pack/public-wrapper bodies.

The Vulkan bridge DSO includes that generated file directly and constructs its resident native-name→guest-adapter lookup from the generated `FOREACH_internal_SYMBOL` list.

No `ExtractBridgeThunks.py` or `ExtractBridgeSymbols.py` generated-C++ scraping is used in this runtime gate.

## Runtime matrix

### Hold control

```text
Linking address 0x7ffff76c80f4 to direct-generated resident host invoker 0x7ffff7e7bcc0
PROBE acquired generation=1 ... pfn=0x7ffff76c80f4 maps=16
PROBE return where=before-close result=0 version=0x403113 maps=16
PROBE extra-ref ...
PROBE after-first-close maps=16
PROBE return where=after-close-with-extra-ref result=0 version=0x403113 maps=16
```

### Final-close retained PFN

The generated Vulkan wrapper begins with five tracked mappings. After final close:

```text
PROBE after-close maps=11 old-pfn=0x7ffff76c80f4
```

The retained native PFN still executes through the resident adapter:

```text
PROBE call where=after-real-close pfn=0x7ffff76c80f4 maps=11
PROBE return where=after-real-close result=0 version=0x403113 maps=11
```

The probe's historical message says `stale call unexpectedly returned`; for the split architecture that return is the **expected successful outcome** because the PFN no longer targets wrapper-owned executable code.

### Forced moved reload

Generation 1 wrapper ranges are physically gone and all five old ranges are reserved:

```text
PROBE after-close maps=11 old-pfn=0x7ffff76c80f4
PROBE reserved-old-generation-ranges=5
```

Generation 2 moves the wrapper/GIPA while preserving the native host PFN:

```text
Linking address 0x7ffff76c80f4 to direct-generated resident host invoker 0x7ffff7e7bcc0
PROBE acquired generation=2 ...
old-gipa=0x7ffff7eb6ee0
new-gipa=0x7ffff7685ee0
old-pfn=0x7ffff76c80f4
new-pfn=0x7ffff76c80f4
same-pfn=1
```

The reloaded real Vulkan call succeeds:

```text
PROBE return where=after-reload-new-pfn result=0 version=0x403113 maps=16
```

## Relationship to the generator-equivalence proof

The direct runtime follows the earlier generator-only comparison:

```text
libvulkan: callbacks guest=476 bridge=476 equal=True
libvulkan: internal symbols guest=714 bridge=714 equal=True
libGL: callbacks guest=736 bridge=736 equal=True
libGL: internal symbols guest=3102 bridge=3102 equal=True
THUNKGEN_GUEST_BRIDGE_OUTPUT_EQUIVALENT
```

That comparison is retained in [`THUNKGEN_RESIDENT_BRIDGE_OUTPUT_2026-08-14.md`](./THUNKGEN_RESIDENT_BRIDGE_OUTPUT_2026-08-14.md).

Together the two experiments establish:

1. thunkgen already has exactly the data needed by resident companions;
2. it can emit that data directly without generated-C++ scraping;
3. the direct output can build the real generated Vulkan companion;
4. the resulting split passes physical wrapper unload and moved reload with a stable native PFN under stock FEX core.

## Production-shaped implication

A cleaner central integration is now credible:

```text
thunkgen interface analysis
    -> normal unloadable guest-wrapper output
    -> resident-bridge adapter/symbol output

GuestLibs/CMake
    -> ordinary wrapper DSO
    -> NODELETE companion DSO containing escaped executable glue
```

Per-library guest code still owns semantic decisions about callback targets that must move resident. The generator can provide generic signature adapters and generated symbol identity; it cannot infer every lifetime owner from function type alone.

GL independently shows another required rule: once a resident companion becomes authoritative for dynamic adapters, the unloadable wrapper should not keep a parallel adapter registry referencing wrapper-local copies.

## Boundary

All changes are diagnostic/research code on owned repository surfaces. No upstream FEX interaction was made. Any upstream implementation must be independently derived and written by a human in compliance with FEX contribution policy.
