# Current-main NULL-instance `vkGetInstanceProcAddr` semantics

## Scope

This checkpoint tests Vulkan's `vkGetInstanceProcAddr(NULL, pName)` command-level contract on exact current FEX product source.

- FEX product source: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.
- Owned-FEX carrier branch: `ci/agent-b-null-gipa-f3ab-20260814`.
- Carrier commit: `1c1952ac4965a64ffd4cd43d9bbeb19b8961825f`.
- ARM64 workflow run: `31771309864`.
- Job: `94677664508`.
- Artifact: `9208299362`, `agent-b-null-gipa-31771309864`.
- Runner: GitHub hosted `ubuntu-24.04-arm`.
- Workflow: https://redirect.github.com/teamleaderleo/FEX/actions/runs/31771309864

The carrier contains no product-source changes under `ThunkLibs`, `FEXCore`, or `Source` relative to the exact product SHA.

## Vulkan contract

Khronos' current Vulkan specification says that when `instance` is `NULL`, `vkGetInstanceProcAddr` returns a function pointer for a global command and returns `NULL` for any case not covered by the table. The listed global commands are `vkEnumerateInstanceVersion` where available, `vkEnumerateInstanceExtensionProperties`, `vkEnumerateInstanceLayerProperties`, and `vkCreateInstance`; starting with Vulkan 1.2, `vkGetInstanceProcAddr` can also resolve itself with a `NULL` instance.

Source reviewed at Khronos Vulkan-Docs commit `090f1b190d60ced4a1d198fd3747d071cc271b1c`, `chapters/initialization.adoc`:
https://redirect.github.com/KhronosGroup/Vulkan-Docs/blob/090f1b190d60ced4a1d198fd3747d071cc271b1c/chapters/initialization.adoc

Therefore `vkGetDeviceProcAddr` and `vkCreateDevice` are not valid non-NULL results for `vkGetInstanceProcAddr(NULL, ...)`.

## Native ARM64 control

The native loader matches the specification:

```text
NULL_GIPA name=vkGetDeviceProcAddr ptr=(nil)
NULL_GIPA name=vkCreateInstance ptr=<non-null>
NULL_GIPA name=vkEnumerateInstanceExtensionProperties ptr=<non-null>
NULL_GIPA name=vkCreateDevice ptr=(nil)
NULL_GIPA name=vkCreateDebugUtilsMessengerEXT ptr=(nil)
NULL_GIPA_RESULT bad=0
```

Native exit: `0`.

## Exact-current FEX result

Exact `f3ab82...` differs in two tested non-global cases:

```text
NULL_GIPA name=vkGetDeviceProcAddr ptr=0x7ffff7ea2230
NULL_GIPA name=vkCreateInstance ptr=0x7ffff77c7bd0
NULL_GIPA name=vkEnumerateInstanceExtensionProperties ptr=0x7ffff76c8424
NULL_GIPA name=vkCreateDevice ptr=0x7ffff77c7c48
NULL_GIPA name=vkCreateDebugUtilsMessengerEXT ptr=(nil)
NULL_GIPA_RESULT bad=9
```

FEX exit: `29`.

The global controls remain non-NULL, but both `vkGetDeviceProcAddr` and `vkCreateDevice` incorrectly become non-NULL with a `NULL` instance.

## Source match

At `f3ab82...`, `ThunkLibs/libvulkan/Guest.cpp` special-cases `vkGetDeviceProcAddr` before consulting the host result:

```cpp
PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance a_0, const char* a_1) {
  if (a_1 == std::string_view {"vkGetDeviceProcAddr"}) {
    return (PFN_vkVoidFunction)vkGetDeviceProcAddr;
  } else {
    auto Ret = fexfn_pack_vkGetInstanceProcAddr(a_0, a_1);
    if (!Ret) {
      return nullptr;
    }
    return MakeGuestCallable(__FUNCTION__, Ret, a_1);
  }
}
```

That directly explains the first bad result: native NULL is never queried for the special-cased name.

The `vkCreateDevice` result shows the broader host-side proc-address routing also returns a non-NULL path in a NULL-instance case that the Vulkan table assigns to NULL.

Exact source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libvulkan/Guest.cpp

## Conclusion

Current FEX `f3ab82...` violates the Vulkan NULL-instance `vkGetInstanceProcAddr` command-level contract in at least two tested cases:

- `vkGetDeviceProcAddr`: native/spec `NULL`, FEX non-NULL;
- `vkCreateDevice`: native/spec `NULL`, FEX non-NULL.

This is a semantic defect independent of the callback SIGILL findings. It strengthens the case for a lookup design that first asks the native implementation whether the requested command is valid for the supplied instance and only substitutes an FEX wrapper when the native query itself returned non-NULL.

No upstream interaction was performed. All mutation and CI execution stayed in owned repositories/forks; upstream and Khronos sources were read-only.