# Regular Vulkan proc-address corpus inventory

## Purpose

Define the complete regular-Vulkan command-name corpus for a registry-wide native-vs-FEX proc-availability differential.

This extends the earlier sampled `HOSTED_PROC_ALIAS_SEMANTICS.md` test. The earlier sample was clean, but Finding A was caused by a name-routing inventory hole. A full XML-derived corpus is the appropriate prevention check for that class.

## Exact receipt

```text
FEX source used for registry/submodule identity:
  c011366706eaf65a00380003989b3a10811212b6
workflow:
  .github/workflows/agent-c-proc-corpus-inventory.yml
workflow commit:
  ac7b9ac7573d8e62e555a947a9d68b9a501eba04
Actions run:
  31792729238
job:
  94743043741
artifact:
  9216141032
artifact SHA-256:
  0a839eea7efe5a3f19c9723660c5d5b1e125787a3eb1a51e54d2ca1630e1e35c
Vulkan-Headers submodule:
  450bd2232225d6c7728a4108055ac2e37cef6475
```

## Corpus size

The exact Vulkan XML registry exposes the following regular-Vulkan command-name corpus:

```text
regular command spellings: 773
alias spellings:            105
canonical commands:         668
```

Every spelling in `commands.txt` is included only when that command name is exposed by a regular `vulkan` core feature or extension. Vulkan SC-only names are excluded.

The inventory's simple first-parameter classification produced:

```text
instance-like: 112
device-like:   656
other/global:    5
```

That classification is only descriptive. The runtime differential should query **every one of the 773 names at every lookup scope**, because native Vulkan is the oracle and the purpose is precisely to catch surprising scope/availability behavior.

## Proposed full differential

Compile the same C probe once for native ARM64 and once for x86-64. Use the same native Lavapipe ICD and request the same Vulkan API version.

Create a normal instance and device with no optional extensions enabled, then for every command spelling emit normalized availability rows for:

```text
GIPA_NULL|<name>|0/1
GIPA_INSTANCE|<name>|0/1
GDPA_DEVICE|<name>|0/1
```

The output size is bounded:

```text
773 names x 3 scopes = 2319 availability rows per side
```

Sort/emit deterministically and byte-diff native ARM64 vs x86-through-FEX.

The test intentionally compares **availability only**, not raw function-pointer values. Host and guest pointers are expected to differ.

## Why native is the oracle

Do not hard-code Vulkan scope/promotion/extension expectations in the test. Loader behavior around promoted aliases, extension enablement, global scope, and device-vs-instance lookup has enough nuance that a hand-maintained expected table would recreate the inventory problem this test is meant to prevent.

The exact same driver + loader environment on the same ARM64 runner provides the strongest local oracle:

```text
native ARM64 Vulkan loader/Lavapipe
vs
x86 guest -> FEX Vulkan thunk -> same native loader/Lavapipe
```

A mismatch is then a FEX forwarding/availability candidate that can be investigated by exact command name and scope.

## Important test constraints

- regular Vulkan only; exclude Vulkan SC-only commands;
- include exposed alias spellings, not only canonical names;
- use one exact Vulkan XML/header revision on both probe builds;
- use the same `VK_DRIVER_FILES` Lavapipe ICD for native and FEX;
- request the same API version;
- do not enable optional extensions merely to make more names non-null;
- platform-specific names may remain in the string corpus; native availability decides whether they are relevant on Linux/headless Lavapipe;
- a nonzero diff is a research result, not automatically a product bug until the specific native/FEX semantic difference is understood.

## Next step

Run the complete 2319-row native-vs-FEX differential after the current `vkCreateInstance` callback-restoration candidate is settled. Keep the product candidate frozen during the differential unless a concrete mismatch demonstrates another routing defect.
