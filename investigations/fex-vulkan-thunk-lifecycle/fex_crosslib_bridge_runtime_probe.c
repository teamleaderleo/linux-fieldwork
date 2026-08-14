#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define VK_SUCCESS 0

typedef int32_t VkResult;
typedef uint32_t VkBool32;
typedef void *VkInstance;
typedef void *VkPhysicalDevice;
typedef void (*PFN_vkVoidFunction)(void);
typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(VkInstance instance, const char *name);
typedef VkResult (*PFN_vkCreateInstance)(const void *create_info, const void *allocator, VkInstance *instance);
typedef VkResult (*PFN_vkEnumeratePhysicalDevices)(VkInstance instance, uint32_t *count, VkPhysicalDevice *devices);
typedef VkBool32 (*PFN_vkGetPhysicalDeviceXlibPresentationSupportKHR)(VkPhysicalDevice physical, uint32_t queue_family, void *display, unsigned long visual_id);

typedef void (*GLVoidFunction)(void);
typedef GLVoidFunction (*PFN_glXGetProcAddress)(const unsigned char *name);
typedef int (*PFN_glXQueryVersion)(void *display, int *major, int *minor);
typedef unsigned int (*PFN_glGetError)(void);

struct VkApplicationInfoLite {
  uint32_t sType;
  const void *pNext;
  const char *pApplicationName;
  uint32_t applicationVersion;
  const char *pEngineName;
  uint32_t engineVersion;
  uint32_t apiVersion;
};

struct VkInstanceCreateInfoLite {
  uint32_t sType;
  const void *pNext;
  uint32_t flags;
  const struct VkApplicationInfoLite *pApplicationInfo;
  uint32_t enabledLayerCount;
  const char *const *ppEnabledLayerNames;
  uint32_t enabledExtensionCount;
  const char *const *ppEnabledExtensionNames;
};

static int CountMappingsContaining(const char *needle) {
  FILE *maps = fopen("/proc/self/maps", "r");
  if (!maps) {
    perror("fopen(/proc/self/maps)");
    return -1;
  }
  char line[4096];
  int count = 0;
  while (fgets(line, sizeof(line), maps)) {
    if (strstr(line, needle)) ++count;
  }
  fclose(maps);
  return count;
}

static int FindPathForAddress(void *address, char *out, size_t out_size) {
  FILE *maps = fopen("/proc/self/maps", "r");
  if (!maps) return 0;
  uintptr_t needle = (uintptr_t)address;
  char line[4096];
  while (fgets(line, sizeof(line), maps)) {
    unsigned long long lo = 0, hi = 0;
    if (sscanf(line, "%llx-%llx", &lo, &hi) != 2) continue;
    if (needle < (uintptr_t)lo || needle >= (uintptr_t)hi) continue;
    char *path = strchr(line, '/');
    if (!path) break;
    path[strcspn(path, "\n")] = '\0';
    snprintf(out, out_size, "%s", path);
    fclose(maps);
    return 1;
  }
  fclose(maps);
  return 0;
}

static void Die(const char *what, int code) {
  fprintf(stderr, "PROBE FAIL %s\n", what);
  exit(code);
}

