#define _GNU_SOURCE
#define VK_USE_PLATFORM_XLIB_KHR
#include <vulkan/vulkan.h>

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int CountMappingsContaining(const char *needle) {
  FILE *maps = fopen("/proc/self/maps", "r");
  if (!maps) {
    perror("fopen(/proc/self/maps)");
    return -1;
  }

  char line[4096];
  int count = 0;
  while (fgets(line, sizeof(line), maps)) {
    if (strstr(line, needle)) {
      ++count;
    }
  }
  fclose(maps);
  return count;
}

static void Die(const char *what, int code) {
  fprintf(stderr, "PROBE FAIL %s\n", what);
  exit(code);
}

int main(void) {
  setvbuf(stderr, NULL, _IONBF, 0);

  void *vulkan = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vulkan) {
    fprintf(stderr, "PROBE dlopen failed: %s\n", dlerror());
    return 2;
  }

  PFN_vkGetInstanceProcAddr gipa =
    (PFN_vkGetInstanceProcAddr)dlsym(vulkan, "vkGetInstanceProcAddr");
  if (!gipa) Die("gipa", 3);

  PFN_vkCreateInstance create_instance =
    (PFN_vkCreateInstance)gipa(VK_NULL_HANDLE, "vkCreateInstance");
  if (!create_instance) Die("create-instance-pfn", 4);

  const char *exts[] = {
    VK_KHR_SURFACE_EXTENSION_NAME,
    VK_KHR_XLIB_SURFACE_EXTENSION_NAME,
  };
  VkApplicationInfo app = {
    .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
    .pApplicationName = "fex-split-x11-callback",
    .apiVersion = VK_API_VERSION_1_0,
  };
  VkInstanceCreateInfo ci = {
    .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    .pApplicationInfo = &app,
    .enabledExtensionCount = 2,
    .ppEnabledExtensionNames = exts,
  };

  VkInstance instance = VK_NULL_HANDLE;
  VkResult create_result = create_instance(&ci, NULL, &instance);
  fprintf(stderr,
          "PROBE create-instance result=%d instance=%p vulkan-maps=%d bridge-maps=%d x11-maps=%d\n",
          create_result, (void *)instance,
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libvulkan.so.1"),
          CountMappingsContaining("libfex-vulkan-bridge.so.1"),
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libX11.so.6"));
  if (create_result != VK_SUCCESS) return 5;

  PFN_vkEnumeratePhysicalDevices enumerate =
    (PFN_vkEnumeratePhysicalDevices)gipa(instance, "vkEnumeratePhysicalDevices");
  PFN_vkGetPhysicalDeviceXlibPresentationSupportKHR xlib_support =
    (PFN_vkGetPhysicalDeviceXlibPresentationSupportKHR)
      gipa(instance, "vkGetPhysicalDeviceXlibPresentationSupportKHR");
  if (!enumerate || !xlib_support) Die("required-pfn", 6);

  uint32_t count = 0;
  if (enumerate(instance, &count, NULL) != VK_SUCCESS || count == 0) {
    Die("enumerate-count", 7);
  }
  VkPhysicalDevice *phys = calloc(count, sizeof(*phys));
  if (!phys) return 8;
  if (enumerate(instance, &count, phys) != VK_SUCCESS || count == 0) {
    Die("enumerate-devices", 9);
  }

  fprintf(stderr,
          "PROBE acquired xlib-pfn=%p physical=%p vulkan-maps=%d bridge-maps=%d x11-maps=%d\n",
          (void *)xlib_support, (void *)phys[0],
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libvulkan.so.1"),
          CountMappingsContaining("libfex-vulkan-bridge.so.1"),
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libX11.so.6"));

  Display *display_before = (Display *)(uintptr_t)0x12345000;
  Display *display_after = (Display *)(uintptr_t)0x12346000;

  VkBool32 before = xlib_support(phys[0], 0, display_before, 0);
  fprintf(stderr, "PROBE before-close-xlib result=%u\n", before);

  if (dlclose(vulkan) != 0) {
    fprintf(stderr, "PROBE dlclose failed: %s\n", dlerror());
    return 10;
  }

  int vulkan_maps = CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libvulkan.so.1");
  int bridge_maps = CountMappingsContaining("libfex-vulkan-bridge.so.1");
  int x11_maps = CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libX11.so.6");
  fprintf(stderr,
          "PROBE after-dlclose vulkan-maps=%d bridge-maps=%d x11-maps=%d retained-xlib-pfn=%p\n",
          vulkan_maps, bridge_maps, x11_maps, (void *)xlib_support);

  if (vulkan_maps != 0) Die("vulkan-wrapper-still-mapped", 11);
  if (bridge_maps <= 0) Die("resident-bridge-missing", 12);
  if (x11_maps <= 0) Die("guest-x11-missing", 13);

  fprintf(stderr, "PROBE AFTER_DLCLOSE_BEGIN_CALLBACK_TEST\n");
  VkBool32 after = xlib_support(phys[0], 0, display_after, 0);
  fprintf(stderr,
          "PROBE after-close-xlib result=%u vulkan-maps=%d bridge-maps=%d x11-maps=%d\n",
          after,
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libvulkan.so.1"),
          CountMappingsContaining("libfex-vulkan-bridge.so.1"),
          CountMappingsContaining("/usr/lib/x86_64-linux-gnu/libX11.so.6"));
  fprintf(stderr, "SPLIT_VULKAN_X11_CALLBACK_PASS\n");

  free(phys);
  return 0;
}
