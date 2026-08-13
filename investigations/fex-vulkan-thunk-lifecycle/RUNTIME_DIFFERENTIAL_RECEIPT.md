# Vulkan native-first runtime differential

Owned FEX Actions run `31736419480` compared untouched reviewed FEX with the V3 native-first experiment on `ubuntu-24.04-arm`, using the same x86-64 probes, lavapipe, and headless X11 symbol fixture.

Status matrix:

```text
baseline:
direct-report=0
direct-utils=0
dynamic-report=132
dynamic-utils=132
procaddr=20

candidate:
direct-report=0
direct-utils=0
dynamic-report=0
dynamic-utils=0
procaddr=0
```

Baseline direct calls already use FEX custom mediation and finish with callback count 0. Baseline dynamic report and debug-utils creation resolve native function addresses; each successfully creates the callback object and then exits 132 when the forced native callback path is exercised.

The V3 candidate dynamically resolves the FEX custom wrappers instead. Both forced callback tests finish with callback count 0 and status 0.

Baseline proc-address checks fail three cases: null-instance `vkCreateDevice` is non-null, null-instance `vkGetDeviceProcAddr` is non-null, and valid-instance `vkGetInstanceProcAddr` self-query becomes null. V3 passes those cases and also preserves null results for disabled debug-report and debug-utils extension functions.

This is runtime evidence for both missing dynamic callback routes and for native-first proc-address gating. It does not yet cover non-null allocation callbacks, 32-bit execution, repeated/multi-object queries, or debug-utils callback create-info embedded in `vkCreateInstance::pNext`.
