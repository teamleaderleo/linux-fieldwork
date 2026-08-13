#define _GNU_SOURCE

#include <dlfcn.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

typedef int (*unpacker_fn)(uintptr_t target, int value);
typedef int (*host_callback_fn)(int value);

struct callback_slot {
  uintptr_t guest_unpacker;
  uintptr_t guest_target;
  uint64_t generation;
  bool valid;
};

static struct callback_slot raw_slot;
static struct callback_slot guarded_slot;
static uint64_t live_generation;

static int raw_callback(int value) {
  unpacker_fn unpacker = (unpacker_fn)raw_slot.guest_unpacker;
  return unpacker(raw_slot.guest_target, value);
}

static int guarded_callback(int value) {
  if (!guarded_slot.valid ||
      guarded_slot.generation != live_generation) {
    return -7777;
  }

  unpacker_fn unpacker = (unpacker_fn)guarded_slot.guest_unpacker;
  return unpacker(guarded_slot.guest_target, value);
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

static int child_call(host_callback_fn callback) {
  pid_t child = fork();
  if (child == 0) {
    int result = callback(3);
    fprintf(stderr, "child result=%d\n", result);
    _exit(0);
  }

  int status;
  waitpid(child, &status, 0);
  if (WIFSIGNALED(status)) {
    return -WTERMSIG(status);
  }
  return WEXITSTATUS(status);
}

static void run_pinning_test(void) {
  uintptr_t target;
  uintptr_t unpacker;

  puts("[pinning]");

  void *ordinary = load_guest("./libguest_v1.so", &target, &unpacker);
  void *pin = dlopen("./libguest_v1.so", RTLD_NOW | RTLD_LOCAL);
  if (!pin) {
    fprintf(stderr, "pin dlopen: %s\n", dlerror());
    exit(2);
  }

  raw_slot = (struct callback_slot) {
    .guest_unpacker = unpacker,
    .guest_target = target,
    .generation = 1,
    .valid = true,
  };

  printf("before-close result=%d mapped=%d\n",
         raw_callback(3),
         maps_contains("libguest_v1.so"));

  dlclose(ordinary);

  printf("after-ordinary-close result=%d mapped=%d\n",
         raw_callback(3),
         maps_contains("libguest_v1.so"));

  dlclose(pin);

  printf("after-pin-release mapped=%d stale-child=%d\n",
         maps_contains("libguest_v1.so"),
         child_call(raw_callback));
}

static void run_invalidation_only_test(void) {
  uintptr_t target;
  uintptr_t unpacker;

  puts("[invalidation-only]");

  void *handle = load_guest("./libguest_v1.so", &target, &unpacker);
  raw_slot = (struct callback_slot) {
    .guest_unpacker = unpacker,
    .guest_target = target,
    .generation = 2,
    .valid = true,
  };

  /*
   * Imagine the lookup-table entry is erased here. The already-published host
   * function pointer and its instance data still exist, represented by
   * raw_callback + raw_slot.
   */
  bool cache_entry_present = false;
  (void)cache_entry_present;

  dlclose(handle);

  printf("cache-erased-but-published-pointer stale-child=%d\n",
         child_call(raw_callback));
}

static void run_generation_guard_test(void) {
  uintptr_t target_v1;
  uintptr_t unpacker_v1;

  puts("[generation-guard]");

  void *handle_v1 = load_guest("./libguest_v1.so",
                               &target_v1,
                               &unpacker_v1);

  live_generation = 10;
  guarded_slot = (struct callback_slot) {
    .guest_unpacker = unpacker_v1,
    .guest_target = target_v1,
    .generation = live_generation,
    .valid = true,
  };

  printf("live result=%d\n", guarded_callback(3));

  dlclose(handle_v1);
  guarded_slot.valid = false;
  live_generation++;

  printf("after-unload guarded-result=%d\n",
         guarded_callback(3));

  uintptr_t target_v2;
  uintptr_t unpacker_v2;
  void *handle_v2 = load_guest("./libguest_v1.so",
                               &target_v2,
                               &unpacker_v2);

  printf("after-reload same-address-pair=%d guarded-old-result=%d\n",
         target_v1 == target_v2 && unpacker_v1 == unpacker_v2,
         guarded_callback(3));

  dlclose(handle_v2);
}

int main(void) {
  run_pinning_test();
  run_invalidation_only_test();
  run_generation_guard_test();
  return 0;
}
