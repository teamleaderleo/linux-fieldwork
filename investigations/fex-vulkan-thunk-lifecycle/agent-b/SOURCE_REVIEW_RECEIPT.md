# FEX Vulkan callback source review receipt

Date: 2026-08-14

This receipt records the source-level adjacent check performed while reducing Finding A. GitHub access to FEX was read-only. No issue, pull request, comment, review, reaction, email, branch write, or other upstream interaction occurred.

## Revisions

- Executed investigation target: FEX `FEX-2608`, commit `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
  - `https://redirect.github.com/FEX-Emu/FEX/commit/e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- FEX `main` checked again on 2026-08-14: `71afe476751deac24adabd1adb575fd2337b6e0a`
  - `https://redirect.github.com/FEX-Emu/FEX/commit/71afe476751deac24adabd1adb575fd2337b6e0a`
- Source file in both checks: `ThunkLibs/libvulkan/Host.cpp`
- Historical callback workaround context retained by the parent investigation:
  - `https://redirect.github.com/FEX-Emu/FEX/pull/1803`

## `VK_EXT_debug_report`

`Host.cpp` defines `DummyVkDebugReportCallback` and a custom `FEXFN_IMPL(vkCreateDebugReportCallbackEXT)`. The custom create implementation copies the guest create info, replaces `pfnCallback` with the native dummy callback, queries the native create function, and calls it.

`LookupCustomVulkanFunction()` omits `vkCreateDebugReportCallbackEXT`. `FEXFN_IMPL(vkGetInstanceProcAddr)` checks `LookupCustomVulkanFunction()` first and falls back to the native loader address when the custom lookup returns no entry.

This is the source owner already selected by the retained runtime A/B: pristine dynamic lookup reaches the unsafe route and SIGILLs; selecting the existing custom create implementation removes that SIGILL.

## `VK_EXT_debug_utils`

The adjacent source is strikingly parallel. `Host.cpp` also defines:

```cpp
extern "C" VkBool32 DummyVkDebugUtilsMessengerCallback(...)
```

and a custom:

```cpp
FEXFN_IMPL(vkCreateDebugUtilsMessengerEXT)(...)
```

The custom debug-utils create implementation copies `VkDebugUtilsMessengerCreateInfoEXT`, replaces `pfnUserCallback` with `DummyVkDebugUtilsMessengerCallback`, queries native `vkCreateDebugUtilsMessengerEXT`, and calls it.

`LookupCustomVulkanFunction()` also omits `vkCreateDebugUtilsMessengerEXT`. Whole-file function-name checks at both revisions find the debug-utils create name only in the custom implementation/native lookup sequence, with no custom-lookup branch.

## Conclusion

`VK_EXT_debug_utils` shares Finding A's source-level defect class at both reviewed FEX revisions:

```text
callback-creating extension function has an existing callback-suppressing custom host implementation
+
dynamic vkGetInstanceProcAddr path consults LookupCustomVulkanFunction
+
LookupCustomVulkanFunction omits that function
=
dynamic lookup can bypass the callback-aware custom implementation
```

The reduced `vk_debug_utils_repro.c` provides the runtime discriminator. On pristine affected routing, a matching `vkSubmitDebugUtilsMessageEXT` should expose raw native ARM entry to the x86 callback and hit the deliberate SIGILL callback prefix. A local lookup candidate selecting FEX's existing debug-utils wrapper should return from submit with zero guest callback entries under `--expect=suppressed`.

## Evidence limit

The source-level shared defect class is confirmed. This agent's execution host is x86-64 and has no FEX runtime, so the debug-utils FEX runtime consequence remains unexecuted here. Native software Vulkan execution confirms the probe itself: matching submit produces exactly one guest callback, while no-submit and filter-miss controls produce zero.
