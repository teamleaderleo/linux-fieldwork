#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

#define VK_SUCCESS 0
#define VK_STRUCTURE_TYPE_APPLICATION_INFO 0
#define VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO 1
#define VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT 1000011000
#define VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CALLBACK_DATA_EXT 1000128003
#define VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT 1000128004
#define VK_API_VERSION_1_0 (1u << 22)
#define VK_DEBUG_REPORT_WARNING_BIT_EXT 0x00000002
#define VK_DEBUG_REPORT_OBJECT_TYPE_UNKNOWN_EXT 0
#define VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT 0x00000100
#define VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT 0x00000001

typedef int32_t VkResult;
typedef uint32_t VkFlags;
typedef uint32_t VkBool32;
typedef uint32_t VkDebugReportFlagsEXT;
typedef int32_t VkDebugReportObjectTypeEXT;
typedef uint32_t VkDebugUtilsMessageSeverityFlagBitsEXT;
typedef uint32_t VkDebugUtilsMessageSeverityFlagsEXT;
typedef uint32_t VkDebugUtilsMessageTypeFlagsEXT;
typedef struct VkInstance_T *VkInstance;
typedef uint64_t VkDebugReportCallbackEXT;
typedef uint64_t VkDebugUtilsMessengerEXT;
typedef void (*PFN_vkVoidFunction)(void);

typedef struct VkApplicationInfo {
  int32_t sType;
  const void *pNext;
  const char *pApplicationName;
  uint32_t applicationVersion;
  const char *pEngineName;
  uint32_t engineVersion;
  uint32_t apiVersion;
} VkApplicationInfo;

typedef struct VkInstanceCreateInfo {
  int32_t sType;
  const void *pNext;
  VkFlags flags;
  const VkApplicationInfo *pApplicationInfo;
  uint32_t enabledLayerCount;
  const char *const *ppEnabledLayerNames;
  uint32_t enabledExtensionCount;
  const char *const *ppEnabledExtensionNames;
} VkInstanceCreateInfo;

typedef VkBool32 (*PFN_vkDebugReportCallbackEXT)(VkDebugReportFlagsEXT, VkDebugReportObjectTypeEXT, uint64_t, size_t,
                                                  int32_t, const char *, const char *, void *);
typedef struct VkDebugReportCallbackCreateInfoEXT {
  int32_t sType;
  const void *pNext;
  VkDebugReportFlagsEXT flags;
  PFN_vkDebugReportCallbackEXT pfnCallback;
  void *pUserData;
} VkDebugReportCallbackCreateInfoEXT;

typedef struct VkDebugUtilsMessengerCallbackDataEXT {
  int32_t sType;
  const void *pNext;
  VkFlags flags;
  const char *pMessageIdName;
  int32_t messageIdNumber;
  const char *pMessage;
  uint32_t queueLabelCount;
  const void *pQueueLabels;
  uint32_t cmdBufLabelCount;
  const void *pCmdBufLabels;
  uint32_t objectCount;
  const void *pObjects;
} VkDebugUtilsMessengerCallbackDataEXT;

typedef VkBool32 (*PFN_vkDebugUtilsMessengerCallbackEXT)(VkDebugUtilsMessageSeverityFlagBitsEXT,
                                                          VkDebugUtilsMessageTypeFlagsEXT,
                                                          const VkDebugUtilsMessengerCallbackDataEXT *, void *);
typedef struct VkDebugUtilsMessengerCreateInfoEXT {
  int32_t sType;
  const void *pNext;
  VkFlags flags;
  VkDebugUtilsMessageSeverityFlagsEXT messageSeverity;
  VkDebugUtilsMessageTypeFlagsEXT messageType;
  PFN_vkDebugUtilsMessengerCallbackEXT pfnUserCallback;
  void *pUserData;
} VkDebugUtilsMessengerCreateInfoEXT;

typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(VkInstance, const char *);
typedef VkResult (*PFN_vkCreateInstance)(const VkInstanceCreateInfo *, const void *, VkInstance *);
typedef VkResult (*PFN_vkCreateDebugReportCallbackEXT)(VkInstance, const VkDebugReportCallbackCreateInfoEXT *, const void *,
                                                        VkDebugReportCallbackEXT *);
typedef void (*PFN_vkDebugReportMessageEXT)(VkInstance, VkDebugReportFlagsEXT, VkDebugReportObjectTypeEXT, uint64_t, size_t,
                                             int32_t, const char *, const char *);
typedef VkResult (*PFN_vkCreateDebugUtilsMessengerEXT)(VkInstance, const VkDebugUtilsMessengerCreateInfoEXT *, const void *,
                                                        VkDebugUtilsMessengerEXT *);
typedef void (*PFN_vkSubmitDebugUtilsMessageEXT)(VkInstance, VkDebugUtilsMessageSeverityFlagBitsEXT,
                                                  VkDebugUtilsMessageTypeFlagsEXT,
                                                  const VkDebugUtilsMessengerCallbackDataEXT *);

static volatile int callback_count;

static VkBool32 ReportCallback(VkDebugReportFlagsEXT flags, VkDebugReportObjectTypeEXT object_type, uint64_t object,
                               size_t location, int32_t code, const char *prefix, const char *message, void *user) {
  (void)object_type; (void)object; (void)location; (void)code; (void)user;
  ++callback_count;
  fprintf(stderr, "PROBE_CALLBACK kind=report count=%d flags=0x%x prefix=%s message=%s\n", callback_count, flags,
          prefix ? prefix : "(null)", message ? message : "(null)");
  return 0;
}

