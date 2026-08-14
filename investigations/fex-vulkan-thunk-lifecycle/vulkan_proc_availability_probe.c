#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>

static int read_names(const char *path, char ***out_names, size_t *out_count) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror("fopen command corpus");
    return 1;
  }

  char **names = NULL;
  size_t count = 0;
  size_t capacity = 0;
  char *line = NULL;
  size_t line_capacity = 0;

  while (getline(&line, &line_capacity, f) >= 0) {
    size_t len = strlen(line);
    while (len && (line[len - 1] == '\n' || line[len - 1] == '\r')) {
      line[--len] = '\0';
    }
    if (!len) {
      continue;
    }
    if (count == capacity) {
      size_t next = capacity ? capacity * 2 : 256;
      char **tmp = realloc(names, next * sizeof(*tmp));
      if (!tmp) {
        free(line);
        fclose(f);
        return 2;
      }
      names = tmp;
      capacity = next;
    }
    names[count] = strdup(line);
    if (!names[count]) {
      free(line);
      fclose(f);
      return 3;
    }
    ++count;
  }

  free(line);
  fclose(f);
  *out_names = names;
  *out_count = count;
  return 0;
}

static void free_names(char **names, size_t count) {
  for (size_t i = 0; i < count; ++i) {
    free(names[i]);
  }
  free(names);
}

