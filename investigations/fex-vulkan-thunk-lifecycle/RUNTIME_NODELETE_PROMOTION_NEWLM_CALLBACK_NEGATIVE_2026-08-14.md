# Runtime base-namespace NODELETE promotion — NEWLM callback negative

Date: 2026-08-14

## Question

Can a guest thunk avoid link-time `DF_1_NODELETE` by promoting only its base-namespace instance at runtime with `RTLD_NOLOAD | RTLD_NODELETE`, while leaving `dlmopen(LM_ID_NEWLM, ...)` copies physically unloadable?

The native glibc primitive works and avoids the standalone namespace-retention behavior of ELF-wide NODELETE. A real FEX/Vulkan dynamic-PFN probe also appeared to work: the base Vulkan wrapper remained resident, a NEWLM wrapper physically unloaded, and the original base PFN still called successfully.

That PFN result was not sufficient because FEX-2608 keeps the first existing native-H CustomIR route when the same H is registered again with different guest target data. A NEWLM generation therefore need not replace the base H->T route.

The host->guest callback class is a stronger discriminator because Vulkan's persistent host-side X11 manager is mutable process-static state. Every Vulkan guest constructor publishes X11 callback targets/unpackers again.

## Owned-fork experiment

Repository: `teamleaderleo/FEX`

Branch: `diagnostic/vulkan-nodelete-promotion`

Workflow: `.github/workflows/vulkan-runtime-promotion-x11-newlm-arm64.yml`

Workflow commit: `dacc2ccb1084f05d56fa073e1d59a91e2587ab27`

Run: `31776801367`

Job: `94693828799`

Artifact: `promotion-newlm-x11-31776801367`

Artifact ID: `9210264879`

Artifact zip SHA-256:

```text
64eb7ee708acc70fcb97f9bb60dbcaf9f2f0c893b5ad236473aa6b42cfc7a5b3
```

The generated Vulkan wrapper contains no ELF `FLAGS_1: NODELETE`; only its base loader-namespace instance promotes itself from `OnInit()`.

## Trace

Base Vulkan/X11 callback works before close:

```text
BASE_CALLBACK_BEGIN xlib=0x7ffff77c7ee4
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
Opening host-side X11 display: 0x12345000 -> 0xffd09997c000
```

After ordinary close, base promotion keeps the base wrapper alive and the callback still works:

```text
BASE_PROMOTED_CALLBACK_BEGIN
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
Opening host-side X11 display: 0x12346000 -> 0xffd09997e800
```

A new loader namespace then loads another Vulkan guest wrapper:

```text
NEWLM_CONSTRUCTOR_DONE gipa=0x7fffebcd13e0
```

That NEWLM wrapper is deliberately not promoted. Its final close physically removes it:

```text
NEWLM_AFTER_CLOSE gipa_mapped=0
```

The original base Vulkan Xlib PFN is then invoked again with a third Display token:

```text
BASE_CALLBACK_AFTER_NEWLM_CLOSE_BEGIN
```

No subsequent guest `XSync` / `XDisplayString` marker appears. The FEX process SIGSEGVs:

```text
exit 139
PROMOTION_NEWLM_X11_RESULT=poisoned rc=139
```

## Interpretation

Base-only runtime promotion is **not a general guest-thunk lifetime repair**.

The dynamic-PFN result survived because FEX's process-global H registration can keep the original base-generation H->T route active when a duplicate H is presented by another namespace.

The callback path has different ownership. The NEWLM Vulkan constructor mutates persistent host Vulkan/X11 state by publishing callback trampolines whose guest unpacker lives in the NEWLM guest wrapper. Once that wrapper physically unloads, the persistent host-side helper can retain dead guest executable dependencies even though the original base wrapper remains resident.

This is a direct runtime counterexample to the idea that pinning only the base loader namespace is enough.

## Consequence for design ranking

Demote runtime `RTLD_NODELETE` self-promotion below the general candidates.

Current stronger choices remain:

1. whole shared-wrapper NODELETE / process residency, which protects every wrapper generation that can publish escaped bridge code;
2. a process-resident bridge runtime that owns the escaped `CallHostFunction` adapters and callback unpackers while ordinary wrappers unload;
3. explicit owner/generation plus execution-lifetime reclamation if even the bridge code must be reclaimed.

The failure also reinforces that loader-namespace correctness is broader than the Vulkan H table. FEX thunk state contains process-global host helper objects and callback registries that are not currently namespace-scoped.

All code and CI work here stayed on owned repositories/forks. No upstream interaction occurred.
