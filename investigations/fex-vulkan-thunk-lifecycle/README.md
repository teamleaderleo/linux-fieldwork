# FEX Vulkan thunk callback routing and unload lifecycle

## TL;DR

Two independent FEX Vulkan thunk failures were isolated while bringing an x86-64 Vulkan program up on an Apple M5 through an ARM64 Fedora guest.

1. **Dynamic `VK_EXT_debug_report` callback routing:** pristine FEX `FEX-2608` crashes with SIGILL when x86-64 `vulkaninfo` obtains `vkCreateDebugReportCallbackEXT` through `vkGetInstanceProcAddr()`. FEX already has a custom host implementation that replaces the guest callback with a native dummy callback, but `LookupCustomVulkanFunction()` does not return that custom implementation for `vkCreateDebugReportCallbackEXT`. Adding that lookup entry removes the SIGILL and allows Vulkan enumeration to complete. Current FEX `main` still omits the entry at `71afe476751deac24adabd1adb575fd2337b6e0a`.
2. **Guest Vulkan thunk unload:** after the callback-routing change, `vulkaninfo` completes enumeration but exits 139 during final teardown. FEX records an x86 instruction-fetch page fault whose saved guest RIP lies in the address range previously occupied by `libvulkan-guest.so`. Preventing guest `dlclose()` makes the run exit 0; a bogus preload still exits 139; pinning only `libvulkan-guest.so` also exits 0. This strongly localizes the second failure to unloading the guest Vulkan thunk while FEX still has execution state associated with it. No source fix for this second failure has been established yet.

The final pinned-thunk run enumerates `Virtio-GPU Venus (Apple M5)` and exits 0, proving x86-64 Vulkan → FEX → ARM64 Vulkan thunk → Venus → virtio-gpu → Apple M5 under the declared environment.

The second finding has now received an explicit adversarial source/history review. See [`ADVERSARIAL_REVIEW.md`](./ADVERSARIAL_REVIEW.md). The narrower leading hypothesis is stale dynamic-PFN CustomIR state, but the immediate dispatch edge remains unproved until a post-unload `CustomIRHandlers` hit is captured. The review preserves competing explanations and a discriminating experiment matrix rather than treating the current hypothesis as settled.

No upstream contact has been made. FEX currently states `No AI/ML/LLM/etc code contributions.` and its `AGENTS.md` says AI must not generate code for contributions. The source edit used during this investigation is therefore **diagnostic evidence only, not an upstream-submittable code contribution**. A human considering a FEX patch must independently derive and implement it in compliance with FEX policy.

## Explain like I'm five

FEX lets an x86-64 program call native ARM64 libraries through generated bridge code. Vulkan has functions that can contain callbacks back into the application.

The first crash looked like this:

```text
x86 vulkaninfo asks for vkCreateDebugReportCallbackEXT
    ↓
FEX returns a path that bypasses its callback-sanitizing wrapper
    ↓
native ARM Vulkan code receives an x86 callback address
    ↓
ARM CPU tries to execute x86 bytes
    ↓
SIGILL
```

FEX already had the safe wrapper. The dynamic function lookup did not select it. Selecting the existing wrapper removes that crash.

The second failure happens later:

```text
vulkaninfo finishes and unloads Vulkan
    ↓
libvulkan-guest.so disappears from the guest address map
    ↓
FEX still has guest execution state pointing into that old thunk image
    ↓
FEX synthesizes the guest page fault
    ↓
exit 139
```

Keeping only `libvulkan-guest.so` loaded makes the exact same run exit 0.

## Why care

This sits directly on FEX's x86-to-native Vulkan boundary. A program using `VK_EXT_debug_report` through dynamic Vulkan lookup can crash before useful Vulkan work begins. Once that callback path is corrected, unloading the generated Vulkan guest thunk can still crash an otherwise successful program during normal library teardown.

The observed workload is not a synthetic call to one private helper: Fedora x86-64 `vulkaninfo` reaches the native ARM64 Vulkan loader, enumerates llvmpipe and Venus, and on the final control enumerates the Apple M5 Venus device before exiting successfully.

