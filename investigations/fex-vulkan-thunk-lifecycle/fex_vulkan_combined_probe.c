#define _GNU_SOURCE
#include <dlfcn.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define VK_SUCCESS 0
#define VK_FALSE 0
#define VK_STRUCTURE_TYPE_APPLICATION_INFO 0
#define VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO 1
#define VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT 1000011000u
#define VK_DEBUG_REPORT_WARNING_BIT_EXT 0x00000002u
#define VK_DEBUG_REPORT_ERROR_BIT_EXT 0x00000008u
#define VK_API_VERSION_1_0 (1u << 22)

typedef int32_t VkResult;
typedef uint32_t VkBool32;
typedef uint32_t VkDebugReportFlagsEXT;
typedef uint32_t VkDebugReportObjectTypeEXT;
typedef struct VkInstance_T *VkInstance;
typedef uint64_t VkDebugReportCallbackEXT;
typedef void (*PFN_vkVoidFunction)(void);

typedef struct VkApplicationInfo {
  uint32_t sType;
  const void *pNext;
  const char *pApplicationName;
  uint32_t applicationVersion;
  const char *pEngineName;
  uint32_t engineVersion;
  uint32_t apiVersion;
} VkApplicationInfo;

typedef struct VkInstanceCreateInfo {
  uint32_t sType;
  const void *pNext;
  uint32_t flags;
  const VkApplicationInfo *pApplicationInfo;
  uint32_t enabledLayerCount;
  const char *const *ppEnabledLayerNames;
  uint32_t enabledExtensionCount;
  const char *const *ppEnabledExtensionNames;
} VkInstanceCreateInfo;

typedef VkBool32 (*PFN_vkDebugReportCallbackEXT)(VkDebugReportFlagsEXT, VkDebugReportObjectTypeEXT, uint64_t, size_t,
                                                  int32_t, const char *, const char *, void *);

typedef struct VkDebugReportCallbackCreateInfoEXT {
  uint32_t sType;
  const void *pNext;
  VkDebugReportFlagsEXT flags;
  PFN_vkDebugReportCallbackEXT pfnCallback;
  void *pUserData;
} VkDebugReportCallbackCreateInfoEXT;

typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(VkInstance, const char *);
typedef VkResult (*PFN_vkCreateInstance)(const VkInstanceCreateInfo *, const void *, VkInstance *);
typedef void (*PFN_vkDestroyInstance)(VkInstance, const void *);
typedef VkResult (*PFN_vkEnumerateInstanceVersion)(uint32_t *);
typedef VkResult (*PFN_vkCreateDebugReportCallbackEXTFn)(VkInstance, const VkDebugReportCallbackCreateInfoEXT *, const void *,
                                                          VkDebugReportCallbackEXT *);
typedef void (*PFN_vkDestroyDebugReportCallbackEXTFn)(VkInstance, VkDebugReportCallbackEXT, const void *);

static int AddressMapped(const void *address) {
  FILE *maps = fopen("/proc/self/maps", "r");
  if (!maps) return 0;
  uintptr_t needle = (uintptr_t)address;
  char line[4096];
  while (fgets(line, sizeof(line), maps)) {
    unsigned long long lo = 0, hi = 0;
    if (sscanf(line, "%llx-%llx", &lo, &hi) == 2 && needle >= lo && needle < hi) {
      fclose(maps);
      return 1;
    }
  }
  fclose(maps);
  return 0;
}

static VkBool32 GuestDebugReportCallback(VkDebugReportFlagsEXT flags, VkDebugReportObjectTypeEXT object_type, uint64_t object,
                                         size_t location, int32_t code, const char *layer_prefix, const char *message, void *user) {
  (void)flags; (void)object_type; (void)object; (void)location; (void)code; (void)layer_prefix; (void)message; (void)user;
  fprintf(stderr, "COMBINED unexpected-guest-debug-callback\n");
  return VK_FALSE;
}

static void Require(int condition, const char *what) {
  if (!condition) {
    fprintf(stderr, "COMBINED FAIL %s\n", what);
    exit(90);
  }
}

