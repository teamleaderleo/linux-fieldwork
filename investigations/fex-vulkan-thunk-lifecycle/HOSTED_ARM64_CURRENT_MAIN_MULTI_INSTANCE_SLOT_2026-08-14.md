# Hosted ARM64 current-main Vulkan multi-instance slot reuse — 2026-08-14

Status: demonstrated runtime semantic finding on exact upstream-current product source observed during this investigation.

FEX product revision: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.
Owned-FEX carrier commit: `30619db166bc7eaed61d60f5cea1144564a68ae9`.
Workflow run: `31770442454`.
Job: `94675067397`.
Artifact: `9208003933`, `agent-b-vulkan-multi-instance-slot-31770442454`.
Runner: GitHub hosted `ubuntu-24.04-arm`.
Driver: Lavapipe.

The workflow verified that the carrier had no product-source delta under `ThunkLibs`, `FEXCore`, or `Source` relative to `f3ab82...` before building FEX.

## Discriminator design

An ARM64 preload shim wraps the native Vulkan loader without replacing Vulkan behavior.

The shim records two real `VkInstance` handles according to application names:

```text
slot-A -> instance A
slot-B -> instance B
```

For `vkGetInstanceProcAddr(instance, "vkCreateDevice")`, it deliberately returns a distinct host wrapper according to the queried real instance:

```text
GIPA(A, vkCreateDevice) -> wrapper A
GIPA(B, vkCreateDevice) -> wrapper B
```

Both wrappers log their identity and then delegate to the real native `vkCreateDevice` implementation.

The probe creates both real instances, queries `vkCreateDevice` from each, enumerates a physical device through instance B, and invokes the pointer queried from B with valid Lavapipe device-create input.

This makes first-instance slot reuse observable even if an ordinary Vulkan loader would otherwise return one process-stable dispatch stub for both instances.

## Native ARM64 control

Native execution proves the discriminator follows the queried instance:

```text
SLOT_CREATE_INSTANCE name=slot-A ... A=<A> B=(nil)
PROBE create-A result=0 instance=<A>
SLOT_CREATE_INSTANCE name=slot-B ... A=<A> B=<B>
PROBE create-B result=0 instance=<B>
SLOT_GIPA instance=A wrapper=A
SLOT_GIPA instance=B wrapper=B
PROBE create-device-ptrs A=<wrapper-A> B=<wrapper-B>
PROBE invoke-B physical=<B physical device>
SLOT_CREATE_WRAPPER=B physical=<same physical device>
PROBE invoke-B-return result=0 device=<non-null>
```

Exit:

```text
native=0
```

The pointer queried from B reaches wrapper B, and real device creation succeeds.

## Exact FEX current-main result

FEX creates the same two real host instances successfully:

```text
SLOT_CREATE_INSTANCE name=slot-A ... A=<A> B=(nil)
PROBE create-A result=0 instance=<guest A>
SLOT_CREATE_INSTANCE name=slot-B ... A=<A> B=<B>
PROBE create-B result=0 instance=<guest B>
```

The host shim then records only the instance-A setup query:

```text
SLOT_GIPA instance=A wrapper=A
```

There is no host-side `SLOT_GIPA instance=B wrapper=B` before the guest B query completes.

At the guest boundary, both queried `vkCreateDevice` pointers collapse to the same FEX custom function address:

```text
PROBE create-device-ptrs A=0x7ffff77c7c48 B=0x7ffff77c7c48
```

The probe invokes the pointer obtained from instance B:

```text
PROBE invoke-B physical=<B physical device>
SLOT_CREATE_WRAPPER=A physical=<same physical device>
PROBE invoke-B-return result=0 device=<non-null>
```

Exit:

```text
fex=0
```

The device call succeeds, but it is dispatched through the host `vkCreateDevice` pointer obtained from **instance A**, not the pointer the native loader would return for instance B.

## Source match

At `f3ab82...`, `ThunkLibs/libvulkan/Host.cpp` is byte-identical to the reviewed `71afe476...` version for this code. It contains process-global setup state:

```cpp
static bool SetupInstance {};
static std::mutex SetupMutex {};
```

`DoSetupWithInstance(instance)` populates process-global loader slots such as `LDR_PTR(vkGetDeviceProcAddr)` and `LDR_PTR(vkCreateDevice)` from that instance and sets `SetupInstance = true`. The source explicitly carries `TODO: Support use of multiple instances`.

Later `vkGetInstanceProcAddr` calls normally skip setup once the process-global flag is set. The returned FEX custom `vkCreateDevice` entrypoint therefore uses the already-populated process-global native loader slot.

The runtime markers show that behavior directly: the first real instance establishes wrapper A, the second guest instance still receives the same FEX custom wrapper address, and its actual device creation reaches host wrapper A.

## Interpretation

This promotes the first-instance process-global loader-slot concern from a source-level limitation to an observable runtime semantic error.

The test does **not** rely on a crash. It demonstrates that FEX changes the instance ownership of the underlying host function pointer:

```text
native query B -> host wrapper B -> real vkCreateDevice
FEX query B   -> FEX custom wrapper -> retained host wrapper A -> real vkCreateDevice
```

Lavapipe accepts the resulting call in this environment, so the visible API result is still success. That does not make the dispatch substitution correct: a loader or layered/multi-implementation environment is permitted to return instance-compatible dispatch pointers that differ between instances.

This is independent of the unsynchronized `SetupInstance` C++ data race documented separately. The run is single-threaded; it demonstrates wrong process-global ownership even without concurrent access.

## Design implication

The custom Vulkan host layer should not treat one non-null instance as the permanent owner of instance-scoped native loader slots.

Possible design directions include:

1. query the required native function pointer from the actual instance/device at each custom call where practical;
2. store dispatch state per compatible instance/device ownership rather than in one process-global slot;
3. use a loader-provided process-stable entry only where Vulkan semantics and the actual loader contract make that stability explicit;
4. remove the separate unsynchronized one-time flag as part of the same redesign.

The native-first proc-address routing candidate does not by itself repair this state model because it governs whether a custom wrapper should be returned; once inside `vkCreateDevice`, the current custom wrapper still uses the process-global native slot.

## Evidence boundary

Demonstrated here:

- exact `f3ab82...` product source;
- two real native Vulkan instances;
- native A/B GIPA returns distinct controlled wrappers;
- native B invocation reaches wrapper B;
- FEX B query returns the same FEX custom pointer as A;
- FEX B invocation reaches retained host wrapper A;
- real device creation still succeeds through that wrong retained slot.

Not demonstrated here:

- a crash caused by the slot substitution;
- every process-global Vulkan loader slot has the same observable multi-instance failure;
- a production-ready per-instance dispatch redesign;
- the separate concurrent `SetupInstance` race at runtime.

No upstream write or interaction was performed. All mutation and workflow execution remained in owned repositories/forks.
