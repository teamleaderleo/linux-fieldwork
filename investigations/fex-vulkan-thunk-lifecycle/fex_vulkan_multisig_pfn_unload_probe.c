#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

#define VK_SUCCESS 0
#define MAX_TRACKED_MAPPINGS 32

typedef int32_t VkResult;
typedef void (*PFN_vkVoidFunction)(void);
typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(void *instance, const char *name);
typedef VkResult (*PFN_vkEnumerateInstanceVersion)(uint32_t *version);
typedef VkResult (*PFN_vkEnumerateInstanceLayerProperties)(uint32_t *count, void *properties);
typedef VkResult (*PFN_vkEnumerateInstanceExtensionProperties)(const char *layer_name, uint32_t *count, void *properties);

struct MappingRange {
  uintptr_t start;
  uintptr_t end;
};

struct MappingSet {
  char path[4096];
  struct MappingRange ranges[MAX_TRACKED_MAPPINGS];
  size_t count;
};

struct VulkanPFNs {
  PFN_vkEnumerateInstanceVersion version;
  PFN_vkEnumerateInstanceLayerProperties layers;
  PFN_vkEnumerateInstanceExtensionProperties extensions;
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
    if (strstr(line, needle)) {
      ++count;
    }
  }
  fclose(maps);
  return count;
}

static int ParseRange(const char *line, uintptr_t *start, uintptr_t *end) {
  unsigned long long lo = 0;
  unsigned long long hi = 0;
  if (sscanf(line, "%llx-%llx", &lo, &hi) != 2) {
    return 0;
  }
  *start = (uintptr_t)lo;
  *end = (uintptr_t)hi;
  return 1;
}

static int FindMappingsForAddress(void *address, struct MappingSet *set) {
  memset(set, 0, sizeof(*set));
  uintptr_t needle = (uintptr_t)address;

  FILE *maps = fopen("/proc/self/maps", "r");
  if (!maps) {
    perror("fopen(/proc/self/maps)");
    return 0;
  }

  char line[4096];
  while (fgets(line, sizeof(line), maps)) {
    uintptr_t start = 0;
    uintptr_t end = 0;
    if (!ParseRange(line, &start, &end) || needle < start || needle >= end) {
      continue;
    }

    char *path = strchr(line, '/');
    if (!path) {
      fprintf(stderr, "PROBE mapping for %p has no pathname: %s", address, line);
      fclose(maps);
      return 0;
    }
    path[strcspn(path, "\n")] = '\0';
    snprintf(set->path, sizeof(set->path), "%s", path);
    break;
  }
  fclose(maps);

  if (!set->path[0]) {
    fprintf(stderr, "PROBE no mapping found for address=%p\n", address);
    return 0;
  }

  maps = fopen("/proc/self/maps", "r");
  if (!maps) {
    perror("fopen(/proc/self/maps)");
    return 0;
  }

  while (fgets(line, sizeof(line), maps)) {
    char *path = strchr(line, '/');
    if (!path) {
      continue;
    }
    path[strcspn(path, "\n")] = '\0';
    if (strcmp(path, set->path) != 0) {
      continue;
    }
    if (set->count == MAX_TRACKED_MAPPINGS) {
      fprintf(stderr, "PROBE too many mappings for %s\n", set->path);
      fclose(maps);
      return 0;
    }
    if (!ParseRange(line, &set->ranges[set->count].start, &set->ranges[set->count].end)) {
      continue;
    }
    ++set->count;
  }
  fclose(maps);

  fprintf(stderr, "PROBE tracked-path=%s mappings=%zu anchor=%p\n", set->path, set->count, address);
  for (size_t i = 0; i < set->count; ++i) {
    fprintf(stderr, "PROBE tracked-range[%zu]=0x%lx-0x%lx\n", i,
            (unsigned long)set->ranges[i].start, (unsigned long)set->ranges[i].end);
  }
  return set->count != 0;
}

