# Human-facing upstream report drafts — FEX Vulkan thunk failures

## In simple words

These are preparation-only drafts for a human to review. No upstream issue, pull request, comment, or other interaction has been created by this investigation.

FEX currently prohibits AI-generated code contributions (`CONTRIBUTING.md`: `No AI/ML/LLM/etc code contributions.`; `AGENTS.md`: `AI must not be used to generate code for contributions to this project.`). Because the local source edit was AI-assisted, this packet deliberately **does not provide an upstream PR patch or claim that the diagnostic edit is eligible for submission**.

A human may use the reproduction and source map to file a bug report. If a human later wants to contribute code, the human should independently derive, implement, test, and review that code under FEX's policy.

The two failures should be reported separately unless a human reviewer finds a single source owner that clearly links them.

---

# Draft A — `vkGetInstanceProcAddr` bypasses FEX's custom `VK_EXT_debug_report` callback wrapper

## Suggested title

`Vulkan: dynamic vkCreateDebugReportCallbackEXT lookup bypasses custom callback thunk`

## Suggested body

### Summary

On ARM64 FEX, an x86-64 Vulkan application that obtains `vkCreateDebugReportCallbackEXT` through `vkGetInstanceProcAddr()` can bypass FEX's existing custom implementation for `VK_EXT_debug_report`. With Fedora x86-64 `vulkaninfo`, the result is a SIGILL consistent with native ARM Vulkan code attempting to execute an x86 guest callback address.

FEX already contains the intended callback-sanitizing implementation: it replaces the guest `pfnCallback` with `DummyVkDebugReportCallback` before calling the native Vulkan function. The missing boundary appears to be the custom-function lookup used by `vkGetInstanceProcAddr()`.

This reproduces on the `FEX-2608` release. I also checked current `main` at `71afe476751deac24adabd1adb575fd2337b6e0a`; the lookup table still does not list `vkCreateDebugReportCallbackEXT`.

Historical context: `https://redirect.github.com/FEX-Emu/FEX/pull/1803` added the existing debug-report callback workaround specifically because generic guest callbacks were not available. That makes the intended callback boundary fairly clear.

### Environment

```text
Host: Apple M5 MacBook Air / arm64
VM: Lima 2.2.0 + krunkit 1.3.2
Guest: Fedora Linux 44 Cloud Edition / aarch64
Kernel: 6.19.10-300.fc44.aarch64
Mesa: 25.3.6
FEX: FEX-2608, commit e869aa644a16e4332cdc15c1ea0b4d13d482385d
Guest native Vulkan: Venus + llvmpipe
Test program: Fedora x86-64 vulkaninfo
```

Native ARM64 `vulkaninfo --summary` works and enumerates `Virtio-GPU Venus (Apple M5)`.

### Reproduction

With a source-built, otherwise pristine `FEX-2608` and the Fedora x86-64 `vulkaninfo` binary:

```sh
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Observed baseline: SIGILL.

Disabling Mesa/all Vulkan layers did not change the failure class.

### Source observation

`vulkaninfo` uses `VK_EXT_debug_report`, including a `VkDebugReportCallbackCreateInfoEXT` and an explicit `vkCreateDebugReportCallbackEXT` call obtained through instance function loading.

FEX has:

- `DummyVkDebugReportCallback`;
- custom `vkCreateDebugReportCallbackEXT` and `vkDestroyDebugReportCallbackEXT` host implementations;
- debug-report handling in the `vkCreateInstance` pNext path.

But `LookupCustomVulkanFunction()` does not return the custom `vkCreateDebugReportCallbackEXT` implementation. `FEXFN_IMPL(vkGetInstanceProcAddr)` consults this lookup before falling back to the native loader address.

### Distinguishing result

For diagnostic purposes, I locally made the dynamic lookup select the existing custom create implementation. With no other intended behavioral change, the original SIGILL disappeared, FEX's custom debug-report wrapper was hit, and `vulkaninfo` proceeded through Vulkan device enumeration.

I am intentionally not attaching or proposing that local code as a contribution because the investigation was AI-assisted and FEX's contribution policy forbids AI-generated code contributions.

### Expected behavior

A guest function pointer returned for `vkCreateDebugReportCallbackEXT` should preserve the same callback-sanitizing behavior as FEX's existing custom implementation, rather than allowing a native host Vulkan path to receive/execute the guest callback directly.

### Additional notes / limits

- Executed runtime was `FEX-2608`; current `main` was source-read, not built/executed.
- After this SIGILL is removed, a separate teardown SIGSEGV becomes visible. I have a distinct reproduction showing that pinning `libvulkan-guest.so` prevents that second failure; I would report that separately because it appears to be a guest-thunk unload/lifecycle problem.
- I also tested routing `vkDestroyDebugReportCallbackEXT` through the custom lookup. Its custom wrapper ran and the native destroy call returned, but that did not resolve the separate teardown failure. I do not have an isolated A/B result establishing whether the destroy lookup entry is independently required.

---

# Draft B — unloading `libvulkan-guest.so` causes a guest instruction-fetch fault after successful `vulkaninfo`

## Suggested title

`Vulkan thunk: dlclose/unload leaves stale guest execution state and crashes during teardown`

## Suggested body

### Summary

After correcting a separate `VK_EXT_debug_report` callback-routing problem, Fedora x86-64 `vulkaninfo` can complete Vulkan enumeration through FEX on ARM64 but exits 139 during normal final teardown.

The failure is strongly tied to unloading FEX's Vulkan guest thunk:

- normal run after the callback-routing correction: exit 139;
- guest `dlclose()` replaced with a no-op: exit 0;
- bogus/nonexistent preload control: exit 139;
- only `/opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so` pinned through `LD_PRELOAD`: exit 0;
- same pinned-thunk control without forcing llvmpipe: exit 0 while enumerating `Virtio-GPU Venus (Apple M5)`.

This suggests FEX retains execution/JIT/thunk state that can still refer to the guest Vulkan thunk after the guest dynamic loader has unmapped it.

### Environment

```text
Host: Apple M5 MacBook Air / arm64
VM: Lima 2.2.0 + krunkit 1.3.2
Guest: Fedora Linux 44 Cloud Edition / aarch64
Kernel: 6.19.10-300.fc44.aarch64
Mesa: 25.3.6
FEX: FEX-2608, commit e869aa644a16e4332cdc15c1ea0b4d13d482385d
Guest thunk: /opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so
Test program: Fedora x86-64 vulkaninfo
```

### Baseline after the callback-routing issue is avoided

Force llvmpipe to remove Venus/virtio from the equation:

```sh
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

