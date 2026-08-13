#include <stdint.h>

#ifndef GEN
#define GEN 1
#endif

__attribute__((visibility("default")))
int guest_target(int value) {
  return GEN * 1000 + value;
}

__attribute__((visibility("default")))
int guest_unpacker(uintptr_t target, int value) {
  int (*function)(int) = (int (*)(int))target;
  return function(value) + GEN * 10;
}