## Current state

- State: `REVIEW`
- Fieldwork branch: `investigation/fex-vulkan-thunk-lifecycle`
- Exact Fieldwork head: advanced by the adversarial review record
- Source revision executed: FEX tag `FEX-2608` → `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- Current upstream source checked: `main` → `71afe476751deac24adabd1adb575fd2337b6e0a`
- Latest authoritative gate: x86-64 `vulkaninfo --summary` with FEX Vulkan guest thunk pinned, Venus path selected, exit `0`
- Leading unload hypothesis after adversarial review: stale dynamic-PFN CustomIR registration whose guest target lives in the unloaded thunk image
- Exact proof gap: no retained trace yet shows post-unload `CustomIRHandlers` dispatch selecting the dead `CallHostFunction` target
- First incomplete step: capture `REGISTER → UNMAP → CUSTOMIR HIT → dead target`, then run a forced changed-base reload; separately, a human must independently implement any upstream code candidate because FEX disallows AI-generated contribution code
- Cleanup state: `/tmp` recovered after coredump exhaustion; retained 2 GiB diagnostic core in guest home; no upstream state changed
- Next safe action: execute the discriminating local controls in `ADVERSARIAL_REVIEW.md` before choosing a source-level fix
- External-contact state: **none authorized or made**

## Intent and precedent

FEX merged a 2022 Vulkan thunk change specifically to work around the lack of generic callback support for `VK_EXT_debug_report`. That change added `DummyVkDebugReportCallback`, custom `vkCreateDebugReportCallbackEXT` / `vkDestroyDebugReportCallbackEXT` implementations, and explicit handling of the debug-report callback embedded in `VkInstanceCreateInfo::pNext`.

Precedent: `https://redirect.github.com/FEX-Emu/FEX/pull/1803`.

That history is important because it makes the intended invariant explicit: guest debug-report callbacks must not be passed directly to native host Vulkan code while generic callback translation is unavailable.

At both `FEX-2608` and current `main`, `LookupCustomVulkanFunction()` includes several custom Vulkan implementations but omits `vkCreateDebugReportCallbackEXT`. `vkGetInstanceProcAddr()` checks that lookup before returning a native address. The observed SIGILL disappears when the missing create entry is supplied.

FEX contribution policy was checked at both `FEX-2608` and current `main`:

```text
CONTRIBUTING.md: No AI/ML/LLM/etc code contributions.
AGENTS.md: AI must not be used to generate code for contributions to this project.
```

Therefore the investigation may preserve exact diagnostic source edits and behavior, but those edits are not presented as submit-ready contribution code.

## Question

Under the declared ARM64 Fedora/FEX environment:

1. Does dynamic `vkGetInstanceProcAddr()` lookup bypass FEX's existing custom debug-report callback implementation and cause native ARM64 execution to enter an x86 callback address?
2. After correcting that boundary, does guest unloading of `libvulkan.so.1` / `libvulkan-guest.so` cause a stale guest execution target that produces the final SIGSEGV?

## Source

