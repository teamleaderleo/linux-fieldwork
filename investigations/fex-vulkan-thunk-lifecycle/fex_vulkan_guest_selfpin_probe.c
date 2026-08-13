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

static void *OpenVulkan(void) {
  void *handle = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!handle) {
    fprintf(stderr, "SELFPIN dlopen failed: %s\n", dlerror());
    exit(2);
  }
  return handle;
}

static PFN_vkEnumerateInstanceVersion GetVersionPFN(void *handle, void **gipa_out) {
  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(handle, "vkGetInstanceProcAddr");
  if (!gipa) {
    fprintf(stderr, "SELFPIN missing vkGetInstanceProcAddr: %s\n", dlerror());
    exit(3);
  }
  PFN_vkEnumerateInstanceVersion fn =
    (PFN_vkEnumerateInstanceVersion)gipa(NULL, "vkEnumerateInstanceVersion");
  if (!fn) {
    fprintf(stderr, "SELFPIN vkGetInstanceProcAddr returned NULL\n");
    exit(4);
  }
  *gipa_out = (void *)gipa;
  return fn;
}

static void CallVersion(const char *where, PFN_vkEnumerateInstanceVersion fn) {
  uint32_t version = 0;
  VkResult result = fn(&version);
  fprintf(stderr, "SELFPIN call=%s pfn=%p result=%d version=0x%x\n",
          where, (void *)fn, result, version);
  if (result != VK_SUCCESS) exit(5);
}

int main(void) {
  setvbuf(stderr, NULL, _IONBF, 0);

  void *first = OpenVulkan();
  void *first_gipa = NULL;
  PFN_vkEnumerateInstanceVersion old_fn = GetVersionPFN(first, &first_gipa);
  fprintf(stderr, "SELFPIN generation=1 handle=%p gipa=%p pfn=%p mapped=%d\n",
          first, first_gipa, (void *)old_fn, AddressMapped(first_gipa));
  CallVersion("before-close", old_fn);

  if (dlclose(first) != 0) {
    fprintf(stderr, "SELFPIN first dlclose failed: %s\n", dlerror());
    return 6;
  }

  int retained = AddressMapped(first_gipa);
  fprintf(stderr, "SELFPIN after-final-app-close gipa=%p retained=%d\n", first_gipa, retained);
  if (!retained) {
    return 20;
  }

  CallVersion("old-pfn-after-app-close", old_fn);

  void *second = OpenVulkan();
  void *second_gipa = NULL;
  PFN_vkEnumerateInstanceVersion new_fn = GetVersionPFN(second, &second_gipa);
  fprintf(stderr,
          "SELFPIN reopen handle=%p old-gipa=%p new-gipa=%p old-pfn=%p new-pfn=%p same-gipa=%d same-pfn=%d\n",
          second, first_gipa, second_gipa, (void *)old_fn, (void *)new_fn,
          first_gipa == second_gipa, old_fn == new_fn);
  CallVersion("new-pfn-after-reopen", new_fn);

  if (dlclose(second) != 0) {
    fprintf(stderr, "SELFPIN second dlclose failed: %s\n", dlerror());
    return 7;
  }
  fprintf(stderr, "SELFPIN after-second-close retained=%d\n", AddressMapped(first_gipa));
  return AddressMapped(first_gipa) ? 0 : 21;
}
