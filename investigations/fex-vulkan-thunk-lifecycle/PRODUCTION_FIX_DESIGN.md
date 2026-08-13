# Finding A production-fix design

Exact FEX source reviewed: `71afe476751deac24adabd1adb575fd2337b6e0a`.

This note separates the causal experiment from the preferred production behavior.

## What must the fix guarantee?

1. Dynamic lookup of a callback-bearing Vulkan command must not bypass a FEX custom implementation that deliberately suppresses or repacks a guest callback.
2. `vkGetInstanceProcAddr` and `vkGetDeviceProcAddr` must preserve native Vulkan availability and command-scope behavior.
3. Disabled/unavailable commands must remain null when native Vulkan returns null.
4. The fix must cover the complete currently-missing callback family:
   - `vkCreateDebugReportCallbackEXT`
   - `vkDestroyDebugReportCallbackEXT`
   - `vkCreateDebugUtilsMessengerEXT`
5. Future `custom_host_impl` additions should have a mechanical way to detect missing dynamic substitution coverage.

## Question: why is adding three strings to the current common lookup insufficient as a final design?

`LookupCustomVulkanFunction()` is called before native Vulkan in both host-side proc-address implementations.

The lookup already contains commands with different Vulkan scopes, including `vkCreateInstance`, device commands such as `vkCreateShaderModule`, and physical-device/instance commands such as the Xlib/Xcb presentation helpers.

Because `fexfn_impl_libvulkan_vkGetDeviceProcAddr()` consults this common lookup first, a GDPA query can currently return a FEX custom pointer for a name that native GDPA would reject. Adding more instance commands to the same pre-native lookup widens that behavior.

The callback omission was exposed by dynamic GIPA, but the shared pre-native lookup also carries a command-scope correctness problem.

## Question: what is the smallest policy change that fixes both problems?

Use native Vulkan as the availability/scope authority first.

Conceptually:

```text
native = native_Get*ProcAddr(object, name)
if native == null:
    return null
custom = LookupCustomVulkanFunction(name)
if custom != null:
    return custom
return native
```

For GIPA, existing setup/reload behavior still runs before or alongside this policy as required. Where the current code requeries an instance-extension function after finding a custom wrapper, the already-obtained native PFN can be reused when equivalent.

Consequences:

- GDPA("vkCreateInstance") follows native GDPA and remains null;
- GIPA(instance, enabled callback command) can substitute the FEX callback-safe wrapper;
- GIPA/GDPA for unavailable commands remains null;
- ordinary commands preserve the native PFN;
- the common custom map no longer needs to encode Vulkan command scope to be safe.

## Question: should the three callback functions still be added to the common map?

Yes, for the minimal patch, once native-first gating is in place.

The complete causal/production candidate should add all three callback-family names. The reduced runtime probe only executes the two create paths because it exits before teardown, but source completeness requires the destroy path too.

## Question: should the custom substitution registry be generated?

Three viable ownership models exist.

### Option A — native gate + three handwritten entries

Pros:
- smallest diff;
- easiest to review;
- directly repairs the known crash family;
- fixes the existing GDPA scope leak through native gating.

Cons:
- handwritten registry drift remains possible.

Required companion test: a source invariant comparing public Vulkan `custom_host_impl` declarations with dynamic-substitution registrations.

### Option B — native gate + generated registry from `custom_host_impl`

Pros:
- removes most handwritten drift;
- generic thunk metadata already records `custom_host_impl`;
- native gating supplies command scope, so the generator does not need Vulkan instance/device metadata.

Questions/risks:
- `custom_host_impl` also marks implementation plumbing (`Vulkan_SetGuestX*`) and the proc-address functions themselves;
- generation therefore needs either an exclusion rule or a more specific annotation;
- changing generic thunk output for one Vulkan policy may be a larger review burden than the defect warrants.

Native gating makes accidental inclusion of non-Vulkan/internal names harmless at runtime because native GIPA/GDPA returns null, but generated noise still weakens clarity.

### Option C — add an explicit generator annotation for dynamic substitution

Example concept: `fexgen::dynamic_lookup_substitute` on functions that an API's proc-address path should replace with a custom host implementation.

Pros:
- precise intent;
- avoids plumbing/proc-address exemptions;
- generator can emit the registry mechanically.

Cons:
- introduces generic generator vocabulary for a policy currently needed mainly by Vulkan;
- every custom function still needs an explicit second annotation, so omissions can move from the registry to the annotation list.

### Recommendation

Land Option A first if upstream prefers a focused correctness patch: native-first GIPA/GDPA gating, all three missing callback registrations, and an invariant test.

Consider Option B only if maintainers want registry generation as a follow-up. Native-first gating is the key prerequisite that makes generation safe without Vulkan XML scope data.

## Question: what should the regression tests assert?

Use three layers.

### 1. Pure proc-address policy test

Extract or isolate the small policy so it can be tested with synthetic PFNs and no GPU:

- native null + known custom name -> null;
- native null + ordinary name -> null;
- native PFN + known custom name -> custom PFN;
- native PFN + ordinary name -> native PFN.

Include scope-representative names:

- `vkCreateInstance` through the GDPA policy with native null;
- `vkCreateShaderModule` through GDPA with native non-null;
- `vkCreateDebugReportCallbackEXT` and `vkCreateDebugUtilsMessengerEXT` through GIPA with native non-null.

This catches the ordering bug directly.

### 2. Registry completeness invariant

Compare public Vulkan `custom_host_impl` functions against the substitution registry, exempting only implementation plumbing/proc-address entrypoints that applications cannot obtain as ordinary Vulkan commands.

Current Fieldwork helper: `audit_custom_lookup.py`.

A fixed tree should report an empty missing set.

### 3. End-to-end callback routing probe

Run the reduced guest callback probe under FEX with software Vulkan:

- native control sees the callback;
- baseline direct symbol route uses the existing custom wrapper and sees zero guest callbacks;
- broken baseline dynamic GIPA crosses the wrong callback boundary;
- report-only candidate repairs report while utils remains a control;
- complete callback-family candidate repairs both report and utils.

The hosted headless fixture needs exact 64-bit thunk pairing and valid guest addresses for the Vulkan guest thunk's three X11 initialization symbols. See `HOSTED_CALLBACK_RUNTIME_BLOCKERS.md`.

## Question: does the X11 null-target assertion belong in this Finding A patch?

Keep it separate.

`Guest.cpp::OnInit()` currently assumes `libX11.so.6` and its three symbols are available and sends the results to host trampoline setup without validation. That is a real robustness question, but changing it while proving callback dispatch would add a second product behavior change to the experiment.

The headless hosted probe can satisfy the initializer with the tracked three-symbol guest fixture. A separate issue/patch can decide whether Vulkan thunk initialization should tolerate missing guest X11 at runtime.

## Question: does `VkAllocationCallbacks` belong here?

Keep it separate as well.

FEX's Vulkan custom wrappers generally suppress allocation callbacks. Supporting non-null `VkAllocationCallbacks` is a broader callback/allocator ABI problem and should not enlarge Finding A's dynamic proc-address fix.

## Merge-quality evidence target

A production candidate is ready for human review when all of these hold:

- the three-entry source mismatch is closed;
- native-first policy tests pass;
- the registry invariant reports no missing public custom substitutions;
- software-Vulkan native controls pass;
- direct FEX custom-route controls pass;
- dynamic baseline/candidate routing separates causally;
- GIPA/GDPA null/scope behavior matches native authority;
- Finding B teardown remains excluded from this probe by immediate process exit.

No FEX upstream contact has occurred.