int main(void) {
  setvbuf(stderr, NULL, _IONBF, 0);

  void *lib = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  Require(lib != NULL, "dlopen libvulkan");

  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(lib, "vkGetInstanceProcAddr");
  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(lib, "vkCreateInstance");
  PFN_vkDestroyInstance destroy_instance = (PFN_vkDestroyInstance)dlsym(lib, "vkDestroyInstance");
  PFN_vkEnumerateInstanceVersion enumerate_version = (PFN_vkEnumerateInstanceVersion)dlsym(lib, "vkEnumerateInstanceVersion");
  Require(gipa && create_instance && destroy_instance && enumerate_version, "resolve Vulkan entrypoints");

  PFN_vkEnumerateInstanceVersion dynamic_enumerate_version =
    (PFN_vkEnumerateInstanceVersion)gipa(NULL, "vkEnumerateInstanceVersion");
  Require(dynamic_enumerate_version != NULL, "resolve dynamic version PFN");

  uint32_t version = 0;
  VkResult vr = enumerate_version(&version);
  fprintf(stderr, "COMBINED pre-create-version result=%d version=0x%x gipa=%p\n", vr, version, (void *)gipa);
  Require(vr == VK_SUCCESS, "enumerate version before create");

  const char *extensions[] = {"VK_EXT_debug_report"};
  VkApplicationInfo app = {
    .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
    .pNext = NULL,
    .pApplicationName = "fex-combined-probe",
    .applicationVersion = 1,
    .pEngineName = "none",
    .engineVersion = 1,
    .apiVersion = VK_API_VERSION_1_0,
  };
  VkInstanceCreateInfo instance_info = {
    .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    .pNext = NULL,
    .flags = 0,
    .pApplicationInfo = &app,
    .enabledLayerCount = 0,
    .ppEnabledLayerNames = NULL,
    .enabledExtensionCount = 1,
    .ppEnabledExtensionNames = extensions,
  };

  VkInstance instance = NULL;
  vr = create_instance(&instance_info, NULL, &instance);
  fprintf(stderr, "COMBINED create-instance result=%d instance=%p\n", vr, (void *)instance);
  Require(vr == VK_SUCCESS && instance != NULL, "create Vulkan instance");

  PFN_vkCreateDebugReportCallbackEXTFn create_debug =
    (PFN_vkCreateDebugReportCallbackEXTFn)gipa(instance, "vkCreateDebugReportCallbackEXT");
  PFN_vkDestroyDebugReportCallbackEXTFn destroy_debug =
    (PFN_vkDestroyDebugReportCallbackEXTFn)gipa(instance, "vkDestroyDebugReportCallbackEXT");
  fprintf(stderr, "COMBINED dynamic-debug create=%p destroy=%p\n", (void *)create_debug, (void *)destroy_debug);
  Require(create_debug && destroy_debug, "resolve debug-report functions dynamically");

  VkDebugReportCallbackCreateInfoEXT debug_info = {
    .sType = VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT,
    .pNext = NULL,
    .flags = VK_DEBUG_REPORT_WARNING_BIT_EXT | VK_DEBUG_REPORT_ERROR_BIT_EXT,
    .pfnCallback = GuestDebugReportCallback,
    .pUserData = NULL,
  };
  VkDebugReportCallbackEXT callback = 0;
  vr = create_debug(instance, &debug_info, NULL, &callback);
  fprintf(stderr, "COMBINED debug-report-created result=%d callback=0x%llx\n", vr, (unsigned long long)callback);
  Require(vr == VK_SUCCESS && callback != 0, "create debug-report callback");

  destroy_debug(instance, callback, NULL);
  fprintf(stderr, "COMBINED debug-report-destroyed\n");
  destroy_instance(instance, NULL);
  fprintf(stderr, "COMBINED instance-destroyed\n");

  Require(dlclose(lib) == 0, "application dlclose libvulkan");
  int wrapper_mapped = AddressMapped((const void *)gipa);
  fprintf(stderr, "COMBINED after-app-close wrapper-mapped=%d gipa=%p dynamic-version=%p\n",
          wrapper_mapped, (void *)gipa, (void *)dynamic_enumerate_version);
  Require(wrapper_mapped == 0, "guest Vulkan wrapper unload after application close");

  version = 0;
  vr = dynamic_enumerate_version(&version);
  fprintf(stderr, "COMBINED post-close-dynamic-version result=%d version=0x%x\n", vr, version);
  Require(vr == VK_SUCCESS, "saved dynamic Vulkan PFN after wrapper unload");

  fprintf(stderr, "COMBINED PASS\n");
  return 0;
}
