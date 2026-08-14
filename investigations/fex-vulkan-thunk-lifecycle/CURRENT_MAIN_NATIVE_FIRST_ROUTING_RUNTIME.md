# Current-main native-validity-first Vulkan routing proof

## Scope

This checkpoint tests one combined Vulkan proc-address routing design against three already-demonstrated current-FEX defects:

1. dynamic `vkCreateDebugReportCallbackEXT` lookup escaping to native ARM and SIGILLing when the host calls the x86 guest callback;
2. the analogous dynamic `vkCreateDebugUtilsMessengerEXT` callback escape;
3. NULL-instance `vkGetInstanceProcAddr` overexposing non-global commands such as `vkGetDeviceProcAddr` and `vkCreateDevice`.

Exact FEX product source: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

Owned-FEX carrier branch: `ci/agent-b-native-first-current-main-v2-20260814`.

Carrier lineage:

```text
a3483bf ci: run native-first Vulkan routing matrix v2
7aa742b ci: add native-first Vulkan diagnostic patcher
f3ab82a Merge pull request #5823 from Sonicadvance1/202
```

Before applying the diagnostic, `git diff --name-only f3ab82... -- ThunkLibs FEXCore Source` was empty.

Workflow run: `31775535459`.
Job: `94690097060`.
Artifact: `9209807087`, `agent-b-native-first-current-main-v2-31775535459`.
Artifact digest: `sha256:753d9861816d5651cfae7d3d37b11cf7be8cecfa8d29cedcebea97922f74f974`.
Runner: GitHub hosted `ubuntu-24.04-arm`.
Workflow: https://redirect.github.com/teamleaderleo/FEX/actions/runs/31775535459

This is diagnostic research code in an owned fork. It is not upstream-submittable FEX contribution code.

## Diagnostic design

The candidate makes proc-address routing native-validity-first:

- host `vkGetInstanceProcAddr` asks the native Vulkan loader first;
- host `vkGetDeviceProcAddr` asks the native Vulkan loader first;
- if the native query returns `NULL`, FEX returns `NULL` immediately;
- only after a non-NULL native result does FEX substitute a custom host wrapper;
- `LookupCustomVulkanFunction()` gains the three already-existing custom callback functions which were missing from the hand-maintained table:
  - `vkCreateDebugReportCallbackEXT`
  - `vkDestroyDebugReportCallbackEXT`
  - `vkCreateDebugUtilsMessengerEXT`
- guest `vkGetInstanceProcAddr` also performs the packed host query before selecting its local guest wrapper for `vkGetDeviceProcAddr` or `vkGetInstanceProcAddr` itself.

The candidate does **not** change FEX's existing callback policy. The existing custom debug-report/debug-utils create wrappers still replace the guest callback with a dummy host callback, so expected callback count through those wrappers is zero.

## Native controls

All native controls pass:

```text
native_report=0
native_utils=0
native_null=0
```

The report and utils probes both deliver native callbacks as expected. The NULL-instance GIPA probe matches Vulkan's command-level table.

## Pristine current-main baseline

One run reproduces all three current defects:

```text
base_report_direct=0
base_report_gipa=132
base_utils_direct=0
base_utils_gipa=132
base_null=29
```

Interpretation:

- direct debug-report wrapper: normal return with callback suppression;
- dynamic debug-report lookup: SIGILL 132;
- direct debug-utils wrapper: normal return with callback suppression;
- dynamic debug-utils lookup: SIGILL 132;
- NULL-instance proc-address matrix: semantic failure exit 29.

This is a particularly useful negative control because direct custom entrypoints already work while only the dynamic routing path fails.

## Candidate result

The same current-main build with only the runtime-applied diagnostic gives:

```text
cand_report=0
cand_utils=0
cand_null=0
```

Debug-report dynamic path reaches normal completion:

```text
CREATE_INSTANCE kind=report lookup=gipa result=0 instance=<non-null>
PROC create=<guest-callable> fire=<guest-callable>
CREATE_CALLBACK result=0 callback=<non-null>
AFTER_FIRE callback_count=0 expected=0
PROBE_FINISH callback_count=0 status=0
```

Debug-utils dynamic path likewise reaches normal completion:

```text
CREATE_INSTANCE kind=utils lookup=gipa result=0 instance=<non-null>
PROC create=<guest-callable> fire=<guest-callable>
CREATE_MESSENGER result=0 messenger=<non-null>
AFTER_FIRE callback_count=0 expected=0
PROBE_FINISH callback_count=0 status=0
```

The NULL-instance table is repaired simultaneously:

```text
NULL_GIPA name=vkGetDeviceProcAddr ptr=(nil)
NULL_GIPA name=vkCreateInstance ptr=<non-null>
NULL_GIPA name=vkEnumerateInstanceExtensionProperties ptr=<non-null>
NULL_GIPA name=vkCreateDevice ptr=(nil)
NULL_GIPA name=vkCreateDebugUtilsMessengerEXT ptr=(nil)
NULL_GIPA_RESULT bad=0
```

## What this proves

For exact current FEX `f3ab82...`, native-validity-first routing plus the missing custom registrations simultaneously:

- removes the debug-report dynamic callback SIGILL;
- removes the debug-utils dynamic callback SIGILL;
- preserves the existing FEX dummy-callback/suppression policy for those custom wrappers;
- restores the tested NULL-instance GIPA command-level semantics.

This is materially stronger than the earlier single-function lookup candidate because it validates one routing rule across both callback extension families and an independent Vulkan proc-address semantic matrix.

## Remaining scope

This does **not** solve or test:

- the separate multi-instance first-instance native-slot reuse finding;
- callback-bearing `vkCreateInstance::pNext` paths such as debug-utils or direct-driver-loading;
- `VkAllocationCallbacks` support;
- guest thunk unload/lifetime failures;
- whether native-validity-first is sufficient for every Vulkan core/extension/instance/device command combination.

The multi-instance slot result in particular remains independent: a function may be valid for instance B yet FEX can still retain native dispatch state initially populated from instance A.

## Design conclusion

The current evidence now strongly favors this ordering invariant for FEX Vulkan proc-address routing:

> Native Vulkan validity first; FEX wrapper substitution second.

Custom-first lookup is not just unsafe for callback routing. It can also manufacture non-NULL command availability where the native Vulkan loader says the command is invalid for the supplied dispatch context.

No upstream interaction was performed. All mutation and CI execution stayed in owned repositories/forks; upstream FEX remained read-only.