`vulkaninfo` reaches the normal summary/device output, then exits 139.

I instrumented FEX's existing `vkDestroyDebugReportCallbackEXT` custom host implementation. It was entered, the native destroy call was made, and the native destroy call returned before the final crash.

### FEX guest-fault evidence

GDB stops at FEX dispatcher address `0x8000595804b4`. FEX source identifies this as its deliberate `GuestSignal_SIGSEGV` trampoline rather than an accidental native null dereference.

At that point:

```text
State.rip = 0x7ffff7cd21f0
FaultToTopAndGeneratedException = true
Signal = 11
TrapNo = 14
si_code = 2
err_code = 21  # 0x15
```

The x86 trap number is page fault (`#PF`), and the error code includes the instruction-fetch bit.

At crash time, the saved guest RIP was not mapped. The surrounding process map contained an unmapped hole approximately:

```text
0x7ffff7c87000 - 0x7ffff7cdc000
```

Using the start of that old range as a candidate previous load base:

```text
0x7ffff7cd21f0 - 0x7ffff7c87000 = 0x4b1f0
```

`addr2line` for offset `0x4b1f0` in `libvulkan-guest.so` resolves inside a generated `CallHostFunction<...>` from `ThunkLibs/include/common/Guest.h`.

The exact saved RIP should not be overinterpreted as an instruction boundary because FEX notes that `State.rip` can be imperfect while JIT is active. The durable observation is that the saved guest execution location belongs to the old Vulkan guest-thunk image range after the image is no longer mapped.

### Distinguishing controls

#### A. Disable guest `dlclose()`

I built a tiny x86-64 preload object exporting:

```c
int dlclose(void *handle) {
    (void)handle;
    return 0;
}
```

Then:

```sh
LD_PRELOAD=$PWD/libnodlclose.so \
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Result: exit 0.

The native ARM loader warns that it cannot preload the x86 object. That warning is expected; the x86 guest loader under FEX is the relevant consumer.

#### B. Bogus preload negative control

```sh
LD_PRELOAD=$PWD/does-not-exist.so \
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Result: exit 139.

So merely setting `LD_PRELOAD` / producing preload warnings is not sufficient to change the outcome.

#### C. Pin only `libvulkan-guest.so`

The guest thunk has SONAME `libvulkan.so.1`.

```sh
LD_PRELOAD=/opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so \
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Result: exit 0.

#### D. Venus / Apple M5 control

```sh
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

### Expected behavior

Unloading a guest thunk library during ordinary `dlclose()` should not leave FEX execution state capable of returning/jumping into the unmapped thunk image. Either the relevant generated/thunk/JIT state should remain valid for the required lifetime, or unloading should invalidate/update every reference that can still be executed.

### Limits / open question

I have not identified the smallest source-level owner/fix yet. In particular, I do not know whether this is Vulkan-specific or a generic thunk-library unload issue that Vulkan happens to expose.

This report is therefore a reproduction and lifecycle localization, not a proposed patch.

---

# Duplicate / precedent search receipt

Performed before packet preparation on 2026-08-13:

- FEX issues searched for Vulkan debug-report callback / `vkCreateDebugReportCallbackEXT` / SIGILL: no matching issue returned by the repository search used here.
- FEX pull requests searched for `vkCreateDebugReportCallbackEXT`: historical merged `https://redirect.github.com/FEX-Emu/FEX/pull/1803` found and incorporated as intent/precedent.
- FEX issues and pull requests searched for `dlclose`, guest thunk unload, and Vulkan thunk unload: no matching result returned by the searches used here.

This is a bounded duplicate search, not a guarantee that differently worded historical discussions do not exist.

# Human review checklist before any manual upstream issue

- Reproduce once more from a clean VM/session or retain the exact current logs.
- Confirm exact FEX runtime revision in the issue text.
- Decide whether to report A and B as separate issues; current evidence favors separate reports.
- Remove local `FEXDBG` wording from any reproduction unless it is necessary to explain a boundary.
- Do not attach the AI-assisted source diff as contribution code.
- Keep claims at the observed platform/revision boundary.
- If a human later independently implements a patch, run FEX's required build/tests and re-check current `main` before manual submission.
- Automated upstream contact remains prohibited by Fieldwork and has not occurred.