static int ReserveOldMappings(const struct MappingSet *set) {
  for (size_t i = 0; i < set->count; ++i) {
    size_t length = set->ranges[i].end - set->ranges[i].start;
    void *wanted = (void *)set->ranges[i].start;
    void *result = mmap(wanted, length, PROT_NONE,
                        MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    if (result == MAP_FAILED) {
      fprintf(stderr, "PROBE reserve-old-range failed range=0x%lx-0x%lx errno=%d (%s)\n",
              (unsigned long)set->ranges[i].start, (unsigned long)set->ranges[i].end,
              errno, strerror(errno));
      return 0;
    }
    if (result != wanted) {
      fprintf(stderr, "PROBE reserve-old-range wrong-address wanted=%p got=%p\n", wanted, result);
      return 0;
    }
  }
  fprintf(stderr, "PROBE reserved-old-generation-ranges=%zu\n", set->count);
  return 1;
}

static void ReleaseOldMappings(const struct MappingSet *set) {
  for (size_t i = 0; i < set->count; ++i) {
    size_t length = set->ranges[i].end - set->ranges[i].start;
    munmap((void *)set->ranges[i].start, length);
  }
}

static void *OpenVulkan(void) {
  void *handle = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!handle) {
    fprintf(stderr, "PROBE dlopen failed: %s\n", dlerror());
    exit(2);
  }
  return handle;
}

static struct VulkanPFNs GetDynamicPFNs(void *handle, void **gipa_out) {
  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(handle, "vkGetInstanceProcAddr");
  if (!gipa) {
    fprintf(stderr, "PROBE missing vkGetInstanceProcAddr: %s\n", dlerror());
    exit(3);
  }
  if (gipa_out) {
    *gipa_out = (void *)gipa;
  }

  struct VulkanPFNs fns = {
    .version = (PFN_vkEnumerateInstanceVersion)gipa(NULL, "vkEnumerateInstanceVersion"),
    .layers = (PFN_vkEnumerateInstanceLayerProperties)gipa(NULL, "vkEnumerateInstanceLayerProperties"),
    .extensions = (PFN_vkEnumerateInstanceExtensionProperties)gipa(NULL, "vkEnumerateInstanceExtensionProperties"),
  };
  if (!fns.version || !fns.layers || !fns.extensions) {
    fprintf(stderr, "PROBE one or more vkGetInstanceProcAddr lookups returned NULL version=%p layers=%p extensions=%p\n",
            (void *)fns.version, (void *)fns.layers, (void *)fns.extensions);
    exit(4);
  }
  return fns;
}

static void CallAll(const char *where, const struct VulkanPFNs *fns) {
  uint32_t version = 0;
  uint32_t layer_count = 0;
  uint32_t extension_count = 0;

  fprintf(stderr,
          "PROBE call where=%s version=%p layers=%p extensions=%p vulkan-maps=%d bridge-maps=%d\n",
          where, (void *)fns->version, (void *)fns->layers, (void *)fns->extensions,
          CountMappingsContaining("libvulkan.so.1"), CountMappingsContaining("libfex-vulkan-bridge"));

  VkResult vr = fns->version(&version);
  VkResult lr = fns->layers(&layer_count, NULL);
  VkResult er = fns->extensions(NULL, &extension_count, NULL);

  fprintf(stderr,
          "PROBE return where=%s version-result=%d version=0x%x layers-result=%d layers=%u extensions-result=%d extensions=%u vulkan-maps=%d bridge-maps=%d\n",
          where, vr, version, lr, layer_count, er, extension_count,
          CountMappingsContaining("libvulkan.so.1"), CountMappingsContaining("libfex-vulkan-bridge"));

  if (vr != VK_SUCCESS || lr != VK_SUCCESS || er != VK_SUCCESS || version == 0) {
    exit(5);
  }
}

