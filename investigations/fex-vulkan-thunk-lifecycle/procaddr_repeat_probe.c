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

int main(void) {
  void *library = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!library) return 2;
  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(library, "vkGetInstanceProcAddr");
  if (!gipa) return 3;

  PFN_vkVoidFunction create_a = gipa(0, "vkCreateInstance");
  PFN_vkVoidFunction create_b = gipa(0, "vkCreateInstance");
  fprintf(stderr, "REPEAT_CREATE a=%p b=%p same=%d\n", (void *)create_a, (void *)create_b, create_a == create_b);
  if (!create_a || create_a != create_b) return 10;

  VkApplicationInfo app = {VK_STRUCTURE_TYPE_APPLICATION_INFO, 0, "repeat-probe", 1, "none", 1, VK_API_VERSION_1_0};
  VkInstanceCreateInfo info = {VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, 0, 0, &app, 0, 0, 0, 0};
  VkInstance instance = 0;
  VkResult result = ((PFN_vkCreateInstance)create_a)(&info, 0, &instance);
  fprintf(stderr, "REPEAT_DYNAMIC_CREATE result=%d instance=%p\n", result, (void *)instance);
  if (result != VK_SUCCESS || !instance) return 11;

  PFN_vkVoidFunction self_a = gipa(instance, "vkGetInstanceProcAddr");
  PFN_vkVoidFunction self_b = gipa(instance, "vkGetInstanceProcAddr");
  PFN_vkVoidFunction gdpa_a = gipa(instance, "vkGetDeviceProcAddr");
  PFN_vkVoidFunction gdpa_b = gipa(instance, "vkGetDeviceProcAddr");
  fprintf(stderr, "REPEAT_SELF a=%p b=%p same=%d\n", (void *)self_a, (void *)self_b, self_a == self_b);
  fprintf(stderr, "REPEAT_GDPA a=%p b=%p same=%d\n", (void *)gdpa_a, (void *)gdpa_b, gdpa_a == gdpa_b);

  if (!self_a || self_a != self_b) return 12;
  if (!gdpa_a || gdpa_a != gdpa_b) return 13;
  return 0;
}