static VkBool32 UtilsCallback(VkDebugUtilsMessageSeverityFlagBitsEXT severity, VkDebugUtilsMessageTypeFlagsEXT types,
                              const VkDebugUtilsMessengerCallbackDataEXT *data, void *user) {
  (void)user;
  ++callback_count;
  fprintf(stderr, "PROBE_CALLBACK kind=utils count=%d severity=0x%x types=0x%x id=%s message=%s\n", callback_count,
          severity, types, data && data->pMessageIdName ? data->pMessageIdName : "(null)",
          data && data->pMessage ? data->pMessage : "(null)");
  return 0;
}

static void Finish(int status) {
  fprintf(stderr, "PROBE_FINISH callback_count=%d status=%d\n", callback_count, status);
  fflush(NULL);
  _exit(status);
}

int main(int argc, char **argv) {
  if (argc != 4 || (strcmp(argv[1], "report") && strcmp(argv[1], "utils")) ||
      (strcmp(argv[2], "gipa") && strcmp(argv[2], "direct"))) {
    fprintf(stderr, "usage: %s report|utils gipa|direct expected-count|positive\n", argv[0]);
    return 64;
  }

  const int is_report = strcmp(argv[1], "report") == 0;
  const int direct = strcmp(argv[2], "direct") == 0;
  const int expect_positive = strcmp(argv[3], "positive") == 0;
  const int expected = expect_positive ? -1 : atoi(argv[3]);
  void *vulkan = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vulkan) { fprintf(stderr, "DLERROR %s\n", dlerror()); return 2; }
  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(vulkan, "vkGetInstanceProcAddr");
  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(vulkan, "vkCreateInstance");
  if (!gipa || !create_instance) { fprintf(stderr, "MISSING core entrypoints\n"); return 3; }

  const char *extensions[] = {is_report ? "VK_EXT_debug_report" : "VK_EXT_debug_utils"};
  VkApplicationInfo app = {VK_STRUCTURE_TYPE_APPLICATION_INFO, NULL, "fex-vulkan-callback-probe", 1, "none", 1,
                           VK_API_VERSION_1_0};
  VkInstanceCreateInfo instance_info = {VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, NULL, 0, &app, 0, NULL, 1, extensions};
  VkInstance instance = NULL;
  VkResult result = create_instance(&instance_info, NULL, &instance);
  fprintf(stderr, "CREATE_INSTANCE kind=%s lookup=%s result=%d instance=%p\n", argv[1], argv[2], result, (void *)instance);
  if (result != VK_SUCCESS) return 10;

  if (is_report) {
    PFN_vkCreateDebugReportCallbackEXT create = direct
      ? (PFN_vkCreateDebugReportCallbackEXT)dlsym(vulkan, "vkCreateDebugReportCallbackEXT")
      : (PFN_vkCreateDebugReportCallbackEXT)gipa(instance, "vkCreateDebugReportCallbackEXT");
    PFN_vkDebugReportMessageEXT fire = (PFN_vkDebugReportMessageEXT)gipa(instance, "vkDebugReportMessageEXT");
    fprintf(stderr, "PROC create=%p fire=%p\n", (void *)create, (void *)fire);
    if (!create || !fire) return 11;
    VkDebugReportCallbackCreateInfoEXT callback_info = {VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT, NULL,
                                                         VK_DEBUG_REPORT_WARNING_BIT_EXT, ReportCallback, NULL};
    VkDebugReportCallbackEXT callback = 0;
    result = create(instance, &callback_info, NULL, &callback);
    fprintf(stderr, "CREATE_CALLBACK result=%d callback=0x%llx\n", result, (unsigned long long)callback);
    if (result != VK_SUCCESS) return 12;
    fire(instance, VK_DEBUG_REPORT_WARNING_BIT_EXT, VK_DEBUG_REPORT_OBJECT_TYPE_UNKNOWN_EXT, 0, 0, 4242, "fex-probe",
         "forced debug-report callback");
  } else {
    PFN_vkCreateDebugUtilsMessengerEXT create = direct
      ? (PFN_vkCreateDebugUtilsMessengerEXT)dlsym(vulkan, "vkCreateDebugUtilsMessengerEXT")
      : (PFN_vkCreateDebugUtilsMessengerEXT)gipa(instance, "vkCreateDebugUtilsMessengerEXT");
    PFN_vkSubmitDebugUtilsMessageEXT fire = (PFN_vkSubmitDebugUtilsMessageEXT)gipa(instance, "vkSubmitDebugUtilsMessageEXT");
    fprintf(stderr, "PROC create=%p fire=%p\n", (void *)create, (void *)fire);
    if (!create || !fire) return 11;
    VkDebugUtilsMessengerCreateInfoEXT callback_info = {
      VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT, NULL, 0, VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT,
      VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT, UtilsCallback, NULL};
    VkDebugUtilsMessengerEXT messenger = 0;
    result = create(instance, &callback_info, NULL, &messenger);
    fprintf(stderr, "CREATE_MESSENGER result=%d messenger=0x%llx\n", result, (unsigned long long)messenger);
    if (result != VK_SUCCESS) return 12;
    VkDebugUtilsMessengerCallbackDataEXT data = {.sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CALLBACK_DATA_EXT,
                                                  .pMessageIdName = "fex-probe",
                                                  .messageIdNumber = 4242,
                                                  .pMessage = "forced debug-utils callback"};
    fire(instance, VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT, VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT, &data);
  }

  fprintf(stderr, "AFTER_FIRE callback_count=%d expected=%s\n", callback_count, argv[3]);
  Finish(expect_positive ? (callback_count > 0 ? 0 : 20) : (callback_count == expected ? 0 : 20));
}
