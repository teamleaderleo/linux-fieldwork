#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} FEX_SOURCE_ROOT")

root = Path(sys.argv[1])
p = root / "ThunkLibs/libvulkan/Host.cpp"
s = p.read_text()

start = s.index("static VkResult FEXFN_IMPL(vkCreateInstance)")
end = s.index("\n\nstatic VkResult FEXFN_IMPL(vkCreateDevice)", start)

new = r'''extern "C" VkBool32 DummyVkDebugUtilsMessengerCallback(VkDebugUtilsMessageSeverityFlagBitsEXT, VkDebugUtilsMessageTypeFlagsEXT,
                                                       const VkDebugUtilsMessengerCallbackDataEXT*, void*);

static VkResult FEXFN_IMPL(vkCreateInstance)(const VkInstanceCreateInfo* a_0, const VkAllocationCallbacks* a_1, guest_layout<VkInstance*> a_2) {
  struct DebugReportRestore {
    VkDebugReportCallbackCreateInfoEXT* CreateInfo;
    PFN_vkDebugReportCallbackEXT Callback;
  };
  struct DebugUtilsRestore {
    VkDebugUtilsMessengerCreateInfoEXT* CreateInfo;
    PFN_vkDebugUtilsMessengerCallbackEXT Callback;
  };

  std::vector<DebugReportRestore> report_restore;
  std::vector<DebugUtilsRestore> utils_restore;

  for (const VkBaseInStructure* vk_struct = reinterpret_cast<const VkBaseInStructure*>(a_0->pNext); vk_struct;
       vk_struct = vk_struct->pNext) {
    if (vk_struct->sType == VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT) {
      auto* create_info = const_cast<VkDebugReportCallbackCreateInfoEXT*>(
        reinterpret_cast<const VkDebugReportCallbackCreateInfoEXT*>(vk_struct));
      report_restore.push_back({create_info, create_info->pfnCallback});
      create_info->pfnCallback = DummyVkDebugReportCallback;
    } else if (vk_struct->sType == VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT) {
      auto* create_info = const_cast<VkDebugUtilsMessengerCreateInfoEXT*>(
        reinterpret_cast<const VkDebugUtilsMessengerCreateInfoEXT*>(vk_struct));
      utils_restore.push_back({create_info, create_info->pfnUserCallback});
      create_info->pfnUserCallback = DummyVkDebugUtilsMessengerCallback;
    }
  }

  VkInstance out;
  auto ret = LDR_PTR(vkCreateInstance)(a_0, nullptr, &out);

  for (auto it = utils_restore.rbegin(); it != utils_restore.rend(); ++it) {
    it->CreateInfo->pfnUserCallback = it->Callback;
  }
  for (auto it = report_restore.rbegin(); it != report_restore.rend(); ++it) {
    it->CreateInfo->pfnCallback = it->Callback;
  }

  *a_2.get_pointer() = to_guest(to_host_layout(out));
  return ret;
}'''

p.write_text(s[:start] + new + s[end:])
