# FEX Vulkan maintainer question bank

Internal preparation only. This is not an upstream draft and grants no authority for upstream interaction.

## Current decision boundary

Finding A now has a clean hosted ARM64 baseline/candidate runtime differential on exact FEX `71afe476751deac24adabd1adb575fd2337b6e0a`:

- direct debug-report/debug-utils callback creation through exported symbols succeeds and the existing custom wrappers suppress guest callbacks;
- baseline dynamic creation through `vkGetInstanceProcAddr` exits `132` for both callback families;
- the native-first V3 experiment makes both dynamic cases exit `0` with guest callback count remaining zero;
- baseline proc-address semantics fail selected NULL/scope cases;
- V3 passes the retained proc-address semantics probe;
- a separate debug-utils callback route through `VkInstanceCreateInfo::pNext` still exits `132` under both baseline and V3 and is intentionally outside Finding A.

The likely maintainer-sized question is therefore:

> Should Vulkan's native `vkGetInstanceProcAddr` / `vkGetDeviceProcAddr` result decide whether a command is available before FEX substitutes an existing custom host implementation?

The internal investigation knows much more than this question requires. Keep the extra material available for review questions rather than leading with it.

## Why not just add the three missing names?

### Short answer

Adding the names proves the immediate callback-routing diagnosis and is the smallest causal edit. Native-first gating additionally preserves Vulkan's own NULL/scope decision before substituting FEX semantics.

### Evidence behind the answer

The source audit finds exactly three public callback-family `custom_host_impl` functions absent from `LookupCustomVulkanFunction()`:

- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

The existing callback wrappers exist specifically to prevent native ARM code from calling x86 guest callback pointers.

### What could change the recommendation

If maintainers deliberately want FEX's custom lookup table to define availability independently of the native loader, use the three-name repair and keep the broader proc-address policy unchanged. Ask what compatibility requirement depends on that behavior.

## Is native-first a contract repair or a contract change?

### Short answer

It is partly a cleanup of a historical FEX compromise, so do not present it as self-evidently intended behavior. The practical behavior that motivated the old compromise can still be preserved.

### Historical context

The 2023 proc-address refactor (`c10402f4f9d589209b70b250cd94a1a98c55a7c7`, from the work reviewed in `https://redirect.github.com/FEX-Emu/FEX/pull/3307`) deliberately reused a common custom-function list for GIPA/GDPA while 32-bit Vulkan was still being brought up. The PR text notes that returning device-related functions through GIPA was easier to maintain.

Current Vulkan rules allow a real-instance GIPA query to return core dispatchable commands and available device-extension commands. The problematic broadening is in cases where native Vulkan returns NULL, such as NULL-instance non-global queries or GDPA requests outside device-command scope.

### Compatibility test to retain

With a real `VkInstance`, verify that:

- `gipa(instance, "vkCreateDevice")` remains non-NULL;
- `gipa(instance, "vkGetDeviceProcAddr")` remains non-NULL.

These directly test that native-first does not lose the useful behavior the 2023 bring-up compromise was protecting.

## Why does Guest.cpp need to change?

### Short answer

Current guest GIPA fabricates the guest `vkGetDeviceProcAddr` wrapper before asking the host/native lookup path whether that name is valid for the supplied instance.

A host-only native-first patch therefore cannot preserve native NULL semantics for `vkGetDeviceProcAddr`. The guest special case needs to run after the host/native availability query.

### Regression cases

- `gipa(NULL, "vkGetDeviceProcAddr")` -> NULL
- `gipa(instance, "vkGetDeviceProcAddr")` -> non-NULL
- `gipa(instance, "vkGetInstanceProcAddr")` -> non-NULL

## Does native-first add overhead?

### Short answer

Yes. Custom names that previously short-circuited in FEX now perform one native proc-address query before substitution.

### Why the trade may be acceptable

Proc-address queries are normally loader/setup work rather than a per-draw hot path, and every current custom wrapper ultimately relies on native Vulkan functionality anyway. The native query also becomes the authoritative availability/scope check.

