# Real Vulkan split guest bridge runtime

## Result

A process-resident guest bridge DSO can own the executable H→T adapter while the public generated Vulkan guest wrapper keeps ordinary unload semantics.

This has now been demonstrated with:

- pristine FEX core;
- the real generated Vulkan guest wrapper;
- the real FEX Vulkan host thunk;
- a real native Vulkan PFN (`vkEnumerateInstanceVersion`);
- physical guest-wrapper unload;
- forced generation-2 wrapper placement at a different guest address;
- the same resident bridge adapter address across both wrapper generations.

The experiment closes the H→T lifetime problem without cache retirement, handler replacement, target-cell publication, or JIT execution leases.

## Hosted ARM64 run

Owned-FEX branch: `ci/split-vulkan-bridge-runtime-20260814`.

Workflow: `.github/workflows/split-vulkan-bridge-runtime-v2-arm64.yml`.

Workflow head: `09624793d387703d05b867ed641a1c94b9d2d912`.

Run: `31777724626`.

Job: `94696587975`.

Artifact: `9210599331`.

The runtime itself is the exact pristine FEX commit:

```text
71afe476751deac24adabd1adb575fd2337b6e0a
```

## Bridge design used by the test

The normal generated Vulkan wrapper remains a conventional unloadable DSO and does **not** carry `DF_1_NODELETE`.

A second internal x86-64 DSO, `libfex-vulkan-bridge.so.1`, is linked NODELETE and contains only the executable pieces needed for one native dynamic entrypoint signature:

1. the generated special callback thunk for `VkResult(uint32_t*)`;
2. the `CallHostFunction` adapter obtained through `GetCallerForHostFunction(PFN_vkEnumerateInstanceVersion)`;
3. a tiny exported getter that returns that adapter address to the public Vulkan wrapper.

During the public wrapper's `OnInit()`, it opens the bridge, asks for the resident adapter address, and closes the temporary bridge handle. NODELETE keeps the bridge resident.

When `vkGetInstanceProcAddr` returns the native host pointer H for `vkEnumerateInstanceVersion`, the wrapper calls:

```text
LinkAddressToFunction(H, resident_bridge_T)
```

instead of mapping H to an adapter emitted inside the unloadable public wrapper.

The FEX host thunk SHA table remains process-owned. The special guest thunk in the bridge carries the same generated SHA marker and therefore reaches the already registered Vulkan host packer without loading a second host library.

## Physical-close proof

Generation 1 reports:

```text
SPLIT_BRIDGE_READY T=0x7ffff7e43200
SPLIT_BRIDGE_LINK H=0xffff81f49e20 T=0x7ffff7e43200
```

The retained PFN works before close:

```text
PROBE call where=before-real-close ...
PROBE return where=before-real-close result=0 version=4206831
```

The probe then closes the public Vulkan guest wrapper. Its old wrapper mappings disappear from the guest address space, while the bridge remains process-resident.

Calling the exact same retained native PFN after that physical wrapper unload still succeeds:

```text
PROBE call where=after-real-close ...
PROBE return where=after-real-close result=0 version=4206831
```

The existing probe labels this as:

```text
PROBE stale-call unexpectedly returned
```

because the probe was originally written to demonstrate the stale-pointer failure. Under the split bridge, that “unexpected” return is the desired result: H enters bridge-owned T, so wrapper unload is irrelevant to the retained H→T path.

The close case exits 0.

## Forced moved-generation proof

The reload mode makes the result stronger.

Generation 1:

```text
SPLIT_BRIDGE_READY T=0x7ffff7e43200
SPLIT_BRIDGE_LINK H=0xffff81f49e20 T=0x7ffff7e43200
PROBE generation=1 gipa=0x7ffff7ea2420 pfn=0xffff81f49e20
```

After close, the probe reserves all five old wrapper ranges with inaccessible mappings:

```text
PROBE reserved-old-generation-ranges=5
```

That forces generation 2 to load elsewhere:

```text
PROBE acquired generation=2 gipa=0x7ffff7671420 pfn=0xffff81f49e20
PROBE moved generation old_gipa=0x7ffff7ea2420 new_gipa=0x7ffff7671420
```

Generation 2 again receives the exact same bridge adapter target:

```text
SPLIT_BRIDGE_LINK H=0xffff81f49e20 T=0x7ffff7e43200
bridge_targets=0x7ffff7e43200 0x7ffff7e43200
SPLIT_BRIDGE_STABLE_TARGET=0x7ffff7e43200
```

The moved-generation PFN call succeeds:

```text
PROBE return where=after-reload-new-pfn result=0 version=4206831
SPLIT_BRIDGE_MOVED_GENERATION_OK
```

The reload case exits 0.

## Why this is different from target-cell retirement

The target-cell design makes old compiled H code generation-neutral by loading a replaceable T. It still requires reclamation discipline because T itself belongs to an unloadable generation.

The split bridge makes T process-lived instead.

For this H→T class:

```text
native H -> process-lived bridge adapter T -> current host thunk packer
```

There is no generation handoff at H. The public wrapper can load at any guest address and disappear later; every generation republishes the same bridge-owned T for a given signature.

That removes the H→T stale-code race at its source and keeps the API-call hot path equivalent to the current direct H→T jump.

## Generator-level production model

The prototype hand-extracts one generated `MAKE_CALLBACK_THUNK` specialization. A product implementation would make this a thunk-generator/build output.

A per-library resident guest bridge could contain:

- the library's unique signature-specific `MAKE_CALLBACK_THUNK` set;
- generated `CallHostFunction` adapter instantiations for dynamic proc-address symbols;
- a generated name-to-resident-adapter lookup used only when a proc address is acquired;
- callback unpackers that native host state can retain beyond public-wrapper lifetime.

The public wrapper keeps its ordinary exported API packers, initialization, and user-visible SONAME. Only executable cross-lifetime adapters/unpackers move to the private process-lived bridge.

## Packaging work still required

The experiment installs its internal bridge into the guest `/usr/lib` path. Production FEX guest thunks normally live in FEX's private GuestThunks data directory.

A real implementation therefore needs a private dependency-loading rule, for example:

- an `$ORIGIN` RUNPATH on the public wrapper and colocated bridge DSO;
- explicit FEX thunk-loader redirection for bridge dependencies;
- or another private bridge lookup mechanism.

This is packaging/loader plumbing. The cross-ISA execution model itself is proven by the runtime test.

## Next discriminator: host-to-guest callback half

The bridge model should also be able to own Vulkan's fixed X11 callback unpackers (`XSync`, `XGetVisualInfo`, `XDisplayString`). Those unpackers are simple `CallbackUnpack<...>::Unpack` template instantiations and do not require additional host thunk registration.

The next hosted test moves those three unpackers into the resident bridge and also moves the `vkGetPhysicalDeviceXlibPresentationSupportKHR` dynamic PFN adapter there. The public Vulkan wrapper will then be physically unloaded before the retained Xlib PFN is called again with a new guest Display token.

Success requires:

```text
VULKAN_WRAPPER_FULLY_UNMAPPED
GUEST_XSYNC display=0x12346000
GUEST_XDISPLAYSTRING display=0x12346000
REAL_SPLIT_VULKAN_X11_CALLBACK_OK
```

If that passes, the split bridge will have demonstrated both observed lifetime classes while preserving physical public-wrapper unload.

All source and CI work described here lives on owned fork/investigation surfaces. No upstream FEX changes or comments were made.
