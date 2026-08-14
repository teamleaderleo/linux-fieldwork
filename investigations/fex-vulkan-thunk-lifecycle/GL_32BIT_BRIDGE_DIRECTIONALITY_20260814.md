# GL 32-bit resident bridge directionality — 2026-08-14

## Purpose

The strongest 64-bit Vulkan/GL resident-bridge prototypes initially used a broad generated split: every generated function-pointer signature received both resident directions:

```text
host-call invoker: GetCallerForHostFunction<signature>
callback unpacker: CallbackUnpack<signature>::Unpack
```

That is convenient for a prototype and stronger than the semantic requirement. This experiment asks whether that full bidirectional superset is valid under FEX's supported 32-bit guest thunk ABI.

Vulkan is 64-bit-only in FEX's current GuestLib build policy, so GL is the correct supported family for this discriminator.

## Exact carrier

Owned FEX branch:

```text
ci/gl-derived-bridge-32-build-20260814
carrier: d4fd5b9f8ec1618dbff783a11604d987bb504a0b
prototype base: 9bfbf20080cc58a12d3fc5ace127893940a0b035
```

Actions:

```text
run: 31784012375
job: 94715761673
```

Artifact:

```text
id:      9212836851
sha256:  4839289392b62a4aeaa40546a49157f77c69156c4ff6b7a9d8fa4b1f2c89a81f
```

## What reached the real gate

The following completed before the failure:

- branch/prototype provenance validation;
- host thunkgen build;
- 32-bit GuestLib configure using `Data/CMake/toolchain_x86_32.cmake`;
- normal GL generated output;
- extraction of the resident bridge output from the same generated source.

The generated GL source contains 717 `MAKE_CALLBACK_THUNK` signatures in this configuration.

The failure occurs while compiling the actual 32-bit resident companion object, not in CI setup.

## Failure

The prototype extractor emits an accessor for every generated signature that exposes both:

```cpp
GetCallerForHostFunction(name)
CallbackUnpack<decltype(name)>::Unpack
```

For one GL host-call signature, the callback side would require packing 23 arguments. Instantiating the resident `CallbackUnpack` therefore reaches FEX's existing guest callback packing limit:

```text
ThunkLibs/include/common/Guest.h
static_assert(sizeof...(Args) <= 19 || sizeof...(Args) == 24)
```

The failing bridge instantiation has 23 arguments.

The stock GL guest wrapper does not need a callback unpacker for every generated host-call signature. The full-superset bridge creates this template instantiation only because the extractor forces both directions for every signature.

## Interpretation

This is a design discriminator, not evidence that resident companions are incompatible with 32-bit guests.

The generated bridge needs **directional escape ownership**.

### Native function pointer -> guest

For signatures that can escape through `glXGetProcAddress` / equivalent proc-address returns, the resident component needs:

```text
resident GetCallerForHostFunction<signature>
```

That does not imply native code will ever call a guest callback with the same signature.

### Native callback -> guest

For callbacks that native/FEX state can retain, the resident component needs:

```text
resident CallbackUnpack<signature>::Unpack
```

That set is determined by callback parameters, callback members, typed custom helper publication, and related generator metadata.

### Consequence

Production thunkgen output should classify each escaped helper by direction rather than cloning every signature into both directions.

Conceptually:

```text
ResidentHostCallSignatures
ResidentGuestCallbackSignatures
```

A signature may appear in either or both sets when semantics require it.

## Why this is preferable to raising the PackedArguments limit

Expanding `PackedArguments` merely to make the full-superset bridge compile would solve a template symptom while preserving an overly broad ownership model.

Directional output has several benefits:

- matches the actual escape semantics;
- avoids unnecessary template instantiations;
- avoids creating callback machinery for signatures that never travel native -> guest;
- reduces resident code size;
- gives 32-bit and 64-bit generation the same semantic rule;
- creates a clean place for `callback_member` and custom escape annotations to contribute only the required direction.

The existing `PackedArguments` limit can be reviewed separately if a real native->guest callback with 20-23 arguments is demonstrated.

## Generator requirement

The current regex/post-processing prototype has already served its purpose. Production generation should classify direction while typed thunkgen analysis is still available.

For example:

```text
proc-address return / returned function pointer
    -> resident host-call invoker signature

direct callback parameter
    -> resident callback-unpacker signature when callback can escape wrapper lifetime

callback_member
    -> resident callback-unpacker signature when containing native state retains it

custom uintptr_t executable publication
    -> explicit typed direction + signature metadata
```

Retained containing-object lifetime remains a separate declaration.

## Next 32-bit gate

Repeat the GL build with directional generated output:

1. emit resident invokers for proc-address signatures;
2. emit resident unpackers only for actual GL guest callbacks (`malloc_wrapper`, X11 callbacks, generated callback parameters/members as applicable);
3. prove ELF32 bridge output;
4. prove wrapper remains unloadable and NEEDED bridge is present;
5. prove bridge `DF_1_NODELETE`;
6. run a 32-bit proc-address call through the resident invoker;
7. run one 32-bit native->guest callback through a resident unpacker.

Only after those should the RFC claim generic 32-bit runtime support.

## Evidence boundary

The red run establishes a concrete counterexample to **full bidirectional signature cloning** on i386. It does not reject the per-library resident-companion design.

No upstream FEX contact or mutation is authorized or performed by this record.
