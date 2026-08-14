# Generated Vulkan split resident bridge — real X11 callback runtime

Date: 2026-08-14

## Result

The generated Vulkan split resident bridge now has real generated/runtime coverage for **both concrete lifetime directions** after physical unload of the ordinary Vulkan guest wrapper.

A real Vulkan Xlib PFN is routed through a thunkgen-produced resident guest bridge. The persistent host Vulkan/X11 helper uses resident guest callback unpackers from the same bridge. After ordinary guest `dlclose(libvulkan.so.1)` physically removes `libvulkan-guest.so`, the retained Xlib PFN still enters native ARM64 Vulkan and the host helper successfully calls guest `XSync` and `XDisplayString` again.

No FEX core lifetime code is changed.

## Owned-fork carrier

Repository: `teamleaderleo/FEX`

Branch: `diagnostic/generated-vulkan-split-bridge`

Reviewed stock base: `71afe476751deac24adabd1adb575fd2337b6e0a`

Workflow head: `44d3ceefc5f0eb0dce8d98f16226c23800fcd0c1`

Workflow: `.github/workflows/generated-vulkan-split-x11-callback-arm64.yml`

Run: `31777754207`

Job: `94696675245`

Artifact: `generated-vulkan-split-x11-31777754207`

Artifact ID: `9210598441`

Artifact zip SHA-256:

```text
6b542ff9db69325ffbbb19183ece0c17f09108fabb1241c2a995f985472fdcb1
```

## Generated split used by this run

`libvulkan-guest.so` remains an ordinary unloadable wrapper.

`libfex-vulkan-bridge.so` is a small generated companion DSO with `DF_1_NODELETE`.

The resident bridge owns:

- the exact `CallHostFunction` adapter for `vkEnumerateInstanceVersion`;
- the exact `CallHostFunction` adapter for `vkGetPhysicalDeviceXlibPresentationSupportKHR`;
- generic `CallbackUnpack` implementations for guest `XSync`, `XGetVisualInfo`, and `XDisplayString`.

The ordinary Vulkan wrapper performs API/name policy and publishes these resident addresses into FEX/host state.

## ELF proof

The ordinary wrapper reports:

```text
NEEDED: libfex-vulkan-bridge.so
SONAME: libvulkan.so.1
```

and has no `FLAGS_1: NODELETE`.

The bridge reports:

```text
SONAME: libfex-vulkan-bridge.so
FLAGS_1: NODELETE
```

The bridge's only runtime `NEEDED` dependency in this build is libc; X11 types used by the callback unpacker templates do not make the resident DSO own libX11 state.

## Real Vulkan trace

FEX publishes the Xlib native PFN against a resident bridge address:

```text
Linking address 0x7ffff77c7ee4 to host invoker 0x7ffff7e713e0
```

Before close:

```text
SPLIT_X11_BEFORE gipa=0x7ffff7ea23a0 xlib=0x7ffff77c7ee4 bridge_maps=5
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
Opening host-side X11 display: 0x12345000 -> 0xff6fa117c000
```

The probe then performs ordinary `dlclose(libvulkan.so.1)`.

The wrapper is physically gone while the resident bridge remains:

```text
SPLIT_X11_AFTER_CLOSE gipa_mapped=0 bridge_maps=5
```

The exact retained Xlib PFN is invoked again with a new guest Display token so the persistent host-side X11 manager must execute its retained guest callback route again:

```text
SPLIT_X11_AFTER_CLOSE_CALLBACK_BEGIN
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
Opening host-side X11 display: 0x12346000 -> 0xff6fa117e800
SPLIT_X11_AFTER_CLOSE_CALLBACK_RETURN result=0
GENERATED_VULKAN_SPLIT_X11_OK
```

Process exit: `0`.

## Meaning

The generated split now covers the two stale executable-address classes found in FEX source:

```text
native H -> resident guest CallHostFunction adapter
persistent host trampoline/helper -> resident guest callback unpacker
```

The ordinary wrapper can be physically reclaimed without invalidating either FEX-created escaped executable dependency.

This is materially different from runtime base-namespace NODELETE promotion. Base-only promotion failed the corresponding NEWLM callback adversary because another unloadable Vulkan generation could overwrite persistent host callback state with wrapper-owned unpackers and then disappear. The split bridge makes the published unpacker independent of wrapper generation, so that failure mechanism is removed at the ownership boundary rather than hidden by one resident wrapper generation.

## Scope implication

This result narrows when an execution lease/hazard is actually necessary.

If FEX gives **its own escaped bridge executable code** process lifetime, ordinary wrapper reclamation does not need to drain executions already selected into that bridge: the selected bridge bytes remain executable.

Direct ordinary API wrapper code can remain unloadable under the normal application requirement that code is not physically unloaded while it is actively executing.

A lease/hazard/grace-period protocol remains relevant only if FEX also requires reclamation of the resident bridge code itself or other generation-owned executable targets that FEX intentionally allows to outlive wrapper API lifetime.

## Remaining work

1. Force a moved Vulkan wrapper reload while verifying the resident bridge address stays constant and newly reacquired PFNs remain usable.
2. Replace the current fake companion API declarations with explicit function-type registration so thunkgen emits only required indirect signature thunks.
3. Generalize from two Vulkan signatures to all dynamic Vulkan signatures without duplicating ordinary wrapper packers.
4. Audit automatically generated callback parameters: their `CallbackUnpack` addresses can escape through host trampolines and must receive resident ownership too.
5. Prefer a per-library sidecar as the first generic implementation. Thunkgen's host function-pointer wrapper semantics include parameter annotations in addition to C signature; process-global cross-library deduplication needs a separate compatibility/identity audit.
6. Extend to GL/CUDA dynamic PFNs and Wayland's library-specific callback helpers after the Vulkan generator shape is clean.

Whole-wrapper NODELETE remains the smallest near-term product containment. The split bridge is now the strongest demonstrated architecture when physical wrapper unload/reset is desired.

All code and CI work stayed on owned repositories/forks. No upstream FEX interaction occurred.
