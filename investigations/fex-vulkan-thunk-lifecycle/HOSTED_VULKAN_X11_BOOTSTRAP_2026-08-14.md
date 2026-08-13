# Hosted ARM64 Vulkan guest X11 bootstrap A/B

Date: 2026-08-14

## TL;DR

A hosted current-FEX Vulkan-thunk SIGILL that initially blocked the callback-routing experiment was a rootfs bootstrap artifact.

On exact FEX source `71afe476751deac24adabd1adb575fd2337b6e0a`, the generated x86-64 `libvulkan-guest.so` exits with SIGILL while loading in the minimal amd64 rootfs when x86 `libX11.so.6` is absent. Adding only a tiny x86 `libX11.so.6` exporting the three symbols that FEX Vulkan `OnInit()` requests changes the same `dlopen("libvulkan.so.1")` probe from exit `132` to exit `0`.

No FEX or Vulkan source behavior changed between the two cases.

This clears the hosted current-main Finding A lane: the callback-routing A/B should be rerun with valid x86 X11 guest targets supplied.

## Exact identities

- owned FEX repository: `teamleaderleo/FEX`
- exact FEX source under test: `71afe476751deac24adabd1adb575fd2337b6e0a`
- disposable branch: `ci/vulkan-guest-x11-bootstrap-20260814`
- workflow source commit: `e5a872494098bec5b536731724351c193bf3adbd`
- workflow: `Vulkan guest X11 bootstrap A-B`
- GitHub Actions run: `31732798772`
- artifact: `vulkan-guest-x11-bootstrap-31732798772`
- artifact id: `9194035439`
- runner: GitHub hosted `ubuntu-24.04-arm`

## Why this probe exists

The first authoritative hosted Finding A artifact had already established:

```text
static x86 smoke under FEX      0
dynamic plain x86 under FEX     0
dlopen generated Vulkan thunk 132
callback direct                132
callback GIPA baseline         132
callback GIPA candidate        132
```

The callback cases therefore stopped before their callback-routing discriminator.

Current Vulkan guest source performs this constructor path:

```text
LOAD_LIB_INIT(libvulkan, OnInit)
  -> dlopen("libX11.so.6", RTLD_LOCAL | RTLD_LAZY)
  -> dlsym(..., "XSync")
  -> dlsym(..., "XGetVisualInfo")
  -> dlsym(..., "XDisplayString")
  -> publish those guest targets through Vulkan_SetGuest...
```

FEX's host-to-guest trampoline helper requires a nonzero guest target. The minimal amd64 rootfs used by the focused hosted lane had no x86 `libX11.so.6`.

## A/B fixture

Both variants used:

- the same FEX interpreter and `FEXServer`;
- the same generated 64-bit Vulkan host and guest thunks;
- the same amd64 rootfs;
- the same x86 phase probe;
- the same host thunk directory;
- the same command: x86 `dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL)` under FEX.

The candidate variant added one x86 shared object with SONAME `libX11.so.6` and only these exports:

```text
XSync
XGetVisualInfo
XDisplayString
```

The stub is intentionally narrow. The phase probe exits immediately after a successful Vulkan-thunk `dlopen`; it performs no real X11 or Vulkan operation.

## Result

Artifact matrix:

```text
no_x11=132
with_x11=0
```

Baseline stderr reached:

```text
BEFORE_DLOPEN
```

and then FEX reported the guest SIGILL.

Candidate stderr reached:

```text
BEFORE_DLOPEN
AFTER_DLOPEN
```

with exit `0`.

## Interpretation

The focused hosted SIGILL belongs to guest Vulkan constructor/bootstrap setup, specifically the missing X11 guest-target prerequisites in this minimal rootfs.

It is distinct from the retained Apple M5/FEX-2608 Finding A runtime result. The M5 environment had a complete enough guest userspace to reach dynamic Vulkan callback routing. The hosted current-main lane can now do the same by supplying the three required x86 X11 targets.

The result also gives a useful source lesson for future thunk fixtures: generated guest-wrapper constructors can depend on sibling guest libraries even when the reduced application never calls the corresponding API family.

## Next action

Rerun the current-main hosted callback matrix with this X11 stub as fixture setup:

```text
static x86 smoke
dynamic plain x86
guest Vulkan dlopen
direct debug-report callback control
GIPA debug-report baseline
same GIPA case with only diagnostic custom create routing changed
```

Require the guest Vulkan `dlopen` gate to pass before interpreting either callback result.

## Evidence limits

- The X11 stub proves constructor/bootstrap sufficiency for this reduced load probe; it is not a functional X11 implementation.
- This run establishes no current-main callback-routing result by itself.
- The hosted rootfs is synthetic and narrower than the retained Fedora target environment.
- The exact three-symbol dependency is source- and runtime-supported for this bootstrap path; other Vulkan/X11 operations can require additional guest X11 behavior.

## External-contact state

None. No FEX upstream interaction was made.