static void ExerciseVulkan(void) {
  void *handle = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!handle) {
    fprintf(stderr, "PROBE Vulkan dlopen failed: %s\n", dlerror());
    exit(2);
  }

  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(handle, "vkGetInstanceProcAddr");
  if (!gipa) Die("vulkan-gipa", 3);
  char wrapper_path[4096] = {};
  if (!FindPathForAddress((void *)gipa, wrapper_path, sizeof(wrapper_path))) Die("vulkan-path", 4);

  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)gipa(NULL, "vkCreateInstance");
  if (!create_instance) Die("vkCreateInstance", 5);

  const char *extensions[] = {"VK_KHR_surface", "VK_KHR_xlib_surface"};
  struct VkApplicationInfoLite app = {
    .sType = 0,
    .pApplicationName = "fex-crosslib-bridge",
    .apiVersion = (1u << 22),
  };
  struct VkInstanceCreateInfoLite ci = {
    .sType = 1,
    .pApplicationInfo = &app,
    .enabledExtensionCount = 2,
    .ppEnabledExtensionNames = extensions,
  };

  VkInstance instance = NULL;
  VkResult cr = create_instance(&ci, NULL, &instance);
  fprintf(stderr, "PROBE Vulkan create result=%d instance=%p wrapper=%s wrapper-maps=%d bridge-maps=%d\n",
          cr, instance, wrapper_path, CountMappingsContaining(wrapper_path),
          CountMappingsContaining("libfex-guest-bridge.so.1"));
  if (cr != VK_SUCCESS || !instance) Die("vulkan-create", 6);

  PFN_vkEnumeratePhysicalDevices enumerate =
    (PFN_vkEnumeratePhysicalDevices)gipa(instance, "vkEnumeratePhysicalDevices");
  PFN_vkGetPhysicalDeviceXlibPresentationSupportKHR xlib_support =
    (PFN_vkGetPhysicalDeviceXlibPresentationSupportKHR)
      gipa(instance, "vkGetPhysicalDeviceXlibPresentationSupportKHR");
  if (!enumerate || !xlib_support) Die("vulkan-required-pfn", 7);

  uint32_t count = 0;
  if (enumerate(instance, &count, NULL) != VK_SUCCESS || count == 0) Die("vulkan-enumerate-count", 8);
  VkPhysicalDevice *devices = calloc(count, sizeof(*devices));
  if (!devices) return;
  if (enumerate(instance, &count, devices) != VK_SUCCESS || count == 0) Die("vulkan-enumerate", 9);

  VkBool32 support = xlib_support(devices[0], 0, (void *)(uintptr_t)0x31111000, 0);
  fprintf(stderr, "PROBE Vulkan Xlib result=%u bridge-maps=%d x11-maps=%d\n",
          support, CountMappingsContaining("libfex-guest-bridge.so.1"),
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libX11.so.6"));

  if (dlclose(handle) != 0) Die("vulkan-dlclose", 10);
  fprintf(stderr, "PROBE Vulkan after-close wrapper-maps=%d bridge-maps=%d x11-maps=%d\n",
          CountMappingsContaining(wrapper_path), CountMappingsContaining("libfex-guest-bridge.so.1"),
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libX11.so.6"));
  if (CountMappingsContaining(wrapper_path) != 0) Die("vulkan-wrapper-still-mapped", 11);
  if (CountMappingsContaining("libfex-guest-bridge.so.1") <= 0) Die("bridge-missing-after-vulkan", 12);

  free(devices);
}

static void ExerciseGL(void) {
  void *handle = dlopen("libGL.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!handle) {
    fprintf(stderr, "PROBE GL dlopen failed: %s\n", dlerror());
    exit(20);
  }

  PFN_glXGetProcAddress get_proc = (PFN_glXGetProcAddress)dlsym(handle, "glXGetProcAddress");
  PFN_glXQueryVersion query_version = (PFN_glXQueryVersion)dlsym(handle, "glXQueryVersion");
  if (!get_proc || !query_version) Die("gl-entrypoints", 21);
  char wrapper_path[4096] = {};
  if (!FindPathForAddress((void *)get_proc, wrapper_path, sizeof(wrapper_path))) Die("gl-path", 22);

  int major = 0, minor = 0;
  int q = query_version((void *)(uintptr_t)0x32222000, &major, &minor);
  fprintf(stderr,
          "PROBE GL glXQueryVersion result=%d version=%d.%d wrapper=%s wrapper-maps=%d bridge-maps=%d x11-maps=%d\n",
          q, major, minor, wrapper_path, CountMappingsContaining(wrapper_path),
          CountMappingsContaining("libfex-guest-bridge.so.1"),
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libX11.so.6"));

  PFN_glGetError old_get_error = (PFN_glGetError)get_proc((const unsigned char *)"glGetError");
  if (!old_get_error) Die("glGetError-pfn", 23);
  unsigned int before = old_get_error();
  fprintf(stderr, "PROBE GL glGetError before-close pfn=%p result=0x%x\n", (void *)old_get_error, before);

  if (dlclose(handle) != 0) Die("gl-dlclose", 24);
  fprintf(stderr, "PROBE GL after-close wrapper-maps=%d bridge-maps=%d x11-maps=%d retained-glGetError=%p\n",
          CountMappingsContaining(wrapper_path), CountMappingsContaining("libfex-guest-bridge.so.1"),
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libX11.so.6"), (void *)old_get_error);
  if (CountMappingsContaining(wrapper_path) != 0) Die("gl-wrapper-still-mapped", 25);
  if (CountMappingsContaining("libfex-guest-bridge.so.1") <= 0) Die("bridge-missing-after-gl", 26);

  unsigned int after = old_get_error();
  fprintf(stderr, "PROBE GL glGetError after-close pfn=%p result=0x%x wrapper-maps=%d bridge-maps=%d\n",
          (void *)old_get_error, after, CountMappingsContaining(wrapper_path),
          CountMappingsContaining("libfex-guest-bridge.so.1"));
  fprintf(stderr, "CROSSLIB_GL_RETAINED_PFN_PASS\n");
}

int main(void) {
  setvbuf(stderr, NULL, _IONBF, 0);
  ExerciseVulkan();
  ExerciseGL();
  fprintf(stderr, "CROSSLIB_SHARED_BRIDGE_PASS\n");
  return 0;
}
