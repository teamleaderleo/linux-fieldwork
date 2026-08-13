#include <stdint.h>
#include <stdio.h>
#include <dlfcn.h>

#define VK_SUCCESS 0
#define VK_STRUCTURE_TYPE_APPLICATION_INFO 0
#define VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO 1
#define VK_API_VERSION_1_0 (1u << 22)

typedef int32_t VkResult;
typedef uint32_t VkFlags;
typedef struct VkInstance_T *VkInstance;
typedef void (*PFN_vkVoidFunction)(void);

typedef struct {
  int32_t sType;
  const void *pNext;
  const char *pApplicationName;
  uint32_t applicationVersion;
  const char *pEngineName;
  uint32_t engineVersion;
  uint32_t apiVersion;
} VkApplicationInfo;

typedef struct {
  int32_t sType;
  const void *pNext;
  VkFlags flags;
  const VkApplicationInfo *pApplicationInfo;
  uint32_t enabledLayerCount;
  const char *const *ppEnabledLayerNames;
  uint32_t enabledExtensionCount;
  const char *const *ppEnabledExtensionNames;
} VkInstanceCreateInfo;

typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(VkInstance, const char *);
typedef VkResult (*PFN_vkCreateInstance)(const VkInstanceCreateInfo *, const void *, VkInstance *);

static int Check(const char *name, PFN_vkVoidFunction value, int expect_nonnull) {
  int got_nonnull = value != 0;
  int ok = got_nonnull == expect_nonnull;
  fprintf(stderr, "PROCADDR_CASE name=%s got=%s expected=%s status=%s\n",
          name, got_nonnull ? "fp" : "NULL", expect_nonnull ? "fp" : "NULL", ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}

int main(void) {
  void *library = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!library) return 2;

  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(library, "vkGetInstanceProcAddr");
  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(library, "vkCreateInstance");
  if (!gipa || !create_instance) return 3;

  int failures = 0;
  failures += Check("null-create-instance", gipa(0, "vkCreateInstance"), 1);
  failures += Check("null-create-device", gipa(0, "vkCreateDevice"), 0);
  failures += Check("null-get-device-proc-addr", gipa(0, "vkGetDeviceProcAddr"), 0);

  VkApplicationInfo app = {VK_STRUCTURE_TYPE_APPLICATION_INFO, 0, "procaddr-probe", 1, "none", 1, VK_API_VERSION_1_0};
  VkInstanceCreateInfo info = {VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, 0, 0, &app, 0, 0, 0, 0};
  VkInstance instance = 0;
  VkResult result = create_instance(&info, 0, &instance);
  fprintf(stderr, "PROCADDR_INSTANCE result=%d instance=%p\n", result, (void *)instance);
  if (result != VK_SUCCESS || !instance) return 10;

  failures += Check("instance-gipa-self", gipa(instance, "vkGetInstanceProcAddr"), 1);
  failures += Check("disabled-debug-report-create", gipa(instance, "vkCreateDebugReportCallbackEXT"), 0);
  failures += Check("disabled-debug-utils-create", gipa(instance, "vkCreateDebugUtilsMessengerEXT"), 0);

  fprintf(stderr, "PROCADDR_FINISH failures=%d\n", failures);
  return failures ? 20 : 0;
}
