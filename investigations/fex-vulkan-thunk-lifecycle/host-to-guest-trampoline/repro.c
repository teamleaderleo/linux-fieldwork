#define _GNU_SOURCE

#include <dlfcn.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

typedef int (*unpacker_fn)(uintptr_t target, int value);
typedef int (*host_callback_fn)(int value);

struct callback_state {
  uintptr_t guest_unpacker;
  uintptr_t guest_target;
  bool initialized;
};

static struct callback_state cached;

/*
 * Native host-callable entry point. FEX uses a generated executable trampoline;
 * this reduced test keeps the host entry point fixed and puts the remembered
 * guest addresses in process-long state so the lifetime question is isolated.
 */
static int host_callback(int value) {
  unpacker_fn unpacker = (unpacker_fn)cached.guest_unpacker;
  return unpacker(cached.guest_target, value);
}

static host_callback_fn make_host_callback(uintptr_t guest_target,
                                           uintptr_t guest_unpacker) {
  if (cached.initialized &&
      cached.guest_target == guest_target &&
      cached.guest_unpacker == guest_unpacker) {
    return host_callback;
  }

  cached = (struct callback_state) {
    .guest_unpacker = guest_unpacker,
    .guest_target = guest_target,
    .initialized = true,
  };
  return host_callback;
}

static bool maps_contains(const char *needle) {
  FILE *maps = fopen("/proc/self/maps", "r");
  if (!maps) {
    return false;
  }

  char *line = NULL;
  size_t capacity = 0;
  bool found = false;

  while (getline(&line, &capacity, maps) != -1) {
    if (strstr(line, needle)) {
      found = true;
      break;
    }
  }

  free(line);
  fclose(maps);
  return found;
}

static void copy_file(const char *source, const char *destination) {
  int input = open(source, O_RDONLY);
  if (input < 0) {
    perror(source);
    exit(2);
  }

  int output = open(destination, O_WRONLY | O_CREAT | O_TRUNC, 0755);
  if (output < 0) {
    perror(destination);
    exit(2);
  }

  char buffer[65536];
  ssize_t count;
  while ((count = read(input, buffer, sizeof(buffer))) > 0) {
    char *cursor = buffer;
    ssize_t remaining = count;
    while (remaining > 0) {
      ssize_t written = write(output, cursor, remaining);
      if (written < 0) {
        perror("write");
        exit(2);
      }
      cursor += written;
      remaining -= written;
    }
  }

  if (count < 0) {
    perror("read");
    exit(2);
  }

  close(output);
  close(input);
}

static void *load_guest(const char *path,
                        uintptr_t *guest_target,
                        uintptr_t *guest_unpacker) {
  void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
  if (!handle) {
    fprintf(stderr, "dlopen: %s\n", dlerror());
    exit(2);
  }

  *guest_target = (uintptr_t)dlsym(handle, "guest_target");
  *guest_unpacker = (uintptr_t)dlsym(handle, "guest_unpacker");
  if (!*guest_target || !*guest_unpacker) {
    fprintf(stderr, "dlsym failed\n");
    exit(2);
  }

  return handle;
}

static int stale_call_status(host_callback_fn callback) {
  pid_t child = fork();
  if (child == 0) {
    int value = callback(7);
    fprintf(stderr, "unexpected stale-call success: %d\n", value);
    _exit(0);
  }

  int status;
  waitpid(child, &status, 0);
  if (WIFSIGNALED(status)) {
    return -WTERMSIG(status);
  }
  return WEXITSTATUS(status);
}

int main(void) {
  const char *active_path = "./libguest_active.so";

  unlink(active_path);
  copy_file("./libguest_v1.so", active_path);

  uintptr_t target_v1;
  uintptr_t unpacker_v1;
  void *handle_v1 = load_guest(active_path, &target_v1, &unpacker_v1);
  host_callback_fn callback_v1 = make_host_callback(target_v1, unpacker_v1);

  printf("v1 target=%#" PRIxPTR
         " unpacker=%#" PRIxPTR
         " callback=%p result=%d\n",
         target_v1,
         unpacker_v1,
         (void *)callback_v1,
         callback_v1(7));

  printf("mapped-before-close=%d\n",
         maps_contains("libguest_active.so"));

  dlclose(handle_v1);

  printf("mapped-after-close=%d\n",
         maps_contains("libguest_active.so"));
  printf("stale-call-status=%d\n", stale_call_status(callback_v1));

  copy_file("./libguest_v2.so", active_path);

  uintptr_t target_v2;
  uintptr_t unpacker_v2;
  void *handle_v2 = load_guest(active_path, &target_v2, &unpacker_v2);
  host_callback_fn callback_v2 = make_host_callback(target_v2, unpacker_v2);

  printf("v2 target=%#" PRIxPTR
         " unpacker=%#" PRIxPTR
         " callback=%p result=%d\n",
         target_v2,
         unpacker_v2,
         (void *)callback_v2,
         callback_v2(7));

  printf("address-pair-reused=%d callback-entry-reused=%d\n",
         target_v1 == target_v2 && unpacker_v1 == unpacker_v2,
         callback_v1 == callback_v2);

  dlclose(handle_v2);
  return 0;
}
