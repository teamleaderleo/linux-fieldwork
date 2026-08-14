# DRM nested callback-member resident bridge checkpoint

Date: 2026-08-14
Status: provisional research evidence
Scope: owned research surfaces only

## Result

A separate owned-FEX carrier demonstrates that the resident-bridge model can be generated for callback function pointers nested inside aggregate parameters rather than only handwritten callback setup or top-level function-pointer parameters.

Carrier:

```text
repository: teamleaderleo/FEX
branch: ci/agent-b-drm-nested-resident-bridge-20260814
head: a1cdc1d9b25519fef9655505897e8791f17962ea
run: 31782481709
job: 94711055708
```

Artifact:

```text
id: 9212317970
sha256: ecfa672256ba2dee982521b28f64b1de9d4ef36ad8b1457689568e6db8ace5b9
```

The run completed successfully with a resident bridge covering all three deduplicated callback signatures used by the test.

## Generator prototype

The carrier adds a `fexgen::callback_member` annotation for function-pointer struct members.

The analysis pass validates that the annotated field is a non-variadic function pointer, records the member, and registers its canonical callback signature in the existing function-pointer thunk set.

For DRM the prototype annotates callback members of `drmEventContext`, including the vblank/page-flip/sequence handlers.

The generated guest path copies callback-bearing input aggregates rather than modifying caller-owned memory, substitutes host-callable trampolines into the copy, and passes that converted copy onward. Host-side unpacking finalizes the callback trampolines and installs the native targets in the host-layout copy.

The resident bridge owns the callback unpacker execution bytes, while the ordinary DRM wrapper remains independently unloadable.

## Why this matters

This adds a third callback shape to the lifetime evidence:

```text
Vulkan / GL: handwritten persistent callback publication
DRM:         generated nested callback-member publication
Wayland:     custom protocol callback table (still under test)
```

It also supplies the cleaner provenance mechanism needed after the flat GL bridge extractor tried to manufacture callback unpackers for dynamic-only signatures. The generator knows that an annotated member is an actual callback role; it does not need to infer that role merely from the existence of a C function signature.

## Design implication

A production resident-bridge output should preserve bridge role information from thunkgen analysis:

```text
indirect callable PFN        -> resident guest-to-host caller
actual callback parameter    -> resident host-to-guest unpacker
callback_member              -> copied aggregate + resident unpacker
custom escaped callback path -> library-specific resident allocation seam
```

This checkpoint proves the nested callback generation path and resident execution. It is not, by itself, a moved-wrapper-after-registration lifetime A/B; CUDA and Wayland carriers are being used for that stronger retained-callback discriminator.

No upstream interaction or mutation is represented by this checkpoint.