- Project: FEX-Emu/FEX
- Repository: `https://redirect.github.com/FEX-Emu/FEX`
- Requested/executed revision: tag `FEX-2608`
- Resolved tag commit: `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- Current-main source review: `71afe476751deac24adabd1adb575fd2337b6e0a`
- Local source path: `~/src/FEX-2608`
- Build directory: `~/src/FEX-2608/Build`
- Install prefix: `/opt/fex-2608`
- Local source state: dirty diagnostic/candidate edits in `ThunkLibs/libvulkan/Host.cpp`; no canonical source commit was created during the investigation
- Guest Vulkan thunk: `/opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so`
- Host Vulkan thunk: `/opt/fex-2608/lib64/fex-emu/HostThunks/libvulkan-host.so`

## Environment

- Host: Apple M5 MacBook Air, macOS / Darwin 25.6.0, arm64
- Virtualization: Lima 2.2.0 + krunkit 1.3.2
- VM: `bb-linux`, 6 vCPUs, 8 GiB RAM, 50 GiB disk
- Guest: Fedora Linux 44 Cloud Edition, aarch64
- Guest kernel: `6.19.10-300.fc44.aarch64`
- GPU device: virtio-gpu exposed as `/dev/dri/card0` and `/dev/dri/renderD128`
- Mesa: `25.3.6-102.fc44.aarch64` from the `mesa-libkrun-vulkan` COPR path used in this VM
- Native Vulkan driver: Venus, reporting `Virtio-GPU Venus (Apple M5)`
- Software Vulkan control: llvmpipe, Mesa 25.3.6 / LLVM 22.1.0
- x86-64 test program: Fedora x86-64 `vulkaninfo`
- FEX rootfs: `/usr/share/fex-emu/RootFS/default.erofs`
- FEX guest config enabled GL, Vulkan, and drm thunks
- FEX CPU translation control: `FEXBash -c 'uname -m'` returned `x86_64`

Native ARM64 `vulkaninfo --summary` worked before any FEX Vulkan debugging and enumerated Venus plus llvmpipe. This establishes that M5 → krunkit → virtio-gpu → Venus was already working natively in the guest.

A separate accelerated OpenGL/Zink path remains blocked because Venus reports `VK_EXT_robustness2` with `nullDescriptor=false`; that is not part of this Vulkan thunk claim.

## Baseline behavior

### Native guest Vulkan

Native ARM64 Vulkan works and enumerates:

```text
deviceName = Virtio-GPU Venus (Apple M5)
driverName = venus
driverInfo = Mesa 25.3.6
```

### Pristine FEX 2604 and 2608

Running the x86-64 `vulkaninfo --summary` through packaged FEX 2604 produced SIGILL. A source build of pristine `FEX-2608` reproduced the same SIGILL.

Layer controls did not change the failure:

```text
VK_LOADER_LAYERS_DISABLE='*MESA*'
VK_LOADER_LAYERS_DISABLE='~all~'
```

GDB/core inspection showed native ARM64 Vulkan/loader code on the call path, followed by a PC inside x86 guest code. This was consistent with a native ARM callback path jumping directly to the guest callback address.

Khronos `vulkaninfo` constructs a `VkDebugReportCallbackCreateInfoEXT`, passes it in the `VkInstanceCreateInfo.pNext` chain, then obtains/calls `vkCreateDebugReportCallbackEXT` dynamically. FEX's `vkCreateInstance` path already strips/sanitizes the debug-report pNext path, but the later explicit dynamically obtained callback function still bypassed the custom host wrapper.

## Hypothesis / candidate A — dynamic custom Vulkan lookup

Source at `FEX-2608` already contains a custom host implementation for `vkCreateDebugReportCallbackEXT` that copies the guest create-info and replaces `pfnCallback` with `DummyVkDebugReportCallback` before calling the native Vulkan function.

`LookupCustomVulkanFunction()` did not return that function for dynamic lookup. Diagnostic candidate:

```cpp
} else if (a_1 == "vkCreateDebugReportCallbackEXT"sv) {
  return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkCreateDebugReportCallbackEXT;
}
```

This is an **experimental source edit used to establish causality**, not contribution-ready code.

After rebuilding and forcing the `/opt/fex-2608` host thunk, the custom wrapper was hit and the original SIGILL disappeared. `vulkaninfo` proceeded through full device enumeration.

A symmetric `vkDestroyDebugReportCallbackEXT` lookup entry was also tested later. Instrumentation proved its custom wrapper ran and that the native destroy call returned, but the final exit-139 remained. This means the destroy routing is not sufficient to explain the second failure and should not be conflated with the create-callback result without an independent A/B test.

Current upstream `main` at `71afe476751deac24adabd1adb575fd2337b6e0a` still omits these debug-report entries from `LookupCustomVulkanFunction()`.

## Results A — callback routing

Observed sequence after adding the create lookup:

```text
FEXDBG instance pNext debug-report callback=<guest address>
FEXDBG before native vkCreateInstance pNext=(nil)
FEXDBG explicit debug-report custom wrapper hit ...
```

The original SIGILL no longer occurred. Vulkan enumeration completed.

This supports the bounded claim:

> Dynamic `vkGetInstanceProcAddr()` lookup for `vkCreateDebugReportCallbackEXT` can bypass FEX's existing callback-sanitizing custom implementation. Routing the lookup to the existing custom implementation removes the observed native-ARM-to-x86 callback SIGILL.

## Hypothesis / candidate B — guest Vulkan thunk unload

After the callback-routing edit, `vulkaninfo` printed the expected Vulkan summary but exited 139 during teardown.

The debug-report destroy path was instrumented:

```text
FEXDBG destroy debug-report wrapper hit ...
FEXDBG destroy debug-report before native
FEXDBG destroy debug-report after native
```

The process still exited 139, proving the native `vkDestroyDebugReportCallbackEXT` call itself returned.

GDB initially stopped on FEX-internal SIGBUS alignment handling. Allowing SIGBUS to pass reached the stable final SIGSEGV at FEX dispatcher address `0x8000595804b4`.

Source inspection showed that address corresponds to FEX's deliberate `GuestSignal_SIGSEGV` trampoline, which synthesizes a guest SIGSEGV by loading through address zero. The relevant guest fault record was:

```text
State.rip = 0x7ffff7cd21f0
FaultToTopAndGeneratedException = true
Signal = 11
TrapNo = 14
si_code = 2
err_code = 21   # 0x15
```

`TrapNo=14` is an x86 page fault. `err_code=0x15` includes the instruction-fetch bit. At the time of the crash, `0x7ffff7cd21f0` was no longer mapped.

The process map had an unmapped hole from approximately `0x7ffff7c87000` through `0x7ffff7cdc000`. Treating `0x7ffff7c87000` as the former base of `libvulkan-guest.so` gives:

```text
0x7ffff7cd21f0 - 0x7ffff7c87000 = 0x4b1f0
```

`addr2line` against `libvulkan-guest.so` resolves `0x4b1f0` inside a generated `CallHostFunction<...>` in `ThunkLibs/include/common/Guest.h`. `objdump` shows `0x4b1f0` is inside the generated x86 thunk body rather than a live mapped DSO at crash time. FEX documents that saved `State.rip` may be imperfect while JIT is active, so the exact byte should not be overinterpreted; the durable observation is that the saved guest execution location belongs to the old thunk image range after that image has disappeared.

## Results B — unload controls

### Control 1: normal post-callback-fix run

With llvmpipe forced:

```text
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Result: Vulkan enumeration succeeds; final exit `139`.

### Control 2: make guest `dlclose()` a no-op

A tiny x86-64 preload object exported:

```c
int dlclose(void *handle) {
    (void)handle;
    return 0;
}
```

With that x86 object in `LD_PRELOAD`, the same llvmpipe test exits `0`.

The ARM64 host loader reports that it cannot preload the x86 object; this warning is expected. The distinguishing behavior occurs in the x86 guest loader under FEX.

### Negative control: bogus preload

Using a nonexistent preload path preserves the loader-warning class but does not override guest `dlclose()`:

```text
LD_PRELOAD=$PWD/does-not-exist.so ... vulkaninfo --summary
```

Result: exit `139`.

This rules out the explanation that merely setting `LD_PRELOAD` or producing preload warnings changes the result.

### Control 3: pin only FEX's Vulkan guest thunk

`libvulkan-guest.so` has SONAME `libvulkan.so.1`.

```text
LD_PRELOAD=/opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so \
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Result: exit `0`.

This is the cleanest workaround because it keeps only the guest Vulkan thunk resident instead of globally disabling `dlclose()`.

### Final integration control: Venus / Apple M5

Without forcing llvmpipe, while pinning the Vulkan guest thunk:

```text
LD_PRELOAD=/opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Result:

```text
exit=0
deviceName = Virtio-GPU Venus (Apple M5)
driverName = venus
driverInfo = Mesa 25.3.6
```

llvmpipe is also enumerated as a fallback device.