int main(int argc, char **argv) {
  setvbuf(stderr, NULL, _IONBF, 0);
  if (argc != 2 || (strcmp(argv[1], "close") && strcmp(argv[1], "reload"))) {
    fprintf(stderr, "usage: %s close|reload\n", argv[0]);
    return 64;
  }

  void *first = OpenVulkan();
  void *first_gipa = NULL;
  struct VulkanPFNs old_fns = GetDynamicPFNs(first, &first_gipa);
  struct MappingSet old_mappings;
  if (!FindMappingsForAddress(first_gipa, &old_mappings)) {
    return 7;
  }

  fprintf(stderr,
          "PROBE acquired generation=1 handle=%p gipa=%p version=%p layers=%p extensions=%p vulkan-maps=%d bridge-maps=%d\n",
          first, first_gipa, (void *)old_fns.version, (void *)old_fns.layers, (void *)old_fns.extensions,
          CountMappingsContaining("libvulkan.so.1"), CountMappingsContaining("libfex-vulkan-bridge"));
  CallAll("before-close", &old_fns);

  if (dlclose(first) != 0) {
    fprintf(stderr, "PROBE dlclose failed: %s\n", dlerror());
    return 6;
  }
  fprintf(stderr, "PROBE after-close vulkan-maps=%d bridge-maps=%d\n",
          CountMappingsContaining("libvulkan.so.1"), CountMappingsContaining("libfex-vulkan-bridge"));
  if (CountMappingsContaining("libvulkan.so.1") != 0 || CountMappingsContaining("libfex-vulkan-bridge") <= 0) {
    fprintf(stderr, "PROBE lifetime split invariant failed after close\n");
    return 11;
  }

  CallAll("after-real-close-old-pfns", &old_fns);

  if (!strcmp(argv[1], "close")) {
    fprintf(stderr, "PROBE close-mode-pass\n");
    return 0;
  }

  if (!ReserveOldMappings(&old_mappings)) {
    fprintf(stderr, "PROBE old generation was not fully unmapped; cannot force changed-base reload\n");
    return 8;
  }

  void *second = OpenVulkan();
  void *second_gipa = NULL;
  struct VulkanPFNs new_fns = GetDynamicPFNs(second, &second_gipa);
  struct MappingSet new_mappings;
  if (!FindMappingsForAddress(second_gipa, &new_mappings)) {
    return 9;
  }

  fprintf(stderr,
          "PROBE acquired generation=2 handle=%p old-gipa=%p new-gipa=%p old-version=%p new-version=%p old-layers=%p new-layers=%p old-extensions=%p new-extensions=%p same-version=%d same-layers=%d same-extensions=%d vulkan-maps=%d bridge-maps=%d\n",
          second, first_gipa, second_gipa,
          (void *)old_fns.version, (void *)new_fns.version,
          (void *)old_fns.layers, (void *)new_fns.layers,
          (void *)old_fns.extensions, (void *)new_fns.extensions,
          old_fns.version == new_fns.version, old_fns.layers == new_fns.layers,
          old_fns.extensions == new_fns.extensions,
          CountMappingsContaining("libvulkan.so.1"), CountMappingsContaining("libfex-vulkan-bridge"));

  if (!strcmp(old_mappings.path, new_mappings.path) && first_gipa == second_gipa) {
    fprintf(stderr, "PROBE changed-base reload failed: guest entrypoint reused old address despite reservations\n");
    return 10;
  }

  CallAll("after-reload-new-pfns", &new_fns);
  CallAll("after-reload-old-pfns", &old_fns);

  if (dlclose(second) != 0) {
    fprintf(stderr, "PROBE second dlclose failed: %s\n", dlerror());
    return 12;
  }
  fprintf(stderr, "PROBE after-second-close vulkan-maps=%d bridge-maps=%d\n",
          CountMappingsContaining("libvulkan.so.1"), CountMappingsContaining("libfex-vulkan-bridge"));
  if (CountMappingsContaining("libvulkan.so.1") != 0 || CountMappingsContaining("libfex-vulkan-bridge") <= 0) {
    return 13;
  }

  ReleaseOldMappings(&old_mappings);
  fprintf(stderr, "PROBE reload-mode-pass\n");
  return 0;
}
