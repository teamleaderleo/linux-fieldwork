# Direct thunkgen resident bridge output — real Vulkan runtime checkpoint

Date: 2026-08-14
Status: provisional research checkpoint; subject to later counterexamples/refinement
Scope: owned research surfaces only

## Result

The resident-bridge architecture no longer depends on parsing normal generated guest C++ as an implementation requirement.

An owned-FEX prototype adds a direct thunkgen `-guest-bridge` output mode and uses it to build a process-resident Vulkan bridge DSO alongside the ordinary unloadable guest Vulkan wrapper.

Owned carrier:

```text
repository: teamleaderleo/FEX
branch: diagnostic/thunkgen-resident-bridge-output-20260814
head: 7d63f276ecd2c1030afdce3b359fb976c50f7274
workflow: .github/workflows/vulkan-direct-thunkgen-bridge-runtime-arm64.yml
run: 31783988882
job: 94715684246
```

Artifact:

```text
name: real-vulkan-direct-thunkgen-bridge-31783988882
id: 9212870738
sha256: ec63a6031f8a8e18fad44894be983b924f57a54791b3a4c3f5e89f758c996443
```

Final marker:

```text
REAL_VULKAN_DIRECT_THUNKGEN_BRIDGE_OK
```

## Direct generator shape

The diagnostic source transform adds a bridge-only generator path rather than post-processing the normal guest output.

The workflow requires the generated bridge inl to contain:

```text
MAKE_CALLBACK_THUNK
FOREACH_internal_SYMBOL
```

and explicitly requires it to contain no ordinary API packer output:

```text
! fexfn_pack_
```

So the bridge output is intentionally an executable bridge/symbol publication unit, not a second copy of the complete guest wrapper API implementation.

The built ELF split is:

```text
libvulkan.so.1
  NEEDED: libfex-vulkan-bridge.so
  no DF_1_NODELETE

libfex-vulkan-bridge.so
  SONAME: libfex-vulkan-bridge.so
  DF_1_NODELETE
```

## Real dynamic PFN matrix

The runtime uses the retained real Vulkan PFN probe rather than a synthetic function.

### Hold control

```text
Linking address 0x7ffff76c80f4 to direct-generated resident host invoker 0x7ffff7e7bcc0
PROBE acquired generation=1 ... gipa=0x7ffff7eb6ee0 pfn=0x7ffff76c80f4 ...
PROBE return where=before-close result=0 version=0x403113
PROBE return where=after-close-with-extra-ref result=0 version=0x403113
```

Exit:

```text
hold=0
```

### Physical wrapper close

After final close the wrapper mapping count falls while the retained native PFN still enters the direct-generated resident invoker:

```text
PROBE after-close maps=11 old-pfn=0x7ffff76c80f4
PROBE about-to-call-stale-pfn=0x7ffff76c80f4
PROBE call where=after-real-close pfn=0x7ffff76c80f4 maps=11
PROBE return where=after-real-close result=0 version=0x403113 maps=11
```

Exit:

```text
close=0
```

The probe's historical text says "stale call unexpectedly returned" because it was originally written to demonstrate the stock failure. Under the resident-bridge candidate that successful return is the intended result.

### Forced moved reload

The old wrapper ranges are reserved before generation 2.

Generation 1:

```text
gipa=0x7ffff7eb6ee0
pfn=0x7ffff76c80f4
```

Generation 2:

```text
old-gipa=0x7ffff7eb6ee0
new-gipa=0x7ffff7685ee0
old-pfn=0x7ffff76c80f4
new-pfn=0x7ffff76c80f4
same-pfn=1
```

Both generations publish the same process-lived bridge target:

```text
Linking address 0x7ffff76c80f4 to direct-generated resident host invoker 0x7ffff7e7bcc0
```

The generation-2 call returns normally:

```text
PROBE return where=after-reload-new-pfn result=0 version=0x403113
```

Exit matrix:

```text
hold=0
close=0
reload=0
```

## Consequence for implementation ranking

The earlier second-stage `extract_guest_bridge.py` experiments remain valuable evidence because they demonstrated complete Vulkan signature coverage and generalized to GL. They are no longer the preferred long-term generator seam.

A direct thunkgen bridge-output mode has now demonstrated the same core Vulkan lifecycle property with a cleaner ownership boundary:

```text
normal guest output  -> unloadable API wrapper
bridge guest output  -> process-lived escaped executable bridge code
host output          -> existing host thunk/native-library side
```

The remaining generator work is therefore mainly about expressing bridge roles and custom escaped targets cleanly, not proving that a separate generator output is possible.

Useful role classes remain:

```text
indirect guest-call signature      -> resident caller
actual guest callback signature    -> resident unpacker
wrapper-local executable target    -> library-specific resident target or generator/runtime metadata
nested callback-bearing aggregate  -> copied/repacked input + resident unpacker
custom callback table (Wayland)    -> custom resident callback allocation seam
```

## Current interpretation

At this checkpoint:

- whole-wrapper NODELETE remains the smallest containment;
- per-library resident bridge remains the strongest demonstrated unload-preserving architecture;
- direct thunkgen bridge output is now the preferred implementation direction over generated-text post-processing;
- full owner/generation + execution-quiescence machinery remains necessary only if FEX must reclaim the escaped bridge executable bytes themselves.

No upstream interaction or mutation is represented by this checkpoint.