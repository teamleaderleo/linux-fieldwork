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
  (void)severity; (void)types; (void)data; (void)user;
  ++utils_count;
  fprintf(stderr, "UNEXPECTED_UTILS_CALLBACK count=%u\n", utils_count);
  fflush(stderr);
  return VK_FALSE;
}

VKAPI_ATTR VkBool32 VKAPI_CALL report_cb(
    VkDebugReportFlagsEXT flags, VkDebugReportObjectTypeEXT object_type,
    uint64_t object, size_t location, int32_t code,
    const char *layer_prefix, const char *message, void *user) {
  (void)flags; (void)object_type; (void)object; (void)location; (void)code;
  (void)layer_prefix; (void)message; (void)user;
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
  if (fn(&count, props) != VK_SUCCESS) { free(props); return 0; }
  int found = 0;
  for (uint32_t i = 0; i < count; ++i) if (!strcmp(props[i].layerName, wanted)) found = 1;
  free(props);
  return found;
}

static int has_extension(PFN_vkEnumerateInstanceExtensionProperties fn, const char *wanted) {
  uint32_t count = 0;
  if (fn(NULL, &count, NULL) != VK_SUCCESS) return 0;
  VkExtensionProperties *props = calloc(count ? count : 1, sizeof(*props));
  if (!props) return 0;
  if (fn(NULL, &count, props) != VK_SUCCESS) { free(props); return 0; }
  int found = 0;
  for (uint32_t i = 0; i < count; ++i) if (!strcmp(props[i].extensionName, wanted)) found = 1;
  free(props);
  return found;
}

int main(void) {
  void *vk = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vk) { fprintf(stderr, "DLOPEN=%s\n", dlerror()); return 10; }
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
      !has_extension(enumerate_extensions, VK_EXT_DEBUG_REPORT_EXTENSION_NAME)) return 12;

  VkDebugUtilsMessengerCreateInfoEXT utils = {
      .sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
      .messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_VERBOSE_BIT_EXT |
                         VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT |
                         VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                         VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT,
      .messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                     VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                     VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT,
      .pfnUserCallback = utils_cb,
      .pUserData = (void *)(uintptr_t)0x1122334455667788ULL,
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
      .pUserData = (void *)(uintptr_t)0x8877665544332211ULL,
  };
  VkApplicationInfo app = {
      .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
      .pApplicationName = "fex-pnext-full-integrity",
      .apiVersion = VK_API_VERSION_1_0,
  };
  const char *layers[] = {layer};
  const char *extensions[] = {VK_EXT_DEBUG_UTILS_EXTENSION_NAME, VK_EXT_DEBUG_REPORT_EXTENSION_NAME};
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
  PFN_vkDebugReportCallbackEXT original_report_callback = report.pfnCallback;
  PFN_vkDebugUtilsMessengerCallbackEXT original_utils_callback = utils.pfnUserCallback;
  void *original_report_user = report.pUserData;
  void *original_utils_user = utils.pUserData;

  fprintf(stderr,
          "FULL_BEFORE_CREATE ici=%p report_next=%p utils_next=%p report_cb=%p utils_cb=%p report_user=%p utils_user=%p\n",
          create_info.pNext, report.pNext, utils.pNext, (void *)report.pfnCallback, (void *)utils.pfnUserCallback,
          report.pUserData, utils.pUserData);
  fflush(stderr);

  VkInstance instance = VK_NULL_HANDLE;
  VkResult result = create_instance(&create_info, NULL, &instance);
  int pnext_same = create_info.pNext == original_create_pnext &&
                   report.pNext == original_report_pnext && utils.pNext == original_utils_pnext;
  int callbacks_same = report.pfnCallback == original_report_callback &&
                       utils.pfnUserCallback == original_utils_callback;
  int users_same = report.pUserData == original_report_user && utils.pUserData == original_utils_user;
  fprintf(stderr,
          "FULL_AFTER_CREATE result=%d instance=%p pnext_same=%d callbacks_same=%d users_same=%d callbacks=%u/%u\n",
          result, (void *)instance, pnext_same, callbacks_same, users_same, utils_count, report_count);
  fflush(stderr);

  if (result != VK_SUCCESS || instance == VK_NULL_HANDLE) return 20;
  if (utils_count || report_count) return 21;
  if (!pnext_same) return 40;
  if (!callbacks_same) return 42;
  if (!users_same) return 43;

  destroy_instance(instance, NULL);
  pnext_same = create_info.pNext == original_create_pnext &&
               report.pNext == original_report_pnext && utils.pNext == original_utils_pnext;
  callbacks_same = report.pfnCallback == original_report_callback &&
                   utils.pfnUserCallback == original_utils_callback;
  users_same = report.pUserData == original_report_user && utils.pUserData == original_utils_user;
  fprintf(stderr,
          "FULL_AFTER_DESTROY pnext_same=%d callbacks_same=%d users_same=%d callbacks=%u/%u\n",
          pnext_same, callbacks_same, users_same, utils_count, report_count);
  fflush(stderr);

  if (utils_count || report_count) return 22;
  if (!pnext_same) return 41;
  if (!callbacks_same) return 44;
  if (!users_same) return 45;
  if (dlclose(vk) != 0) return 23;
  fprintf(stderr, "FULL_RETURN unchanged=1 callbacks=0\n");
  fflush(stderr);
  return 0;
}