int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: %s COMMAND_NAMES.txt\n", argv[0]);
    return 2;
  }

  char **names = NULL;
  size_t name_count = 0;
  int rr = read_names(argv[1], &names, &name_count);
  if (rr) {
    return 10 + rr;
  }

  void *vk = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!vk) {
    fprintf(stderr, "dlopen libvulkan.so.1 failed: %s\n", dlerror());
    free_names(names, name_count);
    return 20;
  }

  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(vk, "vkGetInstanceProcAddr");
  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(vk, "vkCreateInstance");
  if (!gipa || !create_instance) {
    fprintf(stderr, "required Vulkan loader symbols missing\n");
    dlclose(vk);
    free_names(names, name_count);
    return 21;
  }

  uint32_t api_version = VK_API_VERSION_1_0;
  PFN_vkEnumerateInstanceVersion enumerate_version = (PFN_vkEnumerateInstanceVersion)gipa(VK_NULL_HANDLE, "vkEnumerateInstanceVersion");
  if (enumerate_version) {
    uint32_t reported = VK_API_VERSION_1_0;
    if (enumerate_version(&reported) == VK_SUCCESS && reported >= VK_API_VERSION_1_0) {
      api_version = reported;
    }
  }

  VkApplicationInfo app = {
    .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
    .pApplicationName = "fex-proc-availability-corpus",
    .applicationVersion = 1,
    .pEngineName = "none",
    .engineVersion = 1,
    .apiVersion = api_version,
  };
  VkInstanceCreateInfo ici = {
    .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    .pApplicationInfo = &app,
  };

  VkInstance instance = VK_NULL_HANDLE;
  VkResult instance_result = create_instance(&ici, NULL, &instance);
  fprintf(stderr, "META api_version=%u instance_result=%d corpus_count=%zu\n", api_version, instance_result, name_count);
  if (instance_result != VK_SUCCESS || instance == VK_NULL_HANDLE) {
    dlclose(vk);
    free_names(names, name_count);
    return 22;
  }

  PFN_vkDestroyInstance destroy_instance = (PFN_vkDestroyInstance)gipa(instance, "vkDestroyInstance");
  PFN_vkEnumeratePhysicalDevices enumerate_phys = (PFN_vkEnumeratePhysicalDevices)gipa(instance, "vkEnumeratePhysicalDevices");
  PFN_vkGetPhysicalDeviceQueueFamilyProperties get_qf =
    (PFN_vkGetPhysicalDeviceQueueFamilyProperties)gipa(instance, "vkGetPhysicalDeviceQueueFamilyProperties");
  PFN_vkCreateDevice create_device = (PFN_vkCreateDevice)gipa(instance, "vkCreateDevice");
  if (!destroy_instance || !enumerate_phys || !get_qf || !create_device) {
    fprintf(stderr, "required instance-level Vulkan symbols missing\n");
    if (destroy_instance) {
      destroy_instance(instance, NULL);
    }
    dlclose(vk);
    free_names(names, name_count);
    return 23;
  }

  uint32_t phys_count = 0;
  VkResult phys_result = enumerate_phys(instance, &phys_count, NULL);
  if (phys_result != VK_SUCCESS || phys_count == 0) {
    fprintf(stderr, "physical device enumeration failed: result=%d count=%u\n", phys_result, phys_count);
    destroy_instance(instance, NULL);
    dlclose(vk);
    free_names(names, name_count);
    return 24;
  }

  VkPhysicalDevice *phys = calloc(phys_count, sizeof(*phys));
  if (!phys) {
    destroy_instance(instance, NULL);
    dlclose(vk);
    free_names(names, name_count);
    return 25;
  }
  phys_result = enumerate_phys(instance, &phys_count, phys);
  if (phys_result != VK_SUCCESS || phys_count == 0) {
    free(phys);
    destroy_instance(instance, NULL);
    dlclose(vk);
    free_names(names, name_count);
    return 26;
  }
  VkPhysicalDevice physical_device = phys[0];
  free(phys);

  uint32_t qf_count = 0;
  get_qf(physical_device, &qf_count, NULL);
  if (!qf_count) {
    destroy_instance(instance, NULL);
    dlclose(vk);
    free_names(names, name_count);
    return 27;
  }
  VkQueueFamilyProperties *qf = calloc(qf_count, sizeof(*qf));
  if (!qf) {
    destroy_instance(instance, NULL);
    dlclose(vk);
    free_names(names, name_count);
    return 28;
  }
  get_qf(physical_device, &qf_count, qf);
  uint32_t queue_family = UINT32_MAX;
  for (uint32_t i = 0; i < qf_count; ++i) {
    if (qf[i].queueCount) {
      queue_family = i;
      break;
    }
  }
  free(qf);
  if (queue_family == UINT32_MAX) {
    destroy_instance(instance, NULL);
    dlclose(vk);
    free_names(names, name_count);
    return 29;
  }

  float priority = 1.0f;
  VkDeviceQueueCreateInfo qci = {
    .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
    .queueFamilyIndex = queue_family,
    .queueCount = 1,
    .pQueuePriorities = &priority,
  };
  VkDeviceCreateInfo dci = {
    .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
    .queueCreateInfoCount = 1,
    .pQueueCreateInfos = &qci,
  };

  VkDevice device = VK_NULL_HANDLE;
  VkResult device_result = create_device(physical_device, &dci, NULL, &device);
  fprintf(stderr, "META phys_count=%u queue_family=%u device_result=%d\n", phys_count, queue_family, device_result);
  if (device_result != VK_SUCCESS || device == VK_NULL_HANDLE) {
    destroy_instance(instance, NULL);
    dlclose(vk);
    free_names(names, name_count);
    return 30;
  }

  PFN_vkGetDeviceProcAddr gdpa = (PFN_vkGetDeviceProcAddr)gipa(instance, "vkGetDeviceProcAddr");
  PFN_vkDestroyDevice destroy_device = NULL;
  if (gdpa) {
    destroy_device = (PFN_vkDestroyDevice)gdpa(device, "vkDestroyDevice");
  }
  if (!gdpa || !destroy_device) {
    fprintf(stderr, "required device-level Vulkan symbols missing\n");
    destroy_instance(instance, NULL);
    dlclose(vk);
    free_names(names, name_count);
    return 31;
  }

  puts("name\tdirect\tgipa_null\tgipa_instance\tgdpa_device");
  for (size_t i = 0; i < name_count; ++i) {
    const char *name = names[i];
    int direct = dlsym(vk, name) != NULL;
    int gipa_null = gipa(VK_NULL_HANDLE, name) != NULL;
    int gipa_instance = gipa(instance, name) != NULL;
    int gdpa_device = gdpa(device, name) != NULL;
    printf("%s\t%d\t%d\t%d\t%d\n", name, direct, gipa_null, gipa_instance, gdpa_device);
  }
  fflush(stdout);

  destroy_device(device, NULL);
  destroy_instance(instance, NULL);
  int close_result = dlclose(vk);
  free_names(names, name_count);
  if (close_result != 0) {
    fprintf(stderr, "dlclose failed: %s\n", dlerror());
    return 32;
  }
  return 0;
}
