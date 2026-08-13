# Synthetic FEX thunk lifetime reproducer

## TL;DR

This reduces the teardown failure in the parent [FEX Vulkan thunk lifecycle investigation](../README.md) to a guest-DSO lifetime test with Vulkan removed. The native model demonstrates stale executable pointers after `dlclose()`, same-address ABA rebinding, forced-different-address failure, host-pointer alias collision, cleanup, and repeated cycles. Two real-FEX probes exercise the actual thunk marker protocol and the two suspected retained-reference directions.

The ownership invariant is:

```text
lifetime(FEX state containing guest executable address)
    <= lifetime(guest DSO executable mapping)
```

A second valid policy lets that retained state own a loader reference that keeps the guest DSO mapped. A stable native function pointer and a recycled guest virtual address are identities; neither identifies a DSO load generation.

Internal carriers: [PR 669](https://github.com/teamleaderleo/linux-fieldwork/pull/669) and [issue 672](https://github.com/teamleaderleo/linux-fieldwork/issues/672).

## Explain like I'm five

FEX remembers executable guest addresses so native functions and guest callbacks can cross the architecture boundary. `dlclose()` can remove the library containing those addresses. A remembered pointer then leads into unmapped memory. A later reload can reuse the same address and make the stale pointer appear healthy while it actually reaches a new generation of code.

The fixtures expose every remembered address, exercise it before unload, unload the DSO, prove the executable mapping disappeared, then test retained state and reload behavior.

## Exact FEX source correspondence

Baseline: FEX-2608, `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

- [`Guest.h`](https://redirect.github.com/FEX-Emu/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/ThunkLibs/include/common/Guest.h): `MakeHostFunctionGuestCallable()` maps a native host function pointer to a guest `CallHostFunction` caller via `LinkAddressToFunction()`. `AllocateHostTrampolineForGuestFunction()` sends guest `GuestUnpacker` and `GuestTarget` addresses into FEX.
- [`Thunks.cpp`](https://redirect.github.com/FEX-Emu/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/Source/Tools/LinuxEmulation/Thunks.cpp): `GuestcallToHostTrampoline` is keyed by `{GuestUnpacker, GuestTarget}`. `MakeHostTrampolineForGuestFunction()` copies both guest addresses into persistent executable trampoline instance data.
- [`Core.cpp`](https://redirect.github.com/FEX-Emu/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/FEXCore/Source/Interface/Core/Core.cpp): `AddCustomIREntrypoint()` uses `emplace` keyed by the native entrypoint. `AddThunkTrampolineIRHandler()` captures `GuestThunkEntrypoint`. Re-registering one native address with a different guest target keeps the existing record and emits `Input address for AddThunkTrampoline is already linked elsewhere`; the adjacent source comment names Vulkan aliases as an example. `RemoveCustomIREntrypoint()` exists, while this source review found no guest-DSO unload owner tying `dlclose()` to removal of these thunk registrations.

That leaves two direct lifetime candidates:

1. stable native host function -> CustomIR record -> guest `CallHostFunction` invoker inside the unloaded DSO;
2. persistent host trampoline -> embedded `GuestUnpacker` / `GuestTarget` inside the unloaded DSO.

The failure condition can be asserted before a dangerous call:

```text
retained callable record contains guest executable address
AND
/proc/self/maps shows that address has no executable mapping
```

## Runnable source

The complete source-only fixture is retained as base64 text in `fex-thunk-lifetime-repro-source.tar.gz.b64`. Reassemble it from a checkout:

```sh
base64 -d fex-thunk-lifetime-repro-source.tar.gz.b64 > /tmp/fex-thunk-lifetime-repro-source.tar.gz
printf '%s  %s\n' \
  0582bf8832699cfb2614c1781473d07054ba01f03e3342735a45ea04735c2a01 \
  /tmp/fex-thunk-lifetime-repro-source.tar.gz | sha256sum -c -
mkdir -p /tmp/fex-thunk-lifetime-repro
tar xf /tmp/fex-thunk-lifetime-repro-source.tar.gz -C /tmp/fex-thunk-lifetime-repro
cd /tmp/fex-thunk-lifetime-repro
```

The archive contains source, Makefiles, and run scripts only; generated DSOs and executables are excluded.

### Native ownership model

```sh
make clean all
./thunk_lifetime_repro --call-stale --alias
./thunk_lifetime_repro --call-stale --force-different
./thunk_lifetime_repro --cleanup --force-different --alias --cycles 5
```

### Smallest real-FEX LinkAddress probe

```sh
cd fex-linkaddress-guest
make clean all
export FEX_RUN=/opt/fex-2608/bin/FEXInterpreter
./run-under-fex.sh
```

It uses one unloadable x86-64 guest DSO, a fixed synthetic native-address identity, and the real FEX `fex:link_address_to_function` marker. This is the smallest first bisect target.

### Full real-FEX pair

On an AArch64 FEX host:

```sh
cd fex-full-thunk-pair
make clean
make HOST_CXX=g++ GUEST_CXX=x86_64-linux-gnu-g++
export FEX_RUN=/opt/fex-2608/bin/FEXInterpreter
./run-under-fex.sh
```

Useful variants:

```sh
FEX_THUNKHOSTLIBS="$PWD/host" "$FEX_RUN" ./guest/fex_full_lifetime --call-stale --alias
FEX_THUNKHOSTLIBS="$PWD/host" "$FEX_RUN" ./guest/fex_full_lifetime --call-stale --force-different
FEX_THUNKHOSTLIBS="$PWD/host" "$FEX_RUN" ./guest/fex_full_lifetime --force-different --cycles 5
FEX_THUNKHOSTLIBS="$PWD/host" "$FEX_RUN" ./guest/fex_full_lifetime --pin
```

The full pair supplies two thunk names resolving to the same stable native host pointer, distinct guest invokers, and retained generation-1 versus current generation-2 host callbacks.

## Observed native-model results

The complete local transcript is retained as [`RESULTS.native.txt`](./RESULTS.native.txt).

- Before unload, both retained-call directions executed successfully.
- After `dlclose()`, the old invoker, target, and unpacker all lost executable mappings while retained records still held those pointer values.
- Exercising either stale record in a child produced SIGSEGV.
- Immediate reload reused the same guest invoker address in the observed run; the stale pointer became executable and returned the new generation's value. This is the ABA case.
- Reserving the old DSO span with `PROT_NONE|MAP_FIXED_NOREPLACE` moved the reload from `0x7f947c9d7110` to `0x7f947c9d2110`; the native host function address stayed stable and the old retained call remained invalid.
- A synthetic registry keyed only by the native pointer kept the first invoker when two names resolved to the same native function.
- Owner cleanup before `dlclose()` erased both retained records; five forced-different cycles completed with fresh registrations.

[`BUILD-VERIFIED.txt`](./BUILD-VERIFIED.txt) records successful builds of both FEX-specific probes plus disassembly showing the guest invoker capturing `r11` before its host thunk and the host callback packer reading the custom-ABI register.

## Expected discriminator under current FEX-2608

For LinkAddress, force a different guest reload address while keeping the native host function address stable. Re-registration of that native key should expose whether the old CustomIR record survives. Current source predicts a collision against generation 1 and execution routing toward its dead guest invoker.

For host->guest, keep `FirstCallback` from generation 1 and create `CurrentCallback` from generation 2. With different guest addresses, the useful split is: old callback reaches stale `{GuestUnpacker, GuestTarget}` while the current callback reaches generation 2. Same-address reload can conceal the stale record through ABA reuse. `--pin` is the positive lifetime control corresponding to the Vulkan guest-thunk pin from the parent investigation.

A passing cleanup policy retires generation-1 registrations before its guest text disappears, allowing the same stable native pointer to bind generation 2 cleanly. A passing pin policy keeps the corresponding guest text mapped while retained host trampolines can reach it.

## Regression-test candidate

[`unittests/ThunkFunctionalTests/`](https://redirect.github.com/FEX-Emu/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/unittests/ThunkFunctionalTests/CMakeLists.txt) is the strongest home because it already launches full FEX processes with `FEX_THUNKHOSTLIBS` and includes Vulkan functional coverage.

Suggested split:

- `ThunkLifetime-LinkAddressDifferentReload`
- `ThunkLifetime-HostCallbackOwner`
- `ThunkLifetime-AliasSameNative`

`unittests/ThunkLibs/` can cover smaller cache/key semantics; the loader lifecycle case needs a real guest process with `dlopen()` / `dlclose()`.

## Evidence boundary

The synthetic pair removes Vulkan's loader graph, dispatch tables, driver objects, generated API surface, callbacks, and teardown order. Its `CallHostFunction`-style invoker is hand-written around the same `r11` custom ABI, so a compiler defect unique to the C++ template instantiation remains outside this fixture. Forced-different reload deliberately reserves the old DSO span to create deterministic relocation pressure.

This execution environment lacks a FEX runtime. The real-FEX fixtures were built and disassembled here; their runtime variants remain for the retained FEX-2608 environment. The native ownership model ran completely and its transcript is retained.

External-contact state: **none**. All repository writes are confined to Linux Fieldwork. No FEX upstream issue, PR, comment, branch, or repository write was created.
