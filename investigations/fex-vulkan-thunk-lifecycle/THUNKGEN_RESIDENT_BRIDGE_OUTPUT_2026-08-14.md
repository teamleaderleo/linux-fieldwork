# thunkgen resident-bridge output proof — 2026-08-14

## Result

A diagnostic thunkgen output mode can emit the exact generated material needed by a process-resident guest bridge **directly**, without scraping the normal full guest-wrapper output.

Owned fork branch:

```text
diagnostic/thunkgen-resident-bridge-output-20260814
```

Diagnostic source helper:

```text
.github/fieldwork/apply_thunkgen_guest_bridge_output.py
```

The prototype adds a research-only `-guest-bridge` output kind and emits only:

- the same unique `MAKE_CALLBACK_THUNK(...)` signature adapters used by ordinary guest generation;
- the same generated symbol enumerators, including `FOREACH_internal_SYMBOL`;
- no normal API pack/public-wrapper bodies.

## Runtime-independent equivalence gate

Workflow:

```text
.github/workflows/thunkgen-guest-bridge-output-smoke.yml
```

Valid run:

```text
run: 31783342563
job: 94713673175
head: 9f55b30a44a75254f2dad2a33d13b59d94ae3588
artifact: 9212571829
artifact digest: sha256:07c0072a72db0e32524e38c5e36902ce7f42dae2369453c4821d6d9611502538
```

The job builds the patched thunkgen and asks it for both normal guest output and bridge output for generated Vulkan and GL interfaces.

Exact comparison:

```text
libvulkan: callbacks guest=476 bridge=476 equal=True
libvulkan: internal symbols guest=714 bridge=714 equal=True
libGL: callbacks guest=736 bridge=736 equal=True
libGL: internal symbols guest=3102 bridge=3102 equal=True
THUNKGEN_GUEST_BRIDGE_OUTPUT_EQUIVALENT
```

The gate also asserts that the bridge fragment does not contain normal API packing/public-wrapper material such as `MAKE_THUNK(`, `fexfn_pack_`, or the normal public wrapper block.

## Generated fragment sizes

From the same run:

```text
Vulkan bridge fragment:  244641 bytes
Vulkan full guest inl:   861975 bytes
GL bridge fragment:      386303 bytes
GL full guest inl:      2548172 bytes
```

These are generated source fragment sizes, not ELF/RSS measurements. They show that the bridge-specific output is materially narrower than duplicating the full guest-generated file.

## Why this matters

The successful Vulkan and GL resident-bridge research prototypes originally used small Python extractors to recover two data sets from the normal generated guest `.inl`:

1. unique signature-specific `MAKE_CALLBACK_THUNK` adapters;
2. the internal thunked-symbol list.

thunkgen already owns both data sets while generating the guest file. This experiment proves it can emit them directly and exactly.

Therefore the production-shaped integration should not keep per-library generated-C++ scrapers. A cleaner design is:

```text
thunkgen interface analysis
    -> normal guest wrapper output
    -> resident-bridge output
```

with central GuestLibs/CMake support consuming the bridge output to build a small resident companion DSO.

Library-specific guest source still decides which callback **targets** belong in the resident companion. The generator can provide generic signature adapters and symbol identity, but it cannot infer every semantic owner merely from a function type.

## Relationship to Vulkan evidence

This is a generator/build primitive, not a new lifetime result.

The lifetime safety of the split design is established separately by:

- stock-FEX split synthetic runtime;
- selected-before-wrapper-unmap race;
- real generated Vulkan PFN unload/reload;
- exact FEX-2608 Vulkan PFN run;
- real Vulkan/X11 callback-after-wrapper-unload;
- real distro amd64 `vulkaninfo --summary` compatibility run.

This experiment removes a tooling weakness from that architecture: the resident bridge no longer needs to be described as dependent on post-processing normal generated C++.

## Boundary

All changes are diagnostic/research code on owned repository surfaces. No upstream FEX interaction was made. Any upstream implementation must be independently derived and written by a human in compliance with FEX contribution policy.
