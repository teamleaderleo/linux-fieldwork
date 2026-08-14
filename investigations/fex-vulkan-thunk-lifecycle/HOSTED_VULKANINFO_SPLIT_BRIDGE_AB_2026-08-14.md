# Hosted distro `vulkaninfo` split-bridge A/B — 2026-08-14

## Result

A real amd64 Ubuntu `vulkaninfo --summary` now passes under hosted ARM64 FEX with the generated Vulkan split-resident bridge, using the same FEX core and the same Finding-A host-thunk routing diagnostic as the unsplit control.

Observed matrix:

```text
unsplit=0
split=0
```

Both phases report:

```text
Vulkan Instance Version: 1.3.275
GPU0:
    deviceName = llvmpipe (LLVM 20.1.2, 128 bits)
    driverName = llvmpipe
```

The split phase additionally logs dynamic Vulkan native addresses being linked to guest invokers in the resident bridge throughout the real `vulkaninfo` workload.

## Run identity

Owned fork workflow:

```text
repository: teamleaderleo/FEX
workflow: .github/workflows/vulkaninfo-split-lifetime-ab-arm64.yml
run: 31781210938
job: 94707174060
workflow head: 80650707aef799337133cd30f83914abda82975a
artifact: 9211866011
artifact digest: sha256:9fbede96a867abd6e5f12435ca45b9c4d23fc76ed29c397ea0adc29a3d6fe5a3
reviewed FEX source: 71afe476751deac24adabd1adb575fd2337b6e0a
```

The job completed successfully through both actual tool phases.

## Controlled A/B

The common runtime is held fixed:

- same FEX core/runtime build;
- same real Vulkan host thunk;
- same native ARM64 Lavapipe driver;
- same amd64 distro `vulkaninfo` binary and extracted userspace;
- same Finding-A diagnostic host-thunk route for `vkCreateDebugReportCallbackEXT` in both phases.

The lifetime discriminator is guest-side generated Vulkan ownership.

### Unsplit phase

The ordinary generated `libvulkan-guest.so` owns its generated dynamic-PFN `CallHostFunction` adapters.

Result:

```text
exit=0
Vulkan Instance Version: 1.3.275
deviceName = llvmpipe (LLVM 20.1.2, 128 bits)
driverName = llvmpipe
```

### Split phase

Only the guest lifetime ownership is changed:

```text
unloadable libvulkan-guest.so
    DT_NEEDED -> libfex-vulkan-bridge.so

NODELETE libfex-vulkan-bridge.so
    generated signature-specific host-call adapters
    fixed Vulkan/X11 callback unpackers
```

The FEX core and Finding-A host thunk are unchanged from the unsplit phase.

Result:

```text
exit=0
Vulkan Instance Version: 1.3.275
deviceName = llvmpipe (LLVM 20.1.2, 128 bits)
driverName = llvmpipe
```

Representative split trace lines:

```text
Linking address <native Vulkan PFN> to resident host invoker <resident guest bridge address>
...
Opening host-side X11 display: <guest Display> -> <host Display>
```

The full trace contains many real Vulkan dynamic PFN registrations to resident bridge invokers and completes normally.

## amd64 userspace construction

The ARM runner does not require amd64 binfmt or foreign package scripts for this test.

The workflow constructs the distro guest userspace by:

1. using native ARM `apt-get` only as an amd64 dependency resolver/downloader in an isolated apt state with an empty status database;
2. downloading the amd64 closure for `vulkan-tools`, `libx11-6`, and `ca-certificates`;
3. extracting every amd64 `.deb` with `dpkg-deb -x` into the FEX rootfs;
4. materializing the standard `/lib64/ld-linux-x86-64.so.2` interpreter path from the extracted amd64 `libc6` loader;
5. replacing distro `libvulkan.so.1` with the generated FEX guest Vulkan wrapper for each A/B phase.

No amd64 maintainer scripts are executed during rootfs construction.

A separate extraction-only smoke also passes after this assembly rule.

## Harness correction history

An earlier run (`31780805957`) produced:

```text
unsplit=0
split=1
```

That split result was invalid as a lifetime discriminator. The unsplit step started `Xvfb :99` and killed it in its EXIT trap; the split step then reused `DISPLAY=:99` without restarting Xvfb. Its raw stderr ended with:

```text
XCB failed to connect to the X server
AppCreateXcbSurface failed to establish connection
```

There was no split crash in that run. The corrected workflow starts an independent Xvfb instance for each A/B phase. Run `31781210938` is the valid result.

## Meaning

This adds an end-to-end product-sized confirmation on top of the narrower retained-PFN and callback probes:

- the generated split bridge is not limited to a synthetic fixture;
- it is not limited to a single Vulkan PFN probe;
- it supports a real distro `vulkaninfo --summary` workload under hosted ARM64 FEX;
- real dynamic Vulkan PFNs are routed to resident guest adapters during the tool run;
- the tool enumerates llvmpipe and exits cleanly.

This does **not** replace the original Apple M5 teardown evidence. On this hosted reviewed-source environment, the unsplit control also exits `0`, so this A/B is compatibility/end-to-end validation of the split architecture, not a reproduction of the original M5 teardown `139`.

The original M5 evidence and the hosted moved-generation PFN stock/candidate A/B remain the causal failure receipts. The split selected-before-unmap race, real Vulkan PFN unload/reload test, exact FEX-2608 PFN test, and real Vulkan/X11 callback-after-unload test remain the lifetime-safety receipts.

## Boundary

All source edits and CI work are diagnostic/research code on owned repository surfaces. No upstream FEX interaction was made. AI-assisted experimental source is not represented as upstream-submittable FEX contribution code.
