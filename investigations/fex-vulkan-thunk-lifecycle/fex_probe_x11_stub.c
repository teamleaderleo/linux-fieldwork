/*
 * Headless fixture for the hosted FEX Vulkan callback probe.
 *
 * FEX's Vulkan guest thunk resolves these three X11 symbols during DSO init
 * even when the test never uses X11 WSI. The callback probe only needs valid
 * guest function addresses so the host-side trampoline setup can complete.
 * Any actual X11 use is outside this fixture's contract.
 */

typedef struct _XDisplay Display;
typedef struct {
  long opaque[16];
} XVisualInfo;

int XSync(Display *display, int discard) {
  (void)display;
  (void)discard;
  return 0;
}

XVisualInfo *XGetVisualInfo(Display *display, long mask, XVisualInfo *template_info, int *count) {
  (void)display;
  (void)mask;
  (void)template_info;
  if (count) {
    *count = 0;
  }
  return (XVisualInfo *)0;
}

char *XDisplayString(Display *display) {
  (void)display;
  return (char *)0;
}
