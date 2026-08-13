#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#ifndef MAP_FIXED_NOREPLACE
#define MAP_FIXED_NOREPLACE 0x100000
#endif

typedef void (*generic_fn)(void);
typedef generic_fn (*glx_get_proc_fn)(const unsigned char *);
typedef unsigned int (*gl_get_error_fn)(void);

static void dump_gl_maps(const char *tag) {
  FILE *f = fopen("/proc/self/maps", "r");
  if (!f) {
    perror("fopen /proc/self/maps");
    return;
  }

  printf("PROBE MAPS_BEGIN %s\n", tag);
  char line[1024];
  while (fgets(line, sizeof(line), f)) {
    if (strstr(line, "libGL") || strstr(line, "GuestThunks")) {
      fputs(line, stdout);
    }
  }
  printf("PROBE MAPS_END %s\n", tag);
  fclose(f);
}

static void *page_align_down(void *p, size_t page_size) {
  return (void *)((uintptr_t)p & ~((uintptr_t)page_size - 1));
}

static void *must_dlsym(void *handle, const char *name) {
  dlerror();
  void *result = dlsym(handle, name);
  const char *err = dlerror();
  if (err || !result) {
    fprintf(stderr, "PROBE FAIL dlsym %s: %s\n", name, err ? err : "null");
    exit(20);
  }
  return result;
}

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stderr, NULL, _IONBF, 0);

  const long page_size_long = sysconf(_SC_PAGESIZE);
  if (page_size_long <= 0) {
    perror("sysconf");
    return 21;
  }
  const size_t page_size = (size_t)page_size_long;

  printf("PROBE START page_size=%zu\n", page_size);

  void *h1 = dlopen("libGL.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!h1) {
    fprintf(stderr, "PROBE FAIL first dlopen: %s\n", dlerror());
    return 22;
  }

  glx_get_proc_fn get_proc_1 = (glx_get_proc_fn)must_dlsym(h1, "glXGetProcAddress");
  Dl_info info1 = {0};
  if (!dladdr((void *)get_proc_1, &info1) || !info1.dli_fbase) {
    fprintf(stderr, "PROBE FAIL first dladdr\n");
    return 23;
  }

  gl_get_error_fn pfn1 = (gl_get_error_fn)get_proc_1((const unsigned char *)"glGetError");
  if (!pfn1) {
    fprintf(stderr, "PROBE FAIL first glXGetProcAddress(glGetError) returned null\n");
    return 24;
  }

  printf("PROBE FIRST dso=%s base=%p glx_get_proc=%p native_pfn=%p\n",
         info1.dli_fname ? info1.dli_fname : "?", info1.dli_fbase, (void *)get_proc_1, (void *)pfn1);
  dump_gl_maps("before-first-call");

  unsigned int first_error = pfn1();
  printf("PROBE FIRST_CALL_OK result=0x%x\n", first_error);

  void *old_base_page = page_align_down(info1.dli_fbase, page_size);
  printf("PROBE DLCLOSE_FIRST handle=%p reserve_page=%p\n", h1, old_base_page);
  if (dlclose(h1) != 0) {
    fprintf(stderr, "PROBE FAIL first dlclose: %s\n", dlerror());
    return 25;
  }
  dump_gl_maps("after-first-dlclose");

  errno = 0;
  void *reservation = mmap(old_base_page, page_size, PROT_NONE,
                           MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
  if (reservation == MAP_FAILED) {
    fprintf(stderr, "PROBE RESERVE_FAIL page=%p errno=%d (%s)\n", old_base_page, errno, strerror(errno));
    return 26;
  }
  printf("PROBE RESERVED_OLD_BASE page=%p\n", reservation);

  void *h2 = dlopen("libGL.so.1", RTLD_NOW | RTLD_LOCAL);
  if (!h2) {
    fprintf(stderr, "PROBE FAIL second dlopen: %s\n", dlerror());
    return 27;
  }

  glx_get_proc_fn get_proc_2 = (glx_get_proc_fn)must_dlsym(h2, "glXGetProcAddress");
  Dl_info info2 = {0};
  if (!dladdr((void *)get_proc_2, &info2) || !info2.dli_fbase) {
    fprintf(stderr, "PROBE FAIL second dladdr\n");
    return 28;
  }

  gl_get_error_fn pfn2 = (gl_get_error_fn)get_proc_2((const unsigned char *)"glGetError");
  if (!pfn2) {
    fprintf(stderr, "PROBE FAIL second glXGetProcAddress(glGetError) returned null\n");
    return 29;
  }

  printf("PROBE SECOND dso=%s base=%p glx_get_proc=%p native_pfn=%p\n",
         info2.dli_fname ? info2.dli_fname : "?", info2.dli_fbase, (void *)get_proc_2, (void *)pfn2);
  printf("PROBE COMPARE base_changed=%d native_pfn_stable=%d old_base=%p new_base=%p old_pfn=%p new_pfn=%p\n",
         info1.dli_fbase != info2.dli_fbase, pfn1 == pfn2,
         info1.dli_fbase, info2.dli_fbase, (void *)pfn1, (void *)pfn2);
  dump_gl_maps("before-fresh-reload-call");

  if (info1.dli_fbase == info2.dli_fbase) {
    fprintf(stderr, "PROBE INCONCLUSIVE guest DSO reused old base despite reservation\n");
    return 30;
  }

  printf("PROBE FRESH_REACQUIRED_CALL_BEGIN pfn=%p\n", (void *)pfn2);
  unsigned int second_error = pfn2();
  printf("PROBE FRESH_REACQUIRED_CALL_OK result=0x%x\n", second_error);

  if (dlclose(h2) != 0) {
    fprintf(stderr, "PROBE FAIL second dlclose: %s\n", dlerror());
    return 31;
  }
  if (munmap(reservation, page_size) != 0) {
    perror("munmap reservation");
    return 32;
  }

  printf("PROBE PASS changed-base reload survived with freshly reacquired PFN\n");
  return 0;
}
