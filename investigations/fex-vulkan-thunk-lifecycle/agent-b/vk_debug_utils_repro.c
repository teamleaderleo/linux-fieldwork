#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t VkBool32;
typedef int32_t VkResult;
typedef uint32_t VkFlags;
typedef uint32_t VkStructureType;
typedef struct VkInstance_T *VkInstance;
typedef uint64_t VkDebugUtilsMessengerEXT;
typedef void (*PFN_vkVoidFunction)(void);

#define VK_SUCCESS 0
#define VK_ERROR_EXTENSION_NOT_PRESENT (-7)
#define VK_FALSE 0u
#define VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO 1u
#define VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CALLBACK_DATA_EXT 1000128003u
#define VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT 1000128004u
#define VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT 0x00000100u
#define VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT   0x00001000u
#define VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT     0x00000001u
#define VK_EXT_DEBUG_UTILS_EXTENSION_NAME "VK_EXT_debug_utils"

struct VkInstanceCreateInfo {
  VkStructureType sType;
  const void *pNext;
  VkFlags flags;
  const void *pApplicationInfo;
  uint32_t enabledLayerCount;
  const char *const *ppEnabledLayerNames;
  uint32_t enabledExtensionCount;
  const char *const *ppEnabledExtensionNames;
};

struct VkDebugUtilsMessengerCallbackDataEXT {
  VkStructureType sType;
  const void *pNext;
  VkFlags flags;
  const char *pMessageIdName;
  int32_t messageIdNumber;
  const char *pMessage;
};

typedef VkBool32 (*PFN_vkDebugUtilsMessengerCallbackEXT)(
    uint32_t severity,
    VkFlags types,
    const struct VkDebugUtilsMessengerCallbackDataEXT *data,
    void *user_data);

struct VkDebugUtilsMessengerCreateInfoEXT {
  VkStructureType sType;
  const void *pNext;
  VkFlags flags;
  VkFlags messageSeverity;
  VkFlags messageType;
  PFN_vkDebugUtilsMessengerCallbackEXT pfnUserCallback;
  void *pUserData;
};

typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(VkInstance, const char *);
typedef VkResult (*PFN_vkCreateInstance)(const struct VkInstanceCreateInfo *, const void *, VkInstance *);
typedef void (*PFN_vkDestroyInstance)(VkInstance, const void *);
typedef VkResult (*PFN_vkCreateDebugUtilsMessengerEXT)(VkInstance, const struct VkDebugUtilsMessengerCreateInfoEXT *, const void *, VkDebugUtilsMessengerEXT *);
typedef void (*PFN_vkDestroyDebugUtilsMessengerEXT)(VkInstance, VkDebugUtilsMessengerEXT, const void *);
typedef void (*PFN_vkSubmitDebugUtilsMessageEXT)(VkInstance, uint32_t, VkFlags, const struct VkDebugUtilsMessengerCallbackDataEXT *);

struct State {
  uint32_t matched;
};

static VkBool32 callback(uint32_t severity, VkFlags types,
                         const struct VkDebugUtilsMessengerCallbackDataEXT *data,
                         void *user_data) {
  struct State *state = user_data;
  if ((severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT) &&
      (types & VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT) && data &&
      data->pMessage && strcmp(data->pMessage, "fex-debug-utils-repro") == 0) {
    state->matched++;
    fputs("CALLBACK debug_utils MATCH\n", stderr);
  }
  return VK_FALSE;
}

static int has_arg(int argc, char **argv, const char *arg) {
  for (int i = 1; i < argc; ++i) if (strcmp(argv[i], arg) == 0) return 1;
  return 0;
}

int main(int argc, char **argv) {
  const int no_submit = has_arg(argc, argv, "--no-submit");
  const int filter_miss = has_arg(argc, argv, "--filter-miss");
  const int expect_suppressed = has_arg(argc, argv, "--expect=suppressed");
  setvbuf(stderr, NULL, _IONBF, 0);

  void *lib = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!lib) return 77;
  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(lib, "vkGetInstanceProcAddr");
  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(lib, "vkCreateInstance");
  if (!gipa || !create_instance) return 77;

  const char *extensions[] = {VK_EXT_DEBUG_UTILS_EXTENSION_NAME};
  struct VkInstanceCreateInfo ici = {
      .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
      .enabledExtensionCount = 1,
      .ppEnabledExtensionNames = extensions,
  };
  VkInstance instance = 0;
  VkResult vr = create_instance(&ici, 0, &instance);
  if (vr != VK_SUCCESS) {
    fprintf(stderr, "SKIP vkCreateInstance result=%d%s\n", vr,
            vr == VK_ERROR_EXTENSION_NOT_PRESENT ? " extension unavailable" : "");
    return 77;
  }

  PFN_vkDestroyInstance destroy_instance = (PFN_vkDestroyInstance)gipa(instance, "vkDestroyInstance");
  PFN_vkCreateDebugUtilsMessengerEXT create_messenger =
      (PFN_vkCreateDebugUtilsMessengerEXT)gipa(instance, "vkCreateDebugUtilsMessengerEXT");
  PFN_vkDestroyDebugUtilsMessengerEXT destroy_messenger =
      (PFN_vkDestroyDebugUtilsMessengerEXT)gipa(instance, "vkDestroyDebugUtilsMessengerEXT");
  PFN_vkSubmitDebugUtilsMessageEXT submit =
      (PFN_vkSubmitDebugUtilsMessageEXT)gipa(instance, "vkSubmitDebugUtilsMessageEXT");
  if (!destroy_instance || !create_messenger || !destroy_messenger || !submit) {
    destroy_instance(instance, 0);
    return 77;
  }

  struct State state = {0};
  struct VkDebugUtilsMessengerCreateInfoEXT ci = {
      .sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
      .messageSeverity = filter_miss ? VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT
                                     : VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT,
      .messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT,
      .pfnUserCallback = callback,
      .pUserData = &state,
  };
  VkDebugUtilsMessengerEXT messenger = 0;
  vr = create_messenger(instance, &ci, 0, &messenger);
  if (vr != VK_SUCCESS) return 2;
  fputs("MARK registered\n", stderr);

  if (!no_submit) {
    struct VkDebugUtilsMessengerCallbackDataEXT data = {
        .sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CALLBACK_DATA_EXT,
        .pMessageIdName = "FEX_REPRO",
        .messageIdNumber = 1,
        .pMessage = "fex-debug-utils-repro",
    };
    fputs("MARK submit-enter\n", stderr);
    submit(instance, VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT,
           VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT, &data);
    fprintf(stderr, "MARK submit-return matched=%u\n", state.matched);
  }

  destroy_messenger(instance, messenger, 0);
  destroy_instance(instance, 0);

  const uint32_t expected = (no_submit || filter_miss || expect_suppressed) ? 0u : 1u;
  if (state.matched != expected) {
    fprintf(stderr, "FAIL expected=%u actual=%u\n", expected, state.matched);
    return 10;
  }
  fprintf(stderr, "PASS debug_utils matched=%u\n", state.matched);
  return 0;
}
