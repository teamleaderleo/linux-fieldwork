# NODELETE Vulkan constructor churn runtime

Date: 2026-08-14

## Question

Does repeated logical `dlclose()` / reopen of a NODELETE guest thunk keep one guest-wrapper generation alive, or does the guest constructor/`OnInit()` path rerun on every reopen while the mappings merely remain resident?

This matters because rerunning guest initialization against already-persistent FEX host-thunk state would preserve a generation mismatch even if executable bytes stayed mapped.

## Test

Owned FEX branch: `diagnostic/nodelete-loadlib-count-20260814`.

Carrier commit: `98b2cffd224a9fe75c88341efdd6510f7c7a9e47`.

Hosted ARM64 run: `31776288930`.

Artifact: `nodelete-constructor-count-31776288930`.

Artifact digest:

```text
sha256:7c2fffed212066c4adbb259c266b98f012ff776e2f3ea5e0d24d42d040ba4df6
```

The diagnostic adds a guest-visible marker at Vulkan `OnInit()` and runs the same real generated-Vulkan dynamic-PFN workload through 256 logical close/reopen cycles.

The probe repeatedly reacquires `vkEnumerateInstanceVersion`, requires the native PFN and guest invoker generation to remain stable, performs the real Lavapipe call, closes the guest Vulkan handle, then calls the original retained PFN again.

## Result

The Vulkan guest initialization marker appears exactly once:

```text
FIELDWORK_VULKAN_ONINIT
```

The artifact's explicit count is:

```text
VULKAN_ONINIT_COUNT=1
```

The runtime still completes all churn:

```text
STRESS_CYCLES=256
NODELETE_CONSTRUCTOR_COUNT_PROBE_OK
exit=0
```

Throughout the run, repeated GIPA lookup keeps publishing the same dynamic bridge pair:

```text
native H = 0x7ffff76c80f4
guest invoker T = 0x7ffff7ea4430
```

The repeated `LinkAddressToFunction(H, T)` calls therefore update/reaffirm one resident guest generation rather than registering newly constructed guest-wrapper generations.

## Meaning

For the real generated Vulkan wrapper under glibc NODELETE semantics:

```text
first dlopen
  -> constructor / OnInit runs once
  -> guest wrapper generation becomes resident

logical dlclose / reopen x256
  -> loader handle/reference semantics still operate
  -> constructor does not rerun
  -> guest executable/static generation remains the same
  -> dynamic PFN bridge target remains the same
```

This strengthens the lifetime-alignment argument for NODELETE. FEX's host thunk and native-library state already persist across guest logical close. NODELETE makes the guest wrapper behave as the same persistent generation instead of repeatedly reconstructing only the guest half.

It also removes an ambiguity in earlier wording: the proven behavior is not "finalizers run but code remains mapped." Intermediate logical close does not tear down and reconstruct the Vulkan guest wrapper; the same initialized generation survives until process teardown.

## Limits

This test is Vulkan-specific runtime evidence for constructor behavior. It does not prove that every current or future thunk has no application-visible requirement for constructor/destructor reset on logical reopen; that remains a policy audit question.

All code and CI work described here is confined to owned repositories/forks. No upstream FEX interaction occurred.
