# `VK_EXT_device_memory_report` hosted capability boundary

## Scope

Current FEX source contains a plausible additional cross-ISA callback hazard through `VkDeviceDeviceMemoryReportCreateInfoEXT` in `VkDeviceCreateInfo::pNext`.

At exact FEX product source `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`, the thunk interface handles `VkDeviceCreateInfo::pNext` but leaves the callback-bearing `VkDeviceDeviceMemoryReportCreateInfoEXT::pNext` specialization commented out. This remains a source-level concern because the struct contains `pfnUserCallback`.

The owned ARM64 workflow was designed with a native capability gate so an unsupported hosted driver could not be misrepresented as runtime FEX evidence.

- Owned-FEX branch: `ci/agent-b-device-memory-report-f3ab-20260814`
- Carrier commit: `fbff82c76c9fadc76363577cc046b155d68c459c`
- Workflow run: `31774414731`
- Job: `94686797413`
- Artifact: `9209352045`, `agent-b-device-memory-report-31774414731`
- Artifact digest: `sha256:92abcc4cb750e2e2d954a636d658e8244e901606648f7b247c0a3637ed81e614`
- Runner: hosted `ubuntu-24.04-arm`
- Workflow: https://redirect.github.com/teamleaderleo/FEX/actions/runs/31774414731

## Native capability result

The repaired native probe compiled against the exact pinned Vulkan header set and queried the hosted Lavapipe physical device for `VK_EXT_device_memory_report`.

Receipt:

```text
MEM_REPORT_SUPPORT supported=0 physical=0xab7d575fc540
```

Support-probe exit:

```text
77
```

The workflow therefore set `supported=no` and deliberately skipped:

- exact-product Vulkan thunk build;
- guest-rootfs preparation;
- FEX callback-path execution.

Its final receipt states:

```text
Lavapipe did not advertise VK_EXT_device_memory_report; runtime callback claim remains source-only.
```

## Evidence boundary

Demonstrated here:

- the hosted ARM64 Lavapipe used by this lane does not advertise `VK_EXT_device_memory_report`;
- the workflow correctly refuses to infer callback behavior from an unsupported driver;
- the current FEX source still exposes the previously recorded callback-bearing pNext handling gap.

Not demonstrated here:

- that current FEX executes this callback incorrectly on a driver which actually supports `VK_EXT_device_memory_report`;
- a native-vs-FEX callback differential for this extension.

The device-memory-report item therefore remains a **source-level hazard only**. Promoting it requires a driver/fixture that advertises the extension and can deterministically trigger the callback.

No upstream interaction was performed; all mutation and CI execution stayed in owned repositories/forks.