#include <stddef.h>

int XSync(void *display, int discard) {
  (void)display;
  (void)discard;
  return 0;
}

void *XGetVisualInfo(void *display, long mask, void *templ, int *count) {
  (void)display;
  (void)mask;
  (void)templ;
  if (count) *count = 0;
  return NULL;
}

char *XDisplayString(void *display) {
  (void)display;
  static char empty[] = "";
  return empty;
}
