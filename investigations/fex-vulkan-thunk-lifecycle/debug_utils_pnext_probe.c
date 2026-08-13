#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

#define VK_SUCCESS 0
#define VK_STRUCTURE_TYPE_APPLICATION_INFO 0
#define VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO 1
#define VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CALLBACK_DATA_EXT 1000128003
#define VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT 1000128004
#define VK_API_VERSION_1_0 (1u << 22)
#define VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT 0x00000100
#define VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT 0x00001000
#define VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT 0x00000001
#define VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT 0x00000002

typedef int32_t VkResult;
typedef uint32_t VkFlags;
typedef uint32_t VkBool32;
typedef uint32_t VkDebugUtilsMessageSeverityFlagBitsEXT;
typedef uint32_t VkDebugUtilsMessageSeverityFlagsEXT;
typedef uint32_t VkDebugUtilsMessageTypeFlagsEXT;
typedef struct VkInstance_T *VkInstance;

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

typedef VkResult (*PFN_vkCreateInstance)(const VkInstanceCreateInfo *, const void *, VkInstance *);

static volatile int callback_count;

static VkBool32 Callback(VkDebugUtilsMessageSeverityFlagBitsEXT severity, VkDebugUtilsMessageTypeFlagsEXT types,
                         const VkDebugUtilsMessengerCallbackDataEXT *data, void *user) {
  (void)user;
  ++callback_count;
  fprintf(stderr, "PNEXT_CALLBACK count=%d severity=0x%x types=0x%x id=%s message=%s\n", callback_count, severity, types,
          data && data->pMessageIdName ? data->pMessageIdName : "(null)", data && data->pMessage ? data->pMessage : "(null)");
  return 0;
}

int main(void) {
  void *vulkan = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vulkan) {
    fprintf(stderr, "DLERROR %s\n", dlerror());
    return 2;
  }

  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(vulkan, "vkCreateInstance");
  if (!create_instance) {
    fprintf(stderr, "MISSING vkCreateInstance\n");
    return 3;
  }

  const char *layers[] = {"VK_LAYER_KHRONOS_validation"};
  const char *extensions[] = {"VK_EXT_debug_utils"};
  VkDebugUtilsMessengerCreateInfoEXT debug_info = {
    VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
    NULL,
    1, /* Deliberately invalid: flags is reserved and must be zero. */
    VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT,
    VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT,
    Callback,
    NULL,
  };
  VkApplicationInfo app = {
    VK_STRUCTURE_TYPE_APPLICATION_INFO, NULL, "fex-debug-utils-pnext-probe", 1, "none", 1, VK_API_VERSION_1_0,
  };
  VkInstanceCreateInfo instance_info = {
    VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, &debug_info, 0, &app, 1, layers, 1, extensions,
  };

  VkInstance instance = NULL;
  VkResult result = create_instance(&instance_info, NULL, &instance);
  fprintf(stderr, "PNEXT_CREATE result=%d instance=%p callback_count=%d\n", result, (void *)instance, callback_count);
  fflush(NULL);

  /* The validation-layer control must actually exercise the pNext callback. */
  _exit(callback_count > 0 ? 0 : 20);
}
