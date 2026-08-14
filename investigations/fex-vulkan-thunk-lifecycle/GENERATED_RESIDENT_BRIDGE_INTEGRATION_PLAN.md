# Generated resident bridge integration plan

Date: 2026-08-14

## Goal

Generalize the successful Vulkan split-resident prototype without moving library-specific wrapper state into process-long storage and without requiring FEX core to reclaim already-selected wrapper-owned executable code.

The proven target ownership model is:

```text
ordinary guest wrapper DSO (unloadable)
    constructors / OnInit
    library-specific globals and mutable state
    generated public entrypoint pack/repack wrappers
    calls LinkAddressToFunction using resident adapter addresses
    calls host callback setup using resident unpacker addresses

resident guest bridge companion (NODELETE)
    signature-specific CallHostFunction adapters
    fixed CallbackUnpack<signature>::Unpack functions
    generated signature/thunk markers needed by those adapters
    no library-specific mutable generation state
```

A per-library companion is the smallest general integration step. Cross-library signature deduplication can be a later optimization.

## Why this cut is evidence-driven

The following are already runtime-proven:

- wrapper-owned dynamic PFN adapters can outlive their wrapper generation in FEX-owned dispatch state;
- wrapper-owned fixed callback unpackers can outlive their wrapper generation in host-callable trampoline state;
- all-thread cache retirement fixes future selection but cannot revoke an already-selected host-code pointer;
- whole-wrapper NODELETE avoids that race but keeps too much wrapper-specific state resident;
- moving only escaped adapter/unpacker code to a NODELETE bridge lets the wrapper physically unload/reset;
- stock FEX then retains valid H and callback paths across wrapper close/reload;
- the exact selected-before-wrapper-unmap race returns correctly when the selected adapter lives in the bridge;
- the real generated Vulkan PFN path passes with wrapper physical unload and forced moved reload;
- the real generated Vulkan/X11 callback path passes after exact wrapper mapping count reaches zero.

The generator integration should preserve that ownership boundary rather than reintroduce generation-owned executable addresses.

## Phase 1 — per-library resident companion

### GuestLibs CMake

Extend `add_guest_lib()` or add a sibling helper that can create:

```text
${lib}-guest                  ordinary wrapper
${lib}-bridge-guest           optional resident companion
```

For libraries that need escaping signature glue:

```cmake
add_library(${lib}-bridge-guest SHARED ...)
target_link_options(${lib}-bridge-guest PRIVATE "LINKER:-z,nodelete")
set_target_properties(${lib}-bridge-guest PROPERTIES
  OUTPUT_NAME "fex-${lib}-bridge")
target_link_libraries(${lib}-guest PRIVATE ${lib}-bridge-guest)
target_link_options(${lib}-guest PRIVATE "LINKER:-rpath,$ORIGIN")
```

Install the companion next to GuestThunks.

Do **not** put NODELETE on the ordinary wrapper.

### Generated bridge source

Thunkgen already knows:

- every generated API function signature;
- unique callback/function-pointer signatures;
- the generated thunk SHA/marker for each signature;
- which public API functions require dynamic native-address linking.

Emit a companion source/inl with two families of generated symbols.

#### A. Native H adapters

For each relevant API function name/signature:

```cpp
static const uintptr_t resident_vkFoo =
  reinterpret_cast<uintptr_t>(GetCallerForHostFunction(vkFoo));
```

The wrapper's dynamic-name table should point at the companion's resident adapter rather than instantiate `GetCallerForHostFunction` inside the wrapper.

A production interface can avoid an unordered map if desired. Possibilities:

```text
name -> resident adapter table generated in companion
indexed generated table shared by wrapper/bridge
wrapper-generated direct symbol reference per API
```

The key invariant is address ownership, not lookup representation.

#### B. Fixed callback unpackers

For each callback/function-pointer signature whose unpacker address may be stored in FEX/host state:

```cpp
&CallbackUnpack<signature>::Unpack
```

must resolve to code in the resident companion.

The actual GuestTarget remains owned by the guest component that implements the callback. For Vulkan X11 setup, the targets are `XSync`, `XGetVisualInfo`, and `XDisplayString` in guest libX11, while the fixed unpackers are resident bridge glue.

## Phase 2 — generator-native split, no post-processing

