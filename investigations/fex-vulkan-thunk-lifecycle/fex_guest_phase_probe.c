#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void marker(const char *text) {
  write(2, text, strlen(text));
}

int main(int argc, char **argv) {
  marker("PHASE_MAIN\n");
  if (argc == 1 || strcmp(argv[1], "plain") == 0) {
    marker("PHASE_PLAIN_EXIT\n");
    return 0;
  }
  if (strcmp(argv[1], "vulkan") != 0) {
    marker("PHASE_BAD_ARG\n");
    return 64;
  }
  marker("PHASE_BEFORE_DLOPEN\n");
  void *handle = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!handle) {
    marker("PHASE_DLOPEN_ERROR ");
    const char *error = dlerror();
    marker(error ? error : "unknown");
    marker("\n");
    return 2;
  }
  marker("PHASE_AFTER_DLOPEN\n");
  return 0;
}
