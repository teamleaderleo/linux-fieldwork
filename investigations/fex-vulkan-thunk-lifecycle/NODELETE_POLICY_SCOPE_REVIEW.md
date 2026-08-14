# Guest-thunk residency policy scope review

## Current recommendation

Treat FEX shared guest-thunk wrappers as process-resident implementation code once first loaded.

In the current design, `DF_1_NODELETE` on all shared guest-thunk targets is the smallest policy that matches the lifetime FEX already gives the corresponding host thunk and process-owned bridge metadata.

This is broader than the minimum needed for the Vulkan reproducer, but it is not arbitrary. FEX has no symmetric host-thunk unload protocol: every guest wrapper constructor invokes `fex:loadlib`, `ThunkHandler_impl::LoadLib()` `dlopen()`s the host thunk, registers its exports into process-owned maps, records the library in `Libs`, and never closes the host handle. Physical unload of only the guest half therefore creates a lifetime asymmetry that current FEX bookkeeping does not model.

## Real runtime evidence now covers both bridge directions

The generic shared-wrapper NODELETE candidate has real ARM64 hosted evidence with generated Vulkan thunks and native Lavapipe.

### Guest -> host dynamic PFN

Run `31772712092` retained a `vkEnumerateInstanceVersion` PFN returned through FEX's real GIPA path, called it successfully, performed ordinary guest `dlclose(libvulkan.so.1)`, verified the generated guest wrapper remained mapped, called the exact retained PFN again successfully, and reopened the wrapper at the same resident generation.

The retained mapping covered the guest `vkGetInstanceProcAddr` code after close, and the final marker was:

```text
REAL_NODELETE_VULKAN_PFN_OK
```

### Host -> guest callback trampoline

Run `31773642361` exercised the other concrete stale-address family. A real Vulkan Xlib PFN caused FEX's persistent host-side X11 manager to invoke generated host-to-guest trampolines. After ordinary guest `dlclose(libvulkan.so.1)`, a second guest Display token forced a fresh host X display and caused the retained trampoline to execute guest `XSync` and `XDisplayString` callbacks again. The final marker was:

```text
REAL_NODELETE_VULKAN_X11_CALLBACK_OK
```

No FEX core lifetime code was changed in either test; residency alone kept the executable guest bridge addresses valid.

## Why blanket residency is currently cleaner than a per-library allowlist

A per-library allowlist can identify obvious bridge publishers, but it would encode details of today's thunk implementations into CMake policy and would be easy to get wrong as interfaces evolve.

Current examples:

- Vulkan publishes native-PFN -> `CallHostFunction<signature>` mappings and callback unpackers.
- GL publishes the same dynamic-PFN adapters through `glXGetProcAddress` and registers guest X11/malloc callback unpackers.
- CUDA publishes native-PFN adapters through `cuGetProcAddress_v2` even though that fact is not obvious from only the top-level generator namespace declaration.
- Wayland does not use the same indirect-PFN generator mode, but it allocates/finalizes long-lived host-callable trampolines for guest listener callbacks and stores replacement listener tables in `wl_proxy` objects.
- EGL delegates `eglGetProcAddress` to the GL thunk, so its dynamic function-pointer lifetime is owned elsewhere.
- ALSA's current guest wrapper is nearly pure generated glue plus `LOAD_LIB(libasound)`; many callback APIs are disabled or stubbed.
- DRM has several guest allocation/string shims but no reviewed Vulkan-like dynamic PFN table.

A static allowlist based on these observations would need continuous auditing for new proc-address APIs, callback support, custom guest entrypoints, or generated function-pointer types. Making the base guest-thunk lifetime match the already-persistent host-thunk lifetime avoids that classification problem.

## Existing host-side contract is already process lifetime

`LOAD_LIB` / `LOAD_LIB_INIT` invokes the built-in `fex:loadlib` thunk from a guest DSO constructor.

`ThunkHandler_impl::LoadLib()` then:

1. `dlopen()`s `<name>-host.so`;
2. resolves and executes its export initializer;
3. stores exported thunk functions in the process-owned `Thunks` map;
4. records the library name in `Libs`;
5. keeps the host handle open for the rest of the process.

There is no paired guest destructor notification and no host `dlclose()` path in FEX-2608.

Consequently, physically unloading and reloading a guest wrapper does not recreate a symmetric FEX thunk generation. It reruns guest construction against host state that persisted from the prior load. The source itself comments that unload tracking would ideally happen before the backing guest memory disappears.

