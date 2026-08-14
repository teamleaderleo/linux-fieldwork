#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>

static VKAPI_ATTR VkBool32 VKAPI_CALL report_cb(
    VkDebugReportFlagsEXT flags, VkDebugReportObjectTypeEXT object_type,
    uint64_t object, size_t location, int32_t message_code,
    const char *layer_prefix, const char *message, void *user_data) {
  (void)flags; (void)object_type; (void)object; (void)location;
  (void)message_code; (void)layer_prefix; (void)message; (void)user_data;
  return VK_FALSE;
}

static VKAPI_ATTR VkBool32 VKAPI_CALL utils_cb(
    VkDebugUtilsMessageSeverityFlagBitsEXT severity,
    VkDebugUtilsMessageTypeFlagsEXT types,
    const VkDebugUtilsMessengerCallbackDataEXT *data, void *user_data) {
  (void)severity; (void)types; (void)data; (void)user_data;
  return VK_FALSE;
}

static void *alloc_page(size_t page_size) {
  void *p = mmap(NULL, page_size, PROT_READ | PROT_WRITE,
                 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (p == MAP_FAILED) {
    perror("mmap");
    return NULL;
  }
  return p;
}

static int protect_page(void *p, size_t page_size) {
  if (mprotect(p, page_size, PROT_READ) != 0) {
    perror("mprotect");
    return 0;
  }
  return 1;
}

int main(void) {
  void *vk = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vk) {
    fprintf(stderr, "SKIP dlopen: %s\n", dlerror());
    return 77;
  }
  PFN_vkCreateInstance create_instance =
      (PFN_vkCreateInstance)dlsym(vk, "vkCreateInstance");
  PFN_vkDestroyInstance destroy_instance =
      (PFN_vkDestroyInstance)dlsym(vk, "vkDestroyInstance");
  if (!create_instance || !destroy_instance) return 77;

  long page_size_long = sysconf(_SC_PAGESIZE);
  if (page_size_long <= 0) return 70;
  size_t page_size = (size_t)page_size_long;

  VkInstanceCreateInfo *info = alloc_page(page_size);
  VkDebugReportCallbackCreateInfoEXT *report = alloc_page(page_size);
  VkDebugUtilsMessengerCreateInfoEXT *utils = alloc_page(page_size);
  if (!info || !report || !utils) return 71;

  *utils = (VkDebugUtilsMessengerCreateInfoEXT) {
    .sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
    .pNext = NULL,
    .messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT,
    .messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT,
    .pfnUserCallback = utils_cb,
    .pUserData = (void *)(uintptr_t)0x1234567812345678ULL,
  };
  *report = (VkDebugReportCallbackCreateInfoEXT) {
    .sType = VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT,
    .pNext = utils,
    .flags = VK_DEBUG_REPORT_ERROR_BIT_EXT | VK_DEBUG_REPORT_WARNING_BIT_EXT,
    .pfnCallback = report_cb,
    .pUserData = (void *)(uintptr_t)0x8765432187654321ULL,
  };

  VkApplicationInfo app = {
    .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
    .pApplicationName = "fex-readonly-full-callback-chain",
    .apiVersion = VK_API_VERSION_1_0,
  };
  const char *extensions[] = {
    VK_EXT_DEBUG_REPORT_EXTENSION_NAME,
    VK_EXT_DEBUG_UTILS_EXTENSION_NAME,
    "VK_FEX_intentionally_missing_extension",
  };
  *info = (VkInstanceCreateInfo) {
    .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    .pNext = report,
    .pApplicationInfo = &app,
    .enabledExtensionCount = 3,
    .ppEnabledExtensionNames = extensions,
  };

  const void *orig_info_next = info->pNext;
  const void *orig_report_next = report->pNext;
  const void *orig_utils_next = utils->pNext;
  PFN_vkDebugReportCallbackEXT orig_report_cb = report->pfnCallback;
  PFN_vkDebugUtilsMessengerCallbackEXT orig_utils_cb = utils->pfnUserCallback;
  void *orig_report_user = report->pUserData;
  void *orig_utils_user = utils->pUserData;

  if (!protect_page(info, page_size) || !protect_page(report, page_size) ||
      !protect_page(utils, page_size)) return 72;

  fprintf(stderr,
          "RO_FULL before info=%p report=%p utils=%p report_cb=%p utils_cb=%p\n",
          (void *)info, (void *)report, (void *)utils,
          (void *)report->pfnCallback, (void *)utils->pfnUserCallback);
  fprintf(stderr, "RO_FULL create-enter\n");
  fflush(stderr);

  VkInstance instance = VK_NULL_HANDLE;
  VkResult result = create_instance(info, NULL, &instance);

  int pnext_same = info->pNext == orig_info_next &&
                   report->pNext == orig_report_next && utils->pNext == orig_utils_next;
  int callbacks_same = report->pfnCallback == orig_report_cb &&
                       utils->pfnUserCallback == orig_utils_cb;
  int users_same = report->pUserData == orig_report_user &&
                   utils->pUserData == orig_utils_user;
  fprintf(stderr,
          "RO_FULL create-return result=%d instance=%p pnext_same=%d callbacks_same=%d users_same=%d\n",
          result, (void *)instance, pnext_same, callbacks_same, users_same);
  fflush(stderr);

  if (instance != VK_NULL_HANDLE) destroy_instance(instance, NULL);
  if (!pnext_same) return 20;
  if (!callbacks_same) return 21;
  if (!users_same) return 22;

  fprintf(stderr, "RO_FULL return unchanged=1\n");
  fflush(stderr);
  return 0;
}