## Interpretation

### Demonstrated behavior

- Native ARM64 Vulkan on the guest is healthy and can enumerate Venus on Apple M5.
- Pristine `FEX-2608` reproduces the x86 Vulkan SIGILL.
- FEX already has a custom debug-report callback implementation intended to prevent native code from executing a guest callback.
- Dynamic `vkGetInstanceProcAddr()` lookup does not select that custom implementation for `vkCreateDebugReportCallbackEXT` in `FEX-2608` or current `main`.
- Adding that lookup route removes the original SIGILL and permits Vulkan enumeration.
- The later exit-139 survives successful native debug-report destruction.
- Preventing guest library unload changes exit 139 to 0.
- A bogus preload does not change 139.
- Pinning only `libvulkan-guest.so` changes 139 to 0.
- With the callback route plus thunk pin, x86 `vulkaninfo` enumerates Venus on Apple M5 and exits 0.

### Strong inference

The second failure is a guest-thunk lifecycle/unload problem: unloading `libvulkan-guest.so` leaves FEX with execution/JIT/thunk state that can still resolve or return into the old guest thunk image.

The adversarial review narrows the leading mechanism to stale dynamic-PFN CustomIR state while keeping ordinary guest pointers, host-to-guest trampolines, ordinary JIT/lookup invalidation, code-cache relocation, Vulkan teardown ordering, and generic thunk-library lifetime as explicit competitors until the direct dispatch trace is captured.

### Not yet established

- The exact FEX source owner that must retain/invalidate thunk execution state across `dlclose()`.
- Whether stale CustomIR is the immediate dispatch edge in the observed teardown fault.
- Whether the second bug is Vulkan-specific or a generic thunk-library unload defect exposed by Vulkan.
- The minimal upstream source fix for the unload defect.
- Whether `vkDestroyDebugReportCallbackEXT` also requires an explicit custom lookup entry independently of the create fix; the tested destroy entry is plausible and its wrapper runs, but no isolated baseline/candidate A/B was performed for it.
- Current-main runtime reproduction. Current `main` was source-read and confirmed to retain the missing lookup, but the executed runtime was `FEX-2608`.

## Evidence boundary

This investigation establishes behavior on:

- Apple M5 host;
- Lima + krunkit;
- Fedora 44 ARM64 guest;
- kernel `6.19.10-300.fc44.aarch64`;
- Mesa 25.3.6;
- FEX `FEX-2608` source build;
- Fedora x86-64 `vulkaninfo`;
- llvmpipe and Venus Vulkan drivers.

It does not establish:

- Wine or Proton behavior;
- Battle Brothers behavior;
- GUI/presentation support inside the headless Lima guest;
- accelerated OpenGL through Zink;
- behavior on other host architectures or hypervisors;
- behavior of a current-main FEX binary;
- that the unload defect is generic to every FEX thunk library;
- an upstream-acceptable code patch.

## Next step

1. Capture the direct CustomIR causal trace and prove exact `GuestMunmap` invalidation coverage.
2. Force an unload/reload at a changed guest base and record native PFN stability plus old/new guest invoker addresses.
3. Split dynamic-PFN registration from host-to-guest callback registration, then exercise another thunked library such as libGL.
4. If a human wants to propose a callback-routing patch upstream, the human independently derives and implements the code because FEX prohibits AI-generated code contributions.
5. Prepare a human-submittable issue/reproduction report, not an AI-generated code PR.
6. Only after the Vulkan thunk record is frozen should the Battle Brothers path resume with a writable x86-64 userspace and Wine/Proton.

Detailed controls and interpretation rules are retained in [`ADVERSARIAL_REVIEW.md`](./ADVERSARIAL_REVIEW.md).

## Authority

- Automated FEX upstream contact: **not authorized and not performed**.
- FEX upstream issue/PR/comment/review/reaction/push/discussion: none created by this work.
- Owned-repository work: writable; investigation records and local/owned experimental work may be committed here.
- FEX contribution policy: AI-generated code contributions are prohibited; diagnostic source edits are retained only as evidence.