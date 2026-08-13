#define main original_pnext_probe_main
#include "debug_utils_pnext_probe.c"
#undef main

int main(void) {
  callback_count = 0;

  void *vulkan = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vulkan) return 2;
  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(vulkan, "vkCreateInstance");
  if (!create_instance) return 3;

  const char *layers[] = {"VK_LAYER_KHRONOS_validation"};
  const char *extensions[] = {"VK_EXT_debug_utils"};
  VkDebugUtilsMessengerCreateInfoEXT debug_info = {
    VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
    NULL,
    1,
    VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT,
    VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT,
    Callback,
    NULL,
  };
  VkApplicationInfo app = {
    VK_STRUCTURE_TYPE_APPLICATION_INFO, NULL, "fex-debug-utils-pnext-zero-probe", 1, "none", 1, VK_API_VERSION_1_0,
  };
  VkInstanceCreateInfo instance_info = {
    VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, &debug_info, 0, &app, 1, layers, 1, extensions,
  };

  VkInstance instance = NULL;
  VkResult result = create_instance(&instance_info, NULL, &instance);
  fprintf(stderr, "PNEXT_ZERO_CREATE result=%d instance=%p callback_count=%d\n", result, (void *)instance, callback_count);
  fflush(NULL);
  _exit(callback_count == 0 ? 0 : 20);
}
