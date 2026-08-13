# Hosted ARM64 Vulkan guest-X11 prerequisite A/B

Date: 2026-08-14

This follow-up resolves the early hosted ARM64 exit-132 seen before Finding A callback code ran.

Exact source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a` (`https://redirect.github.com/FEX-Emu/FEX/commit/71afe476751deac24adabd1adb575fd2337b6e0a`). FEX upstream remained read-only. The executable experiment ran only in the owned `teamleaderleo/FEX` fork.

Owned workflow run: `teamleaderleo/FEX` run `31732977682`, artifact `9194131751`, artifact digest `sha256:23d825e255f73bbd5799d455c1b9ea968b6f6755d2a4f4eaffc60e3d15c76471`.

The job built the exact FEX runtime, `vulkan-host-64`, and x86-64 `vulkan-guest` thunk. It then ran the same x86 program whose only operation after entering `main` was `dlopen("libvulkan.so.1", RTLD_NOW|RTLD_LOCAL)`.

## A/B

Without guest `libX11.so.6` in the amd64 rootfs:

```text
BEFORE_DLOPEN
exit=132
```

Then a tiny guest x86-64 `libX11.so.6` exporting only the three symbols resolved by Vulkan `Guest.cpp::OnInit()` was installed:

- `XSync`
- `XGetVisualInfo`
- `XDisplayString`

With that library present, holding FEX, Vulkan thunks, rootfs, and command constant:

```text
BEFORE_DLOPEN
AFTER_DLOPEN
exit=0
```

Matrix:

```text
fex_sha=71afe476751deac24adabd1adb575fd2337b6e0a
no_x11=132
with_x11=0
```

## Conclusion

The earlier hosted ARM64 exit-132 at Vulkan guest-thunk load is explained by the incomplete amd64 CI rootfs prerequisite, specifically the guest X11 symbols Vulkan `OnInit()` resolves. It is not evidence about Finding A's dynamic callback route because the affected runs never reached the callback probe.

The hosted lane is now unblocked for the intended callback A/B: keep the guest X11 fixture, then compare pristine dynamic `vkCreateDebugReportCallbackEXT` lookup with the local diagnostic custom-lookup route. The same repaired lane can subsequently execute the debug-utils and `vkCreateInstance` pNext probes.
