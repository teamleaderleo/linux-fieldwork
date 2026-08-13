#define _GNU_SOURCE
#include <dlfcn.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* Minimal Vulkan ABI declarations: no Vulkan SDK/headers are required. */
typedef uint32_t VkFlags;
typedef uint32_t VkBool32;
typedef int32_t VkResult;
typedef uint32_t VkStructureType;
typedef struct VkInstance_T *VkInstance;
typedef uint64_t VkDebugReportCallbackEXT;
typedef VkFlags VkDebugReportFlagsEXT;
typedef int32_t VkDebugReportObjectTypeEXT;
typedef void (*PFN_vkVoidFunction)(void);

#define VK_SUCCESS 0
#define VK_ERROR_EXTENSION_NOT_PRESENT (-7)
#define VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO 1u
#define VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT 1000011000u
#define VK_DEBUG_REPORT_WARNING_BIT_EXT 0x00000002u
#define VK_DEBUG_REPORT_ERROR_BIT_EXT   0x00000008u
#define VK_DEBUG_REPORT_OBJECT_TYPE_UNKNOWN_EXT 0
#define VK_FALSE 0u
#define VK_EXT_DEBUG_REPORT_EXTENSION_NAME "VK_EXT_debug_report"

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

typedef VkBool32 (*PFN_vkDebugReportCallbackEXT)(
    VkDebugReportFlagsEXT,
    VkDebugReportObjectTypeEXT,
    uint64_t,
    size_t,
    int32_t,
    const char *,
    const char *,
    void *);

struct VkDebugReportCallbackCreateInfoEXT {
  VkStructureType sType;
  const void *pNext;
  VkDebugReportFlagsEXT flags;
  PFN_vkDebugReportCallbackEXT pfnCallback;
  void *pUserData;
};

typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(VkInstance, const char *);
typedef VkResult (*PFN_vkCreateInstance)(const struct VkInstanceCreateInfo *, const void *, VkInstance *);
typedef void (*PFN_vkDestroyInstance)(VkInstance, const void *);
typedef VkResult (*PFN_vkCreateDebugReportCallbackEXT)(VkInstance, const struct VkDebugReportCallbackCreateInfoEXT *, const void *, VkDebugReportCallbackEXT *);
typedef void (*PFN_vkDestroyDebugReportCallbackEXT)(VkInstance, VkDebugReportCallbackEXT, const void *);
typedef void (*PFN_vkDebugReportMessageEXT)(VkInstance, VkDebugReportFlagsEXT, VkDebugReportObjectTypeEXT, uint64_t, size_t, int32_t, const char *, const char *);

static const uint64_t MAGIC = UINT64_C(0x4658454452505431); /* "FXEDRPT1" */
static const char PREFIX[] = "fex-repro";
static const char MESSAGE[] = "debug-report-roundtrip";

struct State {
  uint64_t magic;
  volatile uint32_t matched;
  volatile uint32_t bad_userdata;
};

__attribute__((noinline,used))
static VkBool32 report_callback_body(VkDebugReportFlagsEXT flags,
                                     VkDebugReportObjectTypeEXT object_type,
                                     uint64_t object,
                                     size_t location,
                                     int32_t message_code,
                                     const char *layer_prefix,
                                     const char *message,
                                     void *user_data) {
  (void)object_type;
  (void)object;
  (void)location;
  (void)message_code;
  struct State *state = (struct State *)user_data;
  if (!state || state->magic != MAGIC) {
    static const char bad[] = "CALLBACK debug_report BAD_USERDATA\n";
    (void)write(STDERR_FILENO, bad, sizeof(bad) - 1);
    if (state) state->bad_userdata++;
    return VK_FALSE;
  }

  if ((flags & VK_DEBUG_REPORT_WARNING_BIT_EXT) &&
      layer_prefix && message &&
      strcmp(layer_prefix, PREFIX) == 0 && strcmp(message, MESSAGE) == 0) {
    state->matched++;
    static const char hit[] = "CALLBACK debug_report MATCH\n";
    (void)write(STDERR_FILENO, hit, sizeof(hit) - 1);
  }
  return VK_FALSE;
}

/*
 * First five x86 bytes are E9 00 00 00 00: a harmless x86 jmp +0.
 * A raw little-endian AArch64 entry at this address decodes its first word as
 * 0x000000e9, which is undefined. This makes host execution of the guest
 * callback fail as SIGILL at a deterministic boundary.
 */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
__attribute__((naked,noinline))
static VkBool32 report_callback(VkDebugReportFlagsEXT flags,
                                VkDebugReportObjectTypeEXT object_type,
                                uint64_t object,
                                size_t location,
                                int32_t message_code,
                                const char *layer_prefix,
                                const char *message,
                                void *user_data) {
  __asm__ volatile(
      ".byte 0xe9,0x00,0x00,0x00,0x00\n\t"
      "jmp report_callback_body\n\t");
}
#pragma GCC diagnostic pop

static void *must_dlopen_vulkan(void) {
  void *h = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!h) fprintf(stderr, "SKIP dlopen libvulkan.so.1: %s\n", dlerror());
  return h;
}

static int is_arg(int argc, char **argv, const char *needle) {
  for (int i = 1; i < argc; ++i) if (strcmp(argv[i], needle) == 0) return 1;
  return 0;
}

