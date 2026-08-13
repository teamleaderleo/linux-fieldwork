/*
 * Headless test fixture for FEX's Vulkan guest initializer.
 *
 * The Vulkan guest thunk eagerly resolves these three libX11 symbols during
 * initialization. Callback/proc-address probes do not call them; they only
 * need non-null guest function addresses so FEX can build the corresponding
 * trampolines and reach the Vulkan code under test.
 */

int XSync(void *display, int discard) {
  (void)display;
  (void)discard;
  return 0;
}

void *XGetVisualInfo(void *display, long mask, void *template_info, int *count) {
  (void)display;
  (void)mask;
  (void)template_info;
  if (count) {
    *count = 0;
  }
  return 0;
}

char *XDisplayString(void *display) {
  static char empty[] = "";
  (void)display;
  return empty;
}