The current Vulkan research transformer post-processes generated output to extract:

- `MAKE_CALLBACK_THUNK(...)` signature glue;
- `FOREACH_internal_SYMBOL` API names.

That is acceptable diagnostic machinery but should not become the final generator interface.

Thunkgen should directly emit separate generated artifacts, for example:

```text
thunkgen_guest_${lib}.inl                 wrapper-facing generated code
thunkgen_guest_bridge_${lib}.inl          resident adapter/unpacker glue
thunkgen_guest_bridge_symbols_${lib}.inl  optional name/index table
```

The existing signature SHA should remain the compatibility/deduplication identity.

## Phase 3 — deduplicate companions across libraries

Once per-library companions are stable, measure duplicate resident signatures.

If worthwhile, collapse to one per-bitness process bridge:

```text
libfex-thunk-bridge-64.so
libfex-thunk-bridge-32.so
```

with adapters/unpackers keyed by generated signature identity.

Do this only after correctness. Per-library companions already solve the lifetime race while keeping wrapper state unloadable.

## Logical stale-H policy is separate

The split architecture makes a stale previously advertised H **safe to execute** because its generic adapter remains resident and current FEX host thunk libraries are process-live.

That does not dictate the API policy.

A product may choose:

### permissive resident behavior

```text
H remains callable after wrapper logical close
```

or:

### owner-aware logical revocation

```text
H -> resident adapter -> ACTIVE/REVOKED policy state
```

The crucial improvement is that logical revocation no longer controls whether the wrapper's executable bytes can be reclaimed safely. An already-selected adapter remains resident either way.

## FEX core changes can therefore be narrower

A split bridge reduces pressure on FEX core lifetime machinery.

Potential core work still useful:

- explicit ownership metadata for logical H claims;
- multi-owner compatible-claim retention/promotion;
- ACTIVE/REVOKED stale-use policy;
- callback descriptor state where GuestTarget itself can unload;
- cleanup of process-long bookkeeping that is no longer valid.

But **wrapper executable reclamation no longer requires all-thread cache invalidation or an execution drain for resident H adapters**, because selected bridge executable code is no longer generation-owned.

Ordinary wrapper code invalidation on `munmap` remains normal guest-code invalidation.

## Regression gates to keep

A generalized implementation should carry all of these focused tests.

### H direction

```text
load wrapper
acquire native H -> resident adapter
call H
close wrapper
prove exact wrapper path unmapped
call retained H
reserve old wrapper mappings
reload wrapper at different base
reacquire same H
prove same resident adapter
call H
```

### callback direction

```text
load wrapper
publish host callback using resident fixed unpacker
call callback
close wrapper
prove wrapper unmapped
call retained host callback with fresh GuestTarget input/state
```

### selected-before-unmap race

```text
worker selects resident adapter -> host code
pause after selection guard
unmap wrapper
prove adapter remains resident
resume worker
expect return, not signal
```

### wrapper-state reset

Use a wrapper-local generation/static marker and prove logical unload/reload creates fresh wrapper state while resident adapter address remains unchanged.

### same-address ABA

Force wrapper address reuse and prove resident bridge identity is stable while wrapper generation/state is fresh.

### multi-owner same H

If logical ownership/revocation is implemented, retain compatible claims and test promotion independently of adapter executable residency.

## Library audit order

After Vulkan, prioritize wrappers that already exhibit one of these patterns:

- dynamic `GetCallerForHostFunction` tables;
- fixed `CallbackUnpack` addresses passed to host code;
- host APIs that retain guest function pointers asynchronously.

GL is an obvious next audit because it also has dynamic host-pointer invoker tables and callback unpacker use.

## Packaging / loader checks

Every companion build should verify:

```text
bridge:  DF_1_NODELETE
wrapper: no NODELETE
wrapper: DT_NEEDED bridge
wrapper: RUNPATH/RPATH can locate bridge beside GuestThunks
32-bit and 64-bit variants locate correct-bitness companion
```

Special thunk link modes such as VDSO should remain separate unless they actually need escaping bridge glue.

## Submission boundary

This plan is derived from AI-assisted research code and runtime evidence in owned repositories. It is not upstream-submittable FEX contribution code. Any upstream implementation must be independently derived and written by a human under FEX policy.

No upstream FEX interaction was made.