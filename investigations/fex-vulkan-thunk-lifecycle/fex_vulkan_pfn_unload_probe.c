#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define VK_SUCCESS 0

typedef int32_t VkResult;
typedef void (*PFN_vkVoidFunction)(void);
typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(void *instance, const char *name);
typedef VkResult (*PFN_vkEnumerateInstanceVersion)(uint32_t *version);

static int CountGuestVulkanMappings(void) {
  FILE *maps = fopen("/proc/self/maps", "r");
  if (!maps) {
    perror("fopen(/proc/self/maps)");
    return -1;
  }

  char line[4096];
  int count = 0;
  while (fgets(line, sizeof(line), maps)) {
    if (strstr(line, "libvulkan")) {
      ++count;
    }
  }
  fclose(maps);
  return count;
}

static void *OpenVulkan(void) {
  void *handle = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!handle) {
    fprintf(stderr, "PROBE dlopen failed: %s\n", dlerror());
    exit(2);
  }
  return handle;
}

static PFN_vkEnumerateInstanceVersion GetDynamicVersionPFN(void *handle) {
  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(handle, "vkGetInstanceProcAddr");
  if (!gipa) {
    fprintf(stderr, "PROBE missing vkGetInstanceProcAddr: %s\n", dlerror());
    exit(3);
  }

  PFN_vkEnumerateInstanceVersion fn =
    (PFN_vkEnumerateInstanceVersion)gipa(NULL, "vkEnumerateInstanceVersion");
  if (!fn) {
    fprintf(stderr, "PROBE vkGetInstanceProcAddr returned NULL\n");
    exit(4);
  }
  return fn;
}

static void CallVersion(const char *where, PFN_vkEnumerateInstanceVersion fn) {
  uint32_t version = 0;
  fprintf(stderr, "PROBE call where=%s pfn=%p maps=%d\n", where, (void *)fn, CountGuestVulkanMappings());
  VkResult result = fn(&version);
  fprintf(stderr, "PROBE return where=%s result=%d version=0x%x maps=%d\n",
          where, result, version, CountGuestVulkanMappings());
  if (result != VK_SUCCESS) {
    exit(5);
  }
}

int main(int argc, char **argv) {
  setvbuf(stderr, NULL, _IONBF, 0);
  if (argc != 2 || (strcmp(argv[1], "close") && strcmp(argv[1], "hold") && strcmp(argv[1], "reload"))) {
    fprintf(stderr, "usage: %s close|hold|reload\n", argv[0]);
    return 64;
  }

  void *first = OpenVulkan();
  PFN_vkEnumerateInstanceVersion old_fn = GetDynamicVersionPFN(first);
  fprintf(stderr, "PROBE acquired generation=1 handle=%p pfn=%p maps=%d\n",
          first, (void *)old_fn, CountGuestVulkanMappings());
  CallVersion("before-close", old_fn);

  if (!strcmp(argv[1], "hold")) {
    void *pin = OpenVulkan();
    fprintf(stderr, "PROBE extra-ref handle=%p maps=%d\n", pin, CountGuestVulkanMappings());
    if (dlclose(first) != 0) {
      fprintf(stderr, "PROBE first dlclose failed: %s\n", dlerror());
      return 6;
    }
    fprintf(stderr, "PROBE after-first-close maps=%d\n", CountGuestVulkanMappings());
    CallVersion("after-close-with-extra-ref", old_fn);
    dlclose(pin);
    return 0;
  }

  if (dlclose(first) != 0) {
    fprintf(stderr, "PROBE dlclose failed: %s\n", dlerror());
    return 6;
  }
  fprintf(stderr, "PROBE after-close maps=%d old-pfn=%p\n", CountGuestVulkanMappings(), (void *)old_fn);

  if (!strcmp(argv[1], "close")) {
    fprintf(stderr, "PROBE about-to-call-stale-pfn=%p\n", (void *)old_fn);
    CallVersion("after-real-close", old_fn);
    fprintf(stderr, "PROBE stale call unexpectedly returned\n");
    return 0;
  }

  void *second = OpenVulkan();
  PFN_vkEnumerateInstanceVersion new_fn = GetDynamicVersionPFN(second);
  fprintf(stderr, "PROBE acquired generation=2 handle=%p old-pfn=%p new-pfn=%p same-pfn=%d maps=%d\n",
          second, (void *)old_fn, (void *)new_fn, old_fn == new_fn, CountGuestVulkanMappings());
  CallVersion("after-reload-new-pfn", new_fn);
  dlclose(second);
  return 0;
}
