# Vulkan instance `pNext` callback mediation

Date: 2026-08-14
Status: research design note
Scope: owned research surfaces only

## Problem

FEX's custom Vulkan `vkCreateInstance` host wrapper currently walks the application's `VkInstanceCreateInfo::pNext` chain looking for callback-bearing extension records.

The relevant callback cases are:

- `VkDebugReportCallbackCreateInfoEXT::pfnCallback`;
- `VkDebugUtilsMessengerCreateInfoEXT::pfnUserCallback`.

The current implementation treats the application-owned chain as mutable even though Vulkan exposes it through `const void *pNext` and the host wrapper receives a const create-info view.

The existing debug-report path can unlink a node by `const_cast`-writing the predecessor's `pNext`. The newer candidate also rewrites the debug-utils callback field in place.

## Concrete read-only failure

A controlled probe places `VkInstanceCreateInfo` on a page that is writable during construction and then changes the page to `PROT_READ` before `vkCreateInstance`.

Native Vulkan reaches the call and returns normally for the intentionally unsupported-extension control while preserving the caller-owned chain.

Exact FEX product source `71afe476751deac24adabd1adb575fd2337b6e0a` faults after `MARK create-enter` with exit `139` because the custom host wrapper writes through the caller's read-only create-info / chain state.

Owned carrier:

```text
ci/agent-b-readonly-pnext-arm64-20260814
run 31770241831
```

This is a caller-memory ownership defect independent of the thunk executable-lifetime investigation.

## Candidate result — still fails immutable caller memory

Owned-FEX candidate:

```text
fix/vulkan-instance-callback-pnext
0a19582b538b521420df07ffadeb13679351a4c3
```

The candidate improves traversal semantics for adjacent debug-report/debug-utils nodes and adds real debug-utils callback mediation.

It still performs in-place writes through `const_cast`:

- predecessor `pNext` writes when skipping debug-report records;
- `pfnUserCallback` replacement inside debug-utils records.

Candidate-specific carrier:

```text
ci/vulkan-pnext-candidate-readonly-20260814
carrier: 961b1087a53e9f9d4c8279b53f79698209b3e82e
run:     31783496219
job:     94714147345
```

All provenance, build, rootfs, and probe-preparation steps passed. The only red gate was execution.

Final matrix:

```text
native=0
candidate=139
```

Native control:

```text
MARK readonly=...
MARK create-enter
MARK create-return result=-7 instance=(nil) ... same=1
```

Candidate FEX:

```text
MARK readonly=0x7ffff7ec4000 ...
MARK create-enter
<segmentation fault before create-return>
```

Artifact:

```text
id:      9212682095
sha256:  24217f909131ae6259ce089cd12f2ab3ab21d8971d55a88075e5b76a81e549a4
```

This demotes `0a19582b...` as a source-ready repair. Its callback-routing changes may still be useful input to a later typed conversion patch, while the in-place caller-memory ownership model must change.

## Design rule

> Vulkan thunk marshalling must never require application-owned `pNext` memory to be writable.

Callback mediation and chain ownership should be expressed separately:

```text
callback field       -> how a guest callback becomes a native-callable trampoline
pNext node copy      -> who owns the converted node passed to native Vulkan
chain linkage        -> built entirely from converted/copied nodes, never by editing caller linkage
retained lifetime    -> how long native Vulkan may retain a converted callback-bearing node
```

## Why a one-pointer local repair is insufficient

Skipping an arbitrary middle node requires changing the predecessor's link. If the predecessor belongs to the application, that is another caller-memory write.

Rewriting a callback function pointer in an extension record has the same issue.

A source correction therefore needs ownership of every node whose linkage or callback field changes.

## Preferred direction

Use a typed converted `pNext` chain for callback-bearing instance-create records.

At minimum, the conversion path should:

1. walk the guest/application chain without mutation;
2. copy every node that needs callback mediation or whose `pNext` link must differ in the host chain;
3. convert callback fields in the copies using FEX's typed host-to-guest trampoline machinery;
4. build host-side linkage exclusively between owned copies / safely passthrough nodes;
5. pass a converted `VkInstanceCreateInfo` view to native Vulkan;
6. release temporary converted nodes only after the native call completes, unless Vulkan's contract permits the node/callback state to escape the call.

For `vkCreateInstance`, the callback-bearing debug create-info records are consumed during instance creation. Later callback delivery is represented by the created native debug object / callback registration semantics, so the exact retained-state contract still needs to be verified per extension before choosing stack versus longer-lived converted storage.

## Generator connection

The DRM `callback_member` prototype shows that thunkgen can already be taught to mediate callback members embedded inside aggregate types without handwritten wrappers.

Vulkan `pNext` adds a second dimension: a heterogeneous tagged chain whose node type is selected by `VkStructureType`.

A useful generator/runtime model would combine:

```text
tagged extension-node metadata
callback-member metadata
node-size/layout conversion
chain-copy ownership
optional retained-object lifetime
```

This could eventually cover debug callbacks and other callback-bearing Vulkan extension records with one typed mechanism.

## Immediate acceptance tests

Any `vkCreateInstance` callback fix should pass all of these:

```text
read-only VkInstanceCreateInfo
read-only callback-bearing pNext node
callback node as first element
callback node in the middle of a chain
adjacent debug-report + debug-utils nodes
unknown/pass-through extension nodes before and after mediated nodes
native callback actually enters the guest callback when creation succeeds
caller pNext and callback fields bit-identical after return
```

Negative controls should include an intentionally unsupported extension so the test can verify memory preservation without depending on a display server or a particular validation-layer installation.

## Relation to resident bridge work

Once a callback field is mediated, the executable unpacker used by the host trampoline has the separate lifetime question covered by the thunk executable-lifetime RFC.

The two problems should remain distinct:

```text
pNext mediation correctness -> immutable caller memory + typed chain conversion
callback executable lifetime -> resident unpacker / owner-generation policy
```

Solving one does not imply the other.

## External-contact state

No upstream FEX contact or mutation is authorized or performed by this record.
