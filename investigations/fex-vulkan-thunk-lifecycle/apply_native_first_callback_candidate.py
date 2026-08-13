#!/usr/bin/env python3
"""Apply an internal FEX Vulkan callback-routing experiment.

This is investigation machinery only. It adds the three missing callback-family
custom routes and changes proc-address handling so native Vulkan decides whether
a queried command is available before FEX substitutes a custom implementation.
"""

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source match, found {count}")
    return text.replace(old, new, 1)


def apply(host: Path) -> None:
    text = host.read_text()

    lookup_anchor = '''  } else if (a_1 == "vkAcquireXlibDisplayEXT"sv) {
    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkAcquireXlibDisplayEXT;
'''
    lookup_replacement = '''  } else if (a_1 == "vkCreateDebugReportCallbackEXT"sv) {
    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkCreateDebugReportCallbackEXT;
  } else if (a_1 == "vkDestroyDebugReportCallbackEXT"sv) {
    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkDestroyDebugReportCallbackEXT;
  } else if (a_1 == "vkCreateDebugUtilsMessengerEXT"sv) {
    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkCreateDebugUtilsMessengerEXT;
  } else if (a_1 == "vkAcquireXlibDisplayEXT"sv) {
    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkAcquireXlibDisplayEXT;
'''
    text = replace_once(text, lookup_anchor, lookup_replacement, "lookup callback entries")

    old_gdpa = '''static PFN_vkVoidFunction FEXFN_IMPL(vkGetDeviceProcAddr)(VkDevice a_0, const char* a_1) {
  // Just return the host facing function pointer
  // The guest will handle mapping if this exists

  // Check for functions with custom implementations first
  if (auto ptr = LookupCustomVulkanFunction(a_1)) {
    return ptr;
  }

  return LDR_PTR(vkGetDeviceProcAddr)(a_0, a_1);
}
'''
    new_gdpa = '''static PFN_vkVoidFunction FEXFN_IMPL(vkGetDeviceProcAddr)(VkDevice a_0, const char* a_1) {
  // Let native Vulkan decide whether the command is available for this device.
  auto native_ptr = LDR_PTR(vkGetDeviceProcAddr)(a_0, a_1);
  if (!native_ptr) {
    return nullptr;
  }

  // Preserve native availability while substituting FEX policy when required.
  if (auto ptr = LookupCustomVulkanFunction(a_1)) {
    return ptr;
  }

  return native_ptr;
}
'''
    text = replace_once(text, old_gdpa, new_gdpa, "vkGetDeviceProcAddr")

    old_gipa_head = '''  // Check for functions with custom implementations first
  if (auto ptr = LookupCustomVulkanFunction(a_1)) {
'''
    new_gipa_head = '''  // Let native Vulkan decide whether the command is available for this instance/name.
  auto native_ptr = LDR_PTR(vkGetInstanceProcAddr)(a_0, a_1);
  if (!native_ptr) {
    return nullptr;
  }

  // Preserve native availability while substituting FEX policy when required.
  if (auto ptr = LookupCustomVulkanFunction(a_1)) {
'''
    # The same phrase used to exist in GDPA too, but GDPA has already been replaced.
    text = replace_once(text, old_gipa_head, new_gipa_head, "vkGetInstanceProcAddr head")

    old_gipa_tail = '''  return LDR_PTR(vkGetInstanceProcAddr)(a_0, a_1);
}

#ifdef IS_32BIT_THUNK
'''
    new_gipa_tail = '''  return native_ptr;
}

#ifdef IS_32BIT_THUNK
'''
    text = replace_once(text, old_gipa_tail, new_gipa_tail, "vkGetInstanceProcAddr tail")

    host.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host", type=Path)
    args = parser.parse_args()
    apply(args.host)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
