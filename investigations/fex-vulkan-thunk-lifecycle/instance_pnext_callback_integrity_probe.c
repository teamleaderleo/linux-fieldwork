#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>

static volatile uint32_t utils_count;
static volatile uint32_t report_count;

VKAPI_ATTR VkBool32 VKAPI_CALL utils_cb(
    VkDebugUtilsMessageSeverityFlagBitsEXT severity,
    VkDebugUtilsMessageTypeFlagsEXT types,
    const VkDebugUtilsMessengerCallbackDataEXT *data,
    void *user) {
  (void)severity;
  (void)types;
  (void)data;
  (void)user;
  ++utils_count;
  fprintf(stderr, "UNEXPECTED_UTILS_CALLBACK count=%u\n", utils_count);
  fflush(stderr);
  return VK_FALSE;
}

VKAPI_ATTR VkBool32 VKAPI_CALL report_cb(
    VkDebugReportFlagsEXT flags,
    VkDebugReportObjectTypeEXT object_type,
    uint64_t object,
    size_t location,
    int32_t code,
    const char *layer_prefix,
    const char *message,
    void *user) {
  (void)flags;
  (void)object_type;
  (void)object;
  (void)location;
  (void)code;
  (void)layer_prefix;
  (void)message;
  (void)user;
  ++report_count;
  fprintf(stderr, "UNEXPECTED_REPORT_CALLBACK count=%u\n", report_count);
  fflush(stderr);
  return VK_FALSE;
}

static int has_layer(PFN_vkEnumerateInstanceLayerProperties fn, const char *wanted) {
  uint32_t count = 0;
  if (fn(&count, NULL) != VK_SUCCESS) return 0;
  VkLayerProperties *props = calloc(count ? count : 1, sizeof(*props));
  if (!props) return 0;
  if (fn(&count, props) != VK_SUCCESS) {
    free(props);
    return 0;
  }
  int found = 0;
  for (uint32_t i = 0; i < count; ++i) {
    if (!strcmp(props[i].layerName, wanted)) found = 1;
  }
  free(props);
  return found;
}

static int has_extension(PFN_vkEnumerateInstanceExtensionProperties fn, const char *wanted) {
  uint32_t count = 0;
  if (fn(NULL, &count, NULL) != VK_SUCCESS) return 0;
  VkExtensionProperties *props = calloc(count ? count : 1, sizeof(*props));
  if (!props) return 0;
  if (fn(NULL, &count, props) != VK_SUCCESS) {
    free(props);
    return 0;
  }
  int found = 0;
  for (uint32_t i = 0; i < count; ++i) {
    if (!strcmp(props[i].extensionName, wanted)) found = 1;
  }
  free(props);
  return found;
}

int main(void) {
  void *vk = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vk) {
    fprintf(stderr, "DLOPEN=%s\n", dlerror());
    return 10;
  }

  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(vk, "vkCreateInstance");
  PFN_vkDestroyInstance destroy_instance = (PFN_vkDestroyInstance)dlsym(vk, "vkDestroyInstance");
  PFN_vkEnumerateInstanceLayerProperties enumerate_layers =
      (PFN_vkEnumerateInstanceLayerProperties)dlsym(vk, "vkEnumerateInstanceLayerProperties");
  PFN_vkEnumerateInstanceExtensionProperties enumerate_extensions =
      (PFN_vkEnumerateInstanceExtensionProperties)dlsym(vk, "vkEnumerateInstanceExtensionProperties");
  if (!create_instance || !destroy_instance || !enumerate_layers || !enumerate_extensions) return 11;

  const char *layer = "VK_LAYER_KHRONOS_validation";
  if (!has_layer(enumerate_layers, layer) ||
      !has_extension(enumerate_extensions, VK_EXT_DEBUG_UTILS_EXTENSION_NAME) ||
      !has_extension(enumerate_extensions, VK_EXT_DEBUG_REPORT_EXTENSION_NAME)) {
    return 12;
  }

  VkDebugUtilsMessengerCreateInfoEXT utils = {
      .sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
      .pNext = NULL,
      .messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_VERBOSE_BIT_EXT |
                         VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT |
                         VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                         VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT,
      .messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                     VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                     VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT,
      .pfnUserCallback = utils_cb,
  };
  VkDebugReportCallbackCreateInfoEXT report = {
      .sType = VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT,
      .pNext = &utils,
      .flags = VK_DEBUG_REPORT_INFORMATION_BIT_EXT |
               VK_DEBUG_REPORT_WARNING_BIT_EXT |
               VK_DEBUG_REPORT_PERFORMANCE_WARNING_BIT_EXT |
               VK_DEBUG_REPORT_ERROR_BIT_EXT |
               VK_DEBUG_REPORT_DEBUG_BIT_EXT,
      .pfnCallback = report_cb,
  };
  VkApplicationInfo app = {
      .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
      .pApplicationName = "fex-pnext-restoration",
      .apiVersion = VK_API_VERSION_1_0,
  };
  const char *layers[] = {layer};
  const char *extensions[] = {
      VK_EXT_DEBUG_UTILS_EXTENSION_NAME,
      VK_EXT_DEBUG_REPORT_EXTENSION_NAME,
  };
  VkInstanceCreateInfo create_info = {
      .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
      .pNext = &report,
      .flags = (VkInstanceCreateFlags)0x80000000u,
      .pApplicationInfo = &app,
      .enabledLayerCount = 1,
      .ppEnabledLayerNames = layers,
      .enabledExtensionCount = 2,
      .ppEnabledExtensionNames = extensions,
  };

  const void *original_create_pnext = create_info.pNext;
  const void *original_report_pnext = report.pNext;
  const void *original_utils_pnext = utils.pNext;

  fprintf(stderr, "RESTORE_BEFORE_CREATE ici=%p report=%p utils=%p\n",
          create_info.pNext, report.pNext, utils.pNext);
  fflush(stderr);

  VkInstance instance = VK_NULL_HANDLE;
  VkResult result = create_instance(&create_info, NULL, &instance);
  int create_same = create_info.pNext == original_create_pnext;
  int report_same = report.pNext == original_report_pnext;
  int utils_same = utils.pNext == original_utils_pnext;
  fprintf(stderr,
          "RESTORE_AFTER_CREATE result=%d instance=%p ici_same=%d report_same=%d utils_same=%d callbacks=%u/%u\n",
          result, (void *)instance, create_same, report_same, utils_same,
          utils_count, report_count);
  fflush(stderr);

  if (result != VK_SUCCESS || instance == VK_NULL_HANDLE) return 20;
  if (utils_count || report_count) return 21;
  if (!create_same || !report_same || !utils_same) return 40;

  destroy_instance(instance, NULL);
  create_same = create_info.pNext == original_create_pnext;
  report_same = report.pNext == original_report_pnext;
  utils_same = utils.pNext == original_utils_pnext;
  fprintf(stderr,
          "RESTORE_AFTER_DESTROY ici_same=%d report_same=%d utils_same=%d callbacks=%u/%u\n",
          create_same, report_same, utils_same, utils_count, report_count);
  fflush(stderr);

  if (utils_count || report_count) return 22;
  if (!create_same || !report_same || !utils_same) return 41;
  if (dlclose(vk) != 0) return 23;

  fprintf(stderr, "RESTORE_RETURN unchanged=1 callbacks=0\n");
  fflush(stderr);
  return 0;
}