int main(int argc, char **argv) {
  const int export_create = is_arg(argc, argv, "--create=export");
  const int no_submit = is_arg(argc, argv, "--no-submit");
  const int filter_miss = is_arg(argc, argv, "--filter-miss");
  const int expect_suppressed = is_arg(argc, argv, "--expect=suppressed");

  setvbuf(stderr, NULL, _IONBF, 0);
  fprintf(stderr, "CASE debug_report create=%s submit=%s filter=%s\n",
          export_create ? "export" : "gipa",
          no_submit ? "no" : "yes",
          filter_miss ? "miss" : "match");
  fprintf(stderr, "EXPECT callback=%s\n", expect_suppressed ? "suppressed" : "delivered");
  fprintf(stderr, "GUEST_CALLBACK=0x%" PRIxPTR "\n", (uintptr_t)report_callback);

  void *vulkan = must_dlopen_vulkan();
  if (!vulkan) return 77;

  PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(vulkan, "vkGetInstanceProcAddr");
  PFN_vkCreateInstance create_instance = (PFN_vkCreateInstance)dlsym(vulkan, "vkCreateInstance");
  if (!gipa || !create_instance) {
    fprintf(stderr, "SKIP core Vulkan symbols unavailable\n");
    return 77;
  }

  const char *extensions[] = {VK_EXT_DEBUG_REPORT_EXTENSION_NAME};
  const struct VkInstanceCreateInfo ici = {
      .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
      .enabledExtensionCount = 1,
      .ppEnabledExtensionNames = extensions,
  };
  VkInstance instance = NULL;
  VkResult vr = create_instance(&ici, NULL, &instance);
  if (vr != VK_SUCCESS) {
    fprintf(stderr, "SKIP vkCreateInstance result=%d%s\n", vr,
            vr == VK_ERROR_EXTENSION_NOT_PRESENT ? " (extension unavailable)" : "");
    return 77;
  }

  PFN_vkDestroyInstance destroy_instance = (PFN_vkDestroyInstance)gipa(instance, "vkDestroyInstance");
  PFN_vkCreateDebugReportCallbackEXT create_cb = export_create
      ? (PFN_vkCreateDebugReportCallbackEXT)dlsym(vulkan, "vkCreateDebugReportCallbackEXT")
      : (PFN_vkCreateDebugReportCallbackEXT)gipa(instance, "vkCreateDebugReportCallbackEXT");
  PFN_vkDestroyDebugReportCallbackEXT destroy_cb =
      (PFN_vkDestroyDebugReportCallbackEXT)gipa(instance, "vkDestroyDebugReportCallbackEXT");
  PFN_vkDebugReportMessageEXT submit =
      (PFN_vkDebugReportMessageEXT)gipa(instance, "vkDebugReportMessageEXT");

  fprintf(stderr, "CREATE_PTR=0x%" PRIxPTR " route=%s\n",
          (uintptr_t)create_cb, export_create ? "export" : "gipa");
  if (!create_cb || !destroy_cb || !submit || !destroy_instance) {
    fprintf(stderr, "SKIP extension entry point unavailable (create=%p destroy=%p submit=%p)\n",
            (void *)create_cb, (void *)destroy_cb, (void *)submit);
    destroy_instance(instance, NULL);
    return 77;
  }

  struct State state = {.magic = MAGIC};
  const struct VkDebugReportCallbackCreateInfoEXT ci = {
      .sType = VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT,
      .flags = filter_miss ? VK_DEBUG_REPORT_ERROR_BIT_EXT : VK_DEBUG_REPORT_WARNING_BIT_EXT,
      .pfnCallback = report_callback,
      .pUserData = &state,
  };
  VkDebugReportCallbackEXT callback = 0;
  vr = create_cb(instance, &ci, NULL, &callback);
  if (vr != VK_SUCCESS) {
    fprintf(stderr, "FAIL vkCreateDebugReportCallbackEXT result=%d\n", vr);
    destroy_instance(instance, NULL);
    return 2;
  }
  fprintf(stderr, "MARK registered\n");

  if (!no_submit) {
    fprintf(stderr, "MARK submit-enter\n");
    submit(instance,
           VK_DEBUG_REPORT_WARNING_BIT_EXT,
           VK_DEBUG_REPORT_OBJECT_TYPE_UNKNOWN_EXT,
           0, 0, 0x669,
           PREFIX, MESSAGE);
    fprintf(stderr, "MARK submit-return matched=%u bad_userdata=%u\n",
            state.matched, state.bad_userdata);
  }

  destroy_cb(instance, callback, NULL);
  destroy_instance(instance, NULL);
  /* Intentionally keep libvulkan resident: loader dlclose is a separate FEX finding. */

  const uint32_t expected = (no_submit || filter_miss || expect_suppressed) ? 0u : 1u;
  if (state.bad_userdata != 0 || state.matched != expected) {
    fprintf(stderr, "FAIL expected_matched=%u actual=%u bad_userdata=%u\n",
            expected, state.matched, state.bad_userdata);
    return 10;
  }
  fprintf(stderr, "PASS debug_report matched=%u\n", state.matched);
  return 0;
}
