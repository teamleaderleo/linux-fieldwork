# Hosted ARM64 multiple debug-utils pNext sanitizer test — 2026-08-14

Status: demonstrated candidate-design failure on a Vulkan-valid repeated-`sType` pNext chain. This run does not by itself establish the pristine-FEX baseline for this exact two-node probe.

Base product revision: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX carrier commit: `be1688b706b2be310b05830f545d0cdaa9aeba2d`.
Workflow run: `31769493404`.
Job: `94672297793`.
Runner: GitHub hosted `ubuntu-24.04-arm`.

The workflow verified that the carrier had no product-source delta under `ThunkLibs`, `FEXCore`, or `Source` relative to `71afe476751deac24adabd1adb575fd2337b6e0a` before applying the diagnostic candidate.

## Why the two-node chain is valid input

The Vulkan `VkInstanceCreateInfo` valid-usage rules normally require each `sType` in the input `pNext` chain to be unique, but explicitly exempt `VkDebugUtilsMessengerCreateInfoEXT` from that uniqueness rule. Multiple debug-utils create-info structures are therefore legal in this chain.

Specification reference:

- `https://redirect.github.com/KhronosGroup/Vulkan-Docs` — see `VUID-VkInstanceCreateInfo-sType-unique` in the current Vulkan specification / generated `VkInstanceCreateInfo` reference page. The exception list includes `VkDebugUtilsMessengerCreateInfoEXT`.

The native control also exercises the exact chain and invokes both callback nodes.

## Probe shape

The chain is:

```text
VkInstanceCreateInfo
  -> debug-utils node 1
  -> debug-utils node 2
  -> NULL
```

Both nodes use the same callback entrypoint with the retained x86/ARM64 instruction discriminator. The probe enables `VK_EXT_debug_utils` and also requests an intentionally missing extension so the loader emits synchronous debug messages during `vkCreateInstance` and then returns `VK_ERROR_EXTENSION_NOT_PRESENT`.

## Diagnostic candidate under test

The candidate extends FEX's existing destructive `vkCreateInstance` pNext loop so that it removes either a debug-report node or a debug-utils node by rewriting the previous structure's `pNext` pointer:

```text
if next node is DEBUG_REPORT or DEBUG_UTILS:
    current->pNext = current->pNext->pNext
```

It otherwise retains the loop's existing increment behavior.

This candidate had previously been shown to suppress a single debug-utils pNext callback. The question here is whether it handles the full Vulkan-valid repeated-node case.

## Native ARM64 control

Observed:

```text
CALLBACK_PTR=<native-arm callback> FIRST=<node1> SECOND=<node2>
MARK create-enter
CALLBACK count=1 id=Loader Message
CALLBACK count=2 id=Loader Message
MARK create-return result=-7 callbacks=2 instance=(nil)
```

Exit:

```text
native=0
```

This confirms that both legal nodes are active and independently receive the synchronous loader event.

## Candidate FEX result

Observed:

```text
CALLBACK_PTR=<guest-x86 callback> FIRST=<node1> SECOND=<node2>
MARK create-enter
```

There is no callback-body marker and no `MARK create-return`.

Exit:

```text
candidate_fex=132
Illegal instruction
```

## Interpretation

The result matches the loop-advance failure mode.

Starting with:

```text
root -> node1 -> node2
```

the candidate sees `node1` as `root->pNext` and rewrites the link to:

```text
root -> node2
```

The `for` loop then performs its normal increment through the **new** `root->pNext`, making `node2` the current node. The condition only examines `current->pNext`, so it never examines or removes `node2` itself. The second guest callback therefore remains in the chain and can reach the native ARM loader.

The absence of any guest callback-body marker before SIGILL is consistent with raw native entry into the remaining x86 callback pointer.

## Design implication

A callback-safe `pNext` repair should not mutate and advance through the caller's chain in this way. It needs to process the entire legal chain, including repeated callback-bearing nodes, without skipping newly exposed elements. A copied/sanitized host-side chain is preferable because it can also avoid the separate caller-input mutation defect in the existing `vkCreateInstance` implementation.

This result also explains why a single-node suppression test is insufficient as a regression test. The regression matrix needs at least:

- one debug-utils node;
- two adjacent legal debug-utils nodes;
- callback-bearing nodes separated by an unrelated legal pNext structure;
- preserved caller-owned input after the call.

## Evidence boundary

Demonstrated here: Vulkan-valid two-debug-utils-node native behavior and failure of the specific destructive single-node sanitizer candidate on ARM64 FEX.

Not demonstrated here: the exact pristine-FEX result for this two-node input, or a complete copied-chain repair.