### What to measure if maintainers care

A small GIPA/GDPA microbenchmark can quantify the incremental lookup cost. Do not claim zero performance effect without measuring it.

## Why include `vkDestroyDebugReportCallbackEXT` if the crash is on create?

### Short answer

It is independently declared `custom_host_impl` and omitted from the same dynamic substitution registry, so it belongs to the source mismatch inventory.

### Important limit

Do not use the create-callback runtime differential as proof of allocator/destruction behavior. Non-null `VkAllocationCallbacks` and teardown semantics need separate evidence.

## Why is `vkDestroyDebugUtilsMessengerEXT` absent from the three-name set?

It is not marked `custom_host_impl` in the current Vulkan interface. Do not mechanically add it to the custom substitution map without a separate source/behavior reason.

## Why not generate the custom substitution registry now?

### Short answer

Generation is a credible follow-up, not required to close the immediate correctness defect.

The generator already knows which functions are `custom_host_impl`, but generic metadata does not encode full Vulkan global/instance/device lookup scope. Native-first gating substantially simplifies a future generated registry because native Vulkan can remain the scope/availability authority and generated metadata only needs to select the FEX implementation.

### Downside of doing it now

It expands a focused Vulkan crash fix into generator ownership and generated-output review. Recent FEX crash fixes often stay local when a local owner is sufficient.

## Why not add a new `dynamic_lookup_substitute` annotation?

It would make intent explicit but introduces another independently maintained inventory. Unless a mechanical check derives or validates it, the project can recreate the same drift class under a new name.

## Why not fix real Vulkan debug callback delivery instead of suppressing callbacks?

### Short answer

That is a larger capability change and is coupled to callback/trampoline lifetime.

The 2022 debug-report workaround (`https://redirect.github.com/FEX-Emu/FEX/pull/1803`) intentionally suppresses guest debug callbacks. Its discussion expected future generic callback support to make the workaround removable.

Generic callback support later landed (`https://redirect.github.com/FEX-Emu/FEX/pull/1868`), but Vulkan's callback pointers are embedded in create-info structures. Proper support would require coordinated guest-side trampoline creation, structure-member marshaling, and lifetime/destruction handling.

Finding B is currently investigating retained guest-address lifetime across thunk unload. Introducing more host-callable trampolines that retain guest unpacker/target addresses before that lifecycle is understood would mix two problems.

The routing fix remains necessary even if proper callback delivery is implemented later: dynamically queried commands still need to reach whichever FEX implementation owns their semantics.

## What is the debug-utils `pNext` sibling?

### Short answer

It is a separate callback escape path that does not involve proc-address lookup.

Current `vkCreateInstance` handling suppresses the old debug-report callback create-info from the instance `pNext` chain but does not equivalently suppress `VkDebugUtilsMessengerCreateInfoEXT`.

A focused probe puts a debug-utils messenger create-info in `VkInstanceCreateInfo::pNext` and triggers a validation callback during `vkCreateInstance`. Native ARM invokes the callback; both FEX baseline and V3 exit `132`.

### Why keep it separate from Finding A

V3 fixes dynamic GIPA/GDPA routing and intentionally leaves this path unchanged. Combining them would make it harder to tell which source change owns which runtime result.

## How might the `pNext` sibling be fixed?

Two plausible project-style options:

1. extend the existing debug-report suppression workaround symmetrically to debug-utils;
2. sanitize a copied create-info/pNext representation rather than mutating caller-owned const input.

The first is much smaller and matches the accepted 2022 workaround style. The second is cleaner in isolation but requires generic pNext-chain copying/repacking and broadens review substantially.

### Edge case to test

The existing linked-list deletion loop can skip consecutive targeted nodes after relinking. Test adjacent debug-report and debug-utils callback-create nodes before treating the symmetric deletion edit as complete.

## Why not clean up the four X11/Xcb duplicate GIPA queries in the same patch?

Native-first already obtains the native PFN, so reusing it is a sensible local cleanup and the V3 experiment does so.