NODELETE makes that implicit process-lifetime contract explicit on the guest executable half as well.

## What NODELETE intentionally changes

The policy means a logical application `dlclose()` can drop its loader reference without physically reclaiming the generated guest thunk image before process exit.

Effects include:

- generated guest code and static storage remain mapped;
- guest wrapper constructors are not rerun for a later logical reopen of the same resident object;
- finalization/destructor timing moves to process exit;
- wrapper TLS/static state, if any, persists;
- stale bridge metadata may remain, but its executable destinations remain valid.

These are real semantics and should be documented as the FEX thunk implementation contract rather than described as ordinary physical DSO unload.

For current direct-only wrappers, the reviewed handwritten guest code is small and mostly process-level glue. ALSA is essentially generated thunks plus `LOAD_LIB`. DRM adds a few allocation/string ownership shims. EGL's custom proc-address entrypoint delegates to GL. No reviewed current wrapper has established a requirement that its generated thunk implementation must physically unload and reconstruct while the corresponding host thunk remains process-resident.

## Residency cost

The real generated Vulkan candidate's executable mapping observed in the hosted test was:

```text
7ffff7e82000-7ffff7eae000 r-xp ... libvulkan.so.1
```

which is `0x2c000` bytes (176 KiB) of executable mapping for that segment. This is not the complete file or complete resident-set cost, and should not be presented as such.

The remaining useful measurement is to record file size and mapped segment totals for every generated shared guest thunk under the generic policy. That is a cost measurement, not a correctness prerequisite.

## Why the sidecar design remains useful

The split resident bridge runtime remains the best escalation path if a concrete thunk demonstrates that physical wrapper unload/reset is valuable.

Executed models show that an unloadable wrapper can coexist with a NODELETE sidecar containing only:

- stable guest -> host `CallHostFunction` adapters and their signature-specific special thunks;
- stable host -> guest callback unpackers.

The stronger two-direction model survived 1,001 wrapper generations, allowed both bridge directions to execute after every wrapper unload, preserved stable bridge addresses, reset wrapper state on reopen, and remained clean under ASan+UBSan.

A per-library sidecar would therefore let FEX retain only pure bridge code while giving the ordinary wrapper real unload semantics. It is more generator/build work and should be paid for only if blanket wrapper residency causes a demonstrated compatibility or footprint problem.

## Why generation IDs / synthetic entrypoints / execution leases move down the list

Those mechanisms solve harder problems:

- synthetic guest bridge address `S` preserves caller/alias identity when raw native PFN `H` is insufficient;
- generation IDs distinguish bridge registrations across physical load generations;
- an execution lease or equivalent grace period is required to reclaim executable guest bytes safely while another thread may already be committed to entering them.

If guest thunk code is deliberately process-resident, there is no executable-byte reclamation event to race for that code, and old raw H -> T bridge routes remain valid. The real Vulkan NODELETE tests demonstrate exactly this containment.

Those mechanisms remain relevant if FEX later requires true physical guest-thunk unload, strict stale-pointer rejection, per-generation rebinding, or reclamation of bridge code.

## Policy decision tree

Use the generic shared-wrapper NODELETE policy unless one of these concrete counterexamples appears:

1. a thunk's guest-side constructor/destructor or TLS state must reset on logical `dlclose` / reopen for correctness;
2. retaining the full generated wrapper creates an unacceptable measured memory cost;
3. an application depends on physical disappearance of a thunk mapping rather than ordinary `dlclose` handle semantics;
4. FEX adds a real symmetric host-thunk unload/generation protocol.

If a counterexample appears, first move that thunk's pure bridge code to a resident sidecar. Escalate to owner/generation/lease machinery only when true bridge reclamation is also required.

## Current ranking

1. **Generic shared guest-thunk NODELETE**: smallest coherent contract with current FEX host-thunk lifetime; real Vulkan evidence now covers both bridge directions.
2. **Resident bridge sidecar + unloadable wrapper**: cleaner physical-unload semantics at higher generator/build complexity; strong synthetic evidence.
3. **Explicit owner/generation + revocation + execution grace period**: full reclamation model when physical unload is a hard requirement.
4. **Synthetic guest bridge identities**: useful specifically when raw native PFN identity/alias semantics become insufficient.

This review concerns owned-fork investigation only. It does not constitute or prepare an upstream FEX contribution.
