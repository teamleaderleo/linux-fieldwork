#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>
#include <vulkan/vulkan.h>

static volatile int report_callback_count;
static volatile int utils_callback_count;

static VKAPI_ATTR VkBool32 VKAPI_CALL ReportCallback(VkDebugReportFlagsEXT flags, VkDebugReportObjectTypeEXT object_type,
                                                      uint64_t object, size_t location, int32_t message_code,
                                                      const char *layer_prefix, const char *message, void *user_data) {
  (void)flags;
  (void)object_type;
  (void)object;
  (void)location;
  (void)message_code;
  (void)layer_prefix;
  (void)message;
  (void)user_data;
  ++report_callback_count;
  return VK_FALSE;
}

static VKAPI_ATTR VkBool32 VKAPI_CALL UtilsCallback(VkDebugUtilsMessageSeverityFlagBitsEXT severity,
                                                     VkDebugUtilsMessageTypeFlagsEXT types,
                                                     const VkDebugUtilsMessengerCallbackDataEXT *data,
                                                     void *user_data) {
  (void)severity;
  (void)types;
  (void)data;
  (void)user_data;
  ++utils_callback_count;
  return VK_FALSE;
}

int main(void) {
  void *vulkan = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vulkan) return 2;

  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(vulkan, "vkCreateInstance");
  if (!create_instance) return 3;

  const char *layers[] = {"VK_LAYER_KHRONOS_validation"};
  const char *extensions[] = {VK_EXT_DEBUG_REPORT_EXTENSION_NAME, VK_EXT_DEBUG_UTILS_EXTENSION_NAME};

  VkDebugUtilsMessengerCreateInfoEXT utils_info = {
    .sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
    .pNext = NULL,
    .flags = 1, /* Deliberately invalid so validation exercises this record. */
    .messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT,
    .messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT,
    .pfnUserCallback = UtilsCallback,
    .pUserData = NULL,
  };

  VkDebugReportCallbackCreateInfoEXT report_info = {
    .sType = VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT,
    .pNext = &utils_info,
    .flags = VK_DEBUG_REPORT_WARNING_BIT_EXT | VK_DEBUG_REPORT_ERROR_BIT_EXT,
    .pfnCallback = ReportCallback,
    .pUserData = NULL,
  };

  VkApplicationInfo app = {
    .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
    .pApplicationName = "fex-adjacent-pnext-callback-probe",
    .applicationVersion = 1,
    .pEngineName = "none",
    .engineVersion = 1,
    .apiVersion = VK_API_VERSION_1_0,
  };

  VkInstanceCreateInfo instance_info = {
    .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    .pNext = &report_info,
    .pApplicationInfo = &app,
    .enabledLayerCount = 1,
    .ppEnabledLayerNames = layers,
    .enabledExtensionCount = 2,
    .ppEnabledExtensionNames = extensions,
  };

  VkInstance instance = VK_NULL_HANDLE;
  VkResult result = create_instance(&instance_info, NULL, &instance);
  fprintf(stderr, "PNEXT_ADJACENT_CREATE result=%d instance=%p report_count=%d utils_count=%d\n",
          result, (void *)instance, report_callback_count, utils_callback_count);
  fflush(NULL);

  _exit(result == VK_SUCCESS && instance != VK_NULL_HANDLE && report_callback_count == 0 && utils_callback_count == 0 ? 0 : 20);
}