It is not required for correctness. If maintainers prefer a smaller review surface, keep the existing requery code in the first human patch and make reuse a follow-up.

## What should the regression stack contain?

A useful layered set is:

1. proc-address semantics: native NULL remains NULL; valid real-instance queries remain non-NULL; GIPA-self/GDPA special cases work;
2. direct-vs-dynamic callback routing: direct custom wrapper succeeds, baseline dynamic path fails, repaired dynamic path reaches custom semantics;
3. debug-report and debug-utils sibling coverage;
4. optional mechanical registry completeness check for future drift;
5. existing broader `vulkaninfo` integration coverage as a final end-to-end guard.

Do not make the large Fieldwork harness itself the upstream test requirement. It is evidence used to derive smaller tests.

## What does the hosted runtime differential actually prove?

On public ARM64 with llvmpipe, the retained matrix demonstrates that the baseline dynamic report/utils paths exit `132` while direct custom-wrapper paths survive, and that the V3 native-first candidate makes both dynamic paths survive with callback count remaining zero. The same candidate passes the retained proc-address NULL/scope probe.

It does not prove:

- non-null allocator behavior;
- 32-bit runtime behavior;
- every Vulkan loader/ICD's implementation quirks;
- repeated/multi-instance/device lookup behavior;
- the separate debug-utils instance-pNext path;
- Finding B's unload-lifetime mechanism.

## Is 32-bit covered?

The source/generator audit finds the same three common callback omissions for 32- and 64-bit thunk generation, while the 32-bit-only custom functions are otherwise present in the handwritten lookup registry.

Runtime A/B evidence is currently strongest for x86-64 guest on ARM64. A 32-bit runtime check is useful if cheap, but the existing 64-bit callback differential plus common source omission already establishes Finding A's immediate mechanism.

## What would make us abandon native-first?

Reconsider if any of these appear:

- a documented FEX compatibility requirement depends on returning a custom PFN where native GIPA/GDPA returns NULL;
- a valid real-instance custom device query becomes unavailable under native-first;
- a real loader exposes a required FEX custom command only through the current pre-native shortcut;
- native-first breaks repeated/multi-object setup because of FEX's loader-slot refresh behavior;
- maintainers explicitly prefer the narrow three-name repair and want proc-address policy left unchanged.

## Finding B: is the 15/15 lifetime design the obvious fix?

No.

The adversarial lifetime model says a host-owned indirection/generation/execution-lease design is complete **if real guest thunk unload/reload must be supported after FEX-owned bridges are published**. The real FEX runtime still lacks the decisive legal live-owner post-unload dispatch trace.

First ask the project-policy question:

> Are guest thunk DSOs intended to unload/reload after they publish dynamic-PFN or callback bridges, or may those DSOs become process-lifetime residents?

If process-lifetime residency is acceptable, pinning is a much smaller policy with memory/destructor/reinitialization tradeoffs. If unload/reload is supported, stale bridge retirement belongs in a generic/core owner and needs generation/quiescence/overlap handling.

Do not let a synthetic model outrank the missing runtime ownership fact.

## What is the strongest missing Finding B evidence?

A retained legal runtime trace of:

```text
REGISTER host_pfn=H -> guest_target=T
UNMAP guest thunk range containing T
CUSTOMIR HIT H -> T after unload
FAULT at unmapped T
```

A fault at the old target without the post-unload CustomIR hit would redirect the immediate-cause diagnosis toward a stale direct guest pointer, callback trampoline, or code-cache path.

## Conversation posture

Know the full investigation, but optimize the public conversation for the maintainer's next decision.

Useful opening facts:

```text
observable failure
smallest source ownership bug
why the proposed boundary matches Vulkan/FEX behavior
one distinguishing baseline/candidate result
one intentional non-goal
```

Keep exact CI runs, fixture history, discarded candidates, branch rewrites, and unrelated sibling findings available as backup unless the maintainer asks.

If a maintainer says the project intentionally preserves a broader contract than Vulkan's native proc-address behavior, treat that as new evidence and narrow the proposal rather than defending invested work.
