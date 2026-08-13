# Hosted callback runtime blockers

Exact FEX source: `71afe476751deac24adabd1adb575fd2337b6e0a`  
Hosted callback run: `31729320992`  
Evidence artifact: `fex-vulkan-callback-probe-31729320992` (`sha256:1fe1d608042e2b5ea03890586d74b3f83bcdbb320d149d42d672bf060338934c`)

## Current evidence boundary

The hosted ARM64 lane now proves all of the following:

- exact-current FEX configures, builds, and installs with Vulkan host/guest thunks;
- the source audit finds exactly three missing callback-family custom dynamic registrations: `vkCreateDebugReportCallbackEXT`, `vkDestroyDebugReportCallbackEXT`, and `vkCreateDebugUtilsMessengerEXT`;
- native llvmpipe controls exercise both debug-report and debug-utils callbacks;
- the FEX callback matrix still stops before the callback-routing discriminator.

Run `31729320992` recorded exit `132` for baseline and experimental FEX callback cases. With FEX logging enabled, the first FEX-owned failure is:

`Thunks.cpp:291, MakeHostTrampolineForGuestFunction: Tried to create host-trampoline to null pointer guest function`

This occurs before the callback probe reaches its Vulkan callback logic, so candidate equality in that run is an environment/fixture ceiling.

## Question: which guest function is null?

`ThunkLibs/libvulkan/Guest.cpp::OnInit()` does this during Vulkan guest-thunk initialization:

1. `dlopen("libX11.so.6", RTLD_LAZY)`;
2. `dlsym(..., "XSync")`;
3. `dlsym(..., "XGetVisualInfo")`;
4. `dlsym(..., "XDisplayString")`;
5. sends all three guest addresses to the host through `Vulkan_SetGuestX*` calls.

The minimal exported `ubuntu:24.04` rootfs used by the hosted probe does not contain the guest X11 runtime. `Guest.cpp` does not validate the `dlopen` or `dlsym` results before sending them to the host.

`ThunkLibs/libvulkan/Host.cpp` then unconditionally calls `MakeHostTrampolineForGuestFunctionAt()` for each supplied target. `Source/Tools/LinuxEmulation/Thunks.cpp` asserts that `GuestTarget` is nonzero. This source path matches the hosted assertion exactly.

For this headless callback probe, X11 WSI is never exercised. The narrow fixture repair is therefore a guest x86-64 `libX11.so.6` shim exporting only `XSync`, `XGetVisualInfo`, and `XDisplayString`, with no runtime dependencies. A source fixture for that shim is tracked as `fex_probe_x11_stub.c`.

A separate rootfs preflight (`31730786364`) established that the public ARM runner can pull and create amd64 Docker images but cannot execute them: the amd64 container exits before `docker exec ... uname -m`. Installing guest X11 by executing `apt` inside the amd64 container is therefore unsuitable for this runner. Cross-compiling the three-symbol shim avoids that dependency.

## Question: is the host thunk ABI paired correctly?

The existing callback workflow uses:

`find "$GITHUB_WORKSPACE/fex-install" -type f -name libvulkan-host.so | head -1`

The install contains both:

- `lib/fex-emu/HostThunks/libvulkan-host.so` — 64-bit guest ABI;
- `lib/fex-emu/HostThunks_32/libvulkan-host.so` — 32-bit guest ABI.

The x86 callback probe is a 64-bit guest. Run `31729320992` selected the `_32` directory for the baseline because the lookup is order-dependent.

The report/family candidate build steps contain the same class of ambiguity with `find build -type f -name libvulkan-host.so | head -1`. Candidate builds should use `build/HostLibs_64/libvulkan-host.so` explicitly.

The next hosted run should pin every pairing by exact path:

- guest thunk: `share/fex-emu/GuestThunks/libvulkan-guest.so`;
- baseline host thunk: `lib/fex-emu/HostThunks/libvulkan-host.so`;
- rebuilt candidates: `build/HostLibs_64/libvulkan-host.so`.

## Question: what matrix should run after the fixture is repaired?

Use these gates in order:

1. Native debug-report and debug-utils positive controls: callback count greater than zero.
2. Baseline direct symbol lookup for each create function: expected clean exit with callback count zero. This proves the existing custom wrapper itself works.
3. Baseline `vkGetInstanceProcAddr` lookup: expected failure at the guest/host callback boundary for the missing custom registration.
4. Report-only custom-lookup candidate: debug-report should become clean while debug-utils remains a failing control.
5. Complete callback-family candidate containing all three missing registrations: report and utils should both become clean.
6. Scope-preserving/native-gated candidate: native GIPA/GDPA decides availability first, then FEX substitutes a custom implementation only for a non-null native result.

The report-only stage is valuable because it independently discriminates the adjacent debug-utils omission. The destroy wrapper belongs in the complete family candidate even though the callback probe exits before teardown.

## Question: why is a flat common lookup a diagnostic edit instead of the preferred final design?

History shows the shared `LookupCustomVulkanFunction()` came from the old `vkGetDeviceProcAddr` custom list and was later reused by `vkGetInstanceProcAddr`. That erased instance/device command scope from the handwritten substitution policy.

Current code checks `LookupCustomVulkanFunction()` before native GIPA/GDPA. A flat addition of instance callback commands can therefore make GDPA return a FEX custom pointer for a command that native Vulkan would reject in that scope.

Preferred production direction:

1. query native GIPA/GDPA for the requested object/name;
2. if native returns null, return null;
3. if native returns a PFN and FEX has a custom implementation for that command, return the FEX custom implementation;
4. otherwise return the native PFN.

This preserves native availability, enabled-extension behavior, and GIPA/GDPA scope while still preventing dynamic lookup from bypassing FEX's callback-safe wrappers.

## Small tracked lab helpers

- `audit_custom_lookup.py` — current mismatch invariant;
- `apply_callback_lookup_candidate.py` — report-only / complete-family candidate transformation;
- `fex_probe_x11_stub.c` — headless three-symbol guest X11 fixture;
- `prepare_hosted_callback_fixture.sh` — exact 64-bit thunk path and shim preparation helper.

## Reopen / next-run conditions

Treat Finding A runtime causality as independently reproduced on hosted ARM64 only when the repaired fixture reaches probe code and produces a separating baseline/candidate matrix. Until then, the original retained target-environment A/B remains the runtime authority, while hosted CI provides independent source, build, native-fixture, and pre-main failure evidence.

No FEX upstream contact has occurred.
