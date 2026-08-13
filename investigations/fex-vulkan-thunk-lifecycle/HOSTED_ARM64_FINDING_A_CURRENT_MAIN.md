# Hosted ARM64 Finding A reproduction on reviewed current FEX main

Date: 2026-08-14

This run closes the earlier hosted-run fixture gap and reproduces Finding A on reviewed FEX `main` at `71afe476751deac24adabd1adb575fd2337b6e0a`.

FEX upstream remained read-only. Execution happened only in the owned `teamleaderleo/FEX` fork.

Owned Actions run: `31734089156`

Artifact: `finding-a-x11-repaired-31734089156` (`9194574962`)

Artifact digest:

```text
sha256:f570580fd39a06bf8f6b418171f2f6b4a42acdfe5d67bf0199d52dcd42124deb
```

The amd64 rootfs includes the three guest X11 symbols required by Vulkan guest-thunk initialization (`XSync`, `XGetVisualInfo`, `XDisplayString`), so `dlopen("libvulkan.so.1")` succeeds before the callback A/B begins.

## Exact matrix

```text
static=0
load_vulkan=0
direct=20
gipa_baseline=132
gipa_candidate=20
```

The `20` values are a probe-expectation mismatch, not crashes. This workflow passed `positive`, which requires a guest callback count greater than zero. FEX's existing custom debug-report create wrapper intentionally replaces the guest callback with `DummyVkDebugReportCallback`, so a healthy custom route returns normally with guest callback count zero and this particular probe reports status 20.

### Direct custom route

The direct route reaches FEX's existing custom implementation, creates the callback object, fires the debug-report message, returns from the fire, and exits normally from the probe logic:

```text
CREATE_INSTANCE kind=report lookup=direct result=0
PROC create=<custom-route address> fire=<address>
CREATE_CALLBACK result=0
AFTER_FIRE callback_count=0 expected=positive
PROBE_FINISH callback_count=0 status=20
```

### Pristine dynamic GIPA route

The pristine dynamic lookup obtains a different create address, creates the callback object successfully, and then terminates with exit 132 before the `AFTER_FIRE` marker:

```text
CREATE_INSTANCE kind=report lookup=gipa result=0
PROC create=<native-route address> fire=<address>
CREATE_CALLBACK result=0
# no AFTER_FIRE
exit=132
```

### Diagnostic dynamic GIPA candidate

The local diagnostic source change adds `vkCreateDebugReportCallbackEXT` to `LookupCustomVulkanFunction()` and rebuilds only the Vulkan host thunk. With the same guest binary/rootfs/ICD, the dynamic route now creates the callback object, returns from the fire with guest callback count zero, and reaches normal probe completion:

```text
CREATE_INSTANCE kind=report lookup=gipa result=0
PROC create=<custom-route address> fire=<address>
CREATE_CALLBACK result=0
AFTER_FIRE callback_count=0 expected=positive
PROBE_FINISH callback_count=0 status=20
```

## Interpretation

The distinguishing A/B is:

```text
pristine dynamic route: successful callback creation -> signal before fire returns
candidate dynamic route: successful callback creation -> fire returns with guest callback suppressed
```

This reproduces Finding A on reviewed current FEX `main`, independently of the retained FEX-2608 / Apple-M5 runtime receipt.

A cleanup rerun should pass expected callback count `0` for the direct and candidate custom routes so those healthy cases report exit 0 instead of the harness-semantic exit 20. That cleanup does not change the causal result above.

External source identity: `https://redirect.github.com/FEX-Emu/FEX/commit/71afe476751deac24adabd1adb575fd2337b6e0a`.
