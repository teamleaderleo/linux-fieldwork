# Evidence matrix — FEX Vulkan thunk lifecycle

## In simple words

This file keeps the distinguishing commands and outcomes separate from interpretation. The authoritative runtime source was `FEX-2608` (`e869aa644a16e4332cdc15c1ea0b4d13d482385d`) built locally to `/opt/fex-2608`. Current upstream `main` was source-read at `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Environment receipt

```text
Host: Apple M5 MacBook Air, arm64, Darwin 25.6.0
Lima: 2.2.0
krunkit: 1.3.2
VM: Fedora 44 Cloud Edition, aarch64
Kernel: 6.19.10-300.fc44.aarch64
vCPUs: 6
RAM: 8 GiB
Mesa: 25.3.6
FEX source: FEX-2608 / e869aa644a16e4332cdc15c1ea0b4d13d482385d
FEX install: /opt/fex-2608
FEX rootfs: /usr/share/fex-emu/RootFS/default.erofs
Guest Vulkan thunk: /opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so
Host Vulkan thunk: /opt/fex-2608/lib64/fex-emu/HostThunks/libvulkan-host.so
```

## Build receipt

```sh
cd ~/src/FEX-2608
mkdir -p Build
cd Build

CC=clang CXX=clang++ cmake \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX=/opt/fex-2608 \
  -DUSE_LINKER=lld \
  -DENABLE_LTO=False \
  -DBUILD_TESTING=False \
  -DBUILD_THUNKS=True \
  -DBUILD_FEXCONFIG=False \
  ..

../Data/nix/cmake_enable_libfwd.sh
ninja -j6
sudo ninja install
```

GDB JIT support was later enabled after confirming `/usr/include/gdb/jit-reader.h`:

```sh
cd ~/src/FEX-2608/Build
cmake -U HAVE_GDB_JIT_READER_H -DENABLE_GDB_SYMBOLS=ON ..
grep -E '^ENABLE_GDB_SYMBOLS:|HAVE_GDB_JIT_READER_H' CMakeCache.txt
ninja -j6
sudo ninja install
```

Observed cache:

```text
ENABLE_GDB_SYMBOLS:BOOL=ON
HAVE_GDB_JIT_READER_H:INTERNAL=1
```

## Native Vulkan baseline

Native ARM64 `vulkaninfo --summary` enumerated:

```text
Virtio-GPU Venus (Apple M5)
driverName = venus
Mesa 25.3.6
```

and llvmpipe.

This establishes that the native M5/krunkit/Venus path was working before FEX Vulkan investigation.

## CPU-translation control

```sh
FEXBash -c 'uname -m'
```

Observed:

```text
x86_64
```

## Baseline x86 Vulkan failure

Packaged FEX 2604 and pristine source-built FEX 2608 both produced SIGILL with the Fedora x86-64 `vulkaninfo` binary.

Representative command:

```sh
cd ~/fex-vulkan-test
FEX ./usr/bin/vulkaninfo --summary
```

Layer negative controls:

```sh
VK_LOADER_LAYERS_DISABLE='*MESA*' FEX ./usr/bin/vulkaninfo --summary
VK_LOADER_LAYERS_DISABLE='~all~' FEX ./usr/bin/vulkaninfo --summary
```

Observed: same SIGILL class.

## Source discriminator — debug-report callback

Khronos `vulkaninfo` uses legacy `VK_EXT_debug_report`:

```text
VkDebugReportCallbackCreateInfoEXT dbg_info
VkInstanceCreateInfo.pNext = &dbg_info
vkCreateInstance(...)
vkCreateDebugReportCallbackEXT(instance, &dbg_info, ...)
```

FEX source already has:

- a dummy native debug-report callback;
- a custom `vkCreateDebugReportCallbackEXT` implementation that replaces the guest callback;
- a custom `vkDestroyDebugReportCallbackEXT` implementation;
- `vkCreateInstance` handling for the debug-report create-info path.

`LookupCustomVulkanFunction()` in both `FEX-2608` and current `main` does not contain a `vkCreateDebugReportCallbackEXT` branch.

Diagnostic source candidate tested:

```cpp
} else if (a_1 == "vkCreateDebugReportCallbackEXT"sv) {
  return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkCreateDebugReportCallbackEXT;
}
```

This code is investigation evidence only. FEX prohibits AI-generated code contributions.

## Callback-routing result

With the source host thunk forced:

```sh
cd ~/fex-vulkan-test
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Diagnostic output showed:

```text
FEXDBG instance pNext debug-report callback=<guest address>
FEXDBG before native vkCreateInstance pNext=(nil)
FEXDBG explicit debug-report custom wrapper hit ...
```

Observed change: original SIGILL disappeared; Vulkan enumeration proceeded.

## Teardown failure

After the callback-routing change, `vulkaninfo` reached the Vulkan summary but still exited 139.

Forcing llvmpipe proved this was not Venus-specific:

```sh
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Observed: SIGSEGV / exit 139.

## Debug-report destroy boundary

A symmetric custom-lookup entry for `vkDestroyDebugReportCallbackEXT` was tested, and the existing custom destroy implementation was instrumented.

Observed:

```text
FEXDBG destroy debug-report wrapper hit instance=<...> callback=<...>
FEXDBG destroy debug-report before native
FEXDBG destroy debug-report after native
```

The process still exited 139.

Inference limit: the native debug-report destroy call returned. This does not independently prove whether the destroy lookup entry is required for correctness; there was no isolated old/new A/B for that entry.

## GDB configuration

GDB under krunkit initially failed while probing SVE/SSVE vector length. A no-SVE target description allowed GDB to attach:

```xml
<?xml version="1.0"?>
<target version="1.0">
  <architecture>aarch64</architecture>
</target>
```

Stored as:

```text
/home/leoli.guest/aarch64-nosve.xml
```

GDB setup:

```gdb
set tdesc filename /home/leoli.guest/aarch64-nosve.xml
set debuginfod enabled off
set environment VK_DRIVER_FILES /usr/share/vulkan/icd.d/lvp_icd.aarch64.json
set environment FEX_THUNKHOSTLIBS /opt/fex-2608/lib64/fex-emu/HostThunks
set args ./usr/bin/vulkaninfo --summary
handle SIGBUS nostop noprint pass
run
```

SIGBUS was allowed through because FEX uses/handles ARM alignment faults while translating x86 unaligned accesses. The stable terminal failure was SIGSEGV at:

```text
0x00008000595804b4
```

FEX dispatcher source shows that location is the intentional `GuestSignal_SIGSEGV` trampoline that forces a host SIGSEGV to represent a guest SIGSEGV.

## Guest fault record

At the stable SIGSEGV:

```gdb
p/x ((FEXCore::Core::CpuStateFrame*)$x28)->State.rip
p ((FEXCore::Core::CpuStateFrame*)$x28)->SynchronousFaultData
```

Observed:

```text
State.rip = 0x7ffff7cd21f0
FaultToTopAndGeneratedException = true
Signal = 11
TrapNo = 14
si_code = 2
err_code = 21
```

`TrapNo=14` is an x86 page fault. `err_code=21` is `0x15`, including the instruction-fetch bit.

## Mapping receipt

At crash time, no mapping covered `0x7ffff7cd21f0`.

Relevant neighborhood:

```text
0x7ffff7c83000 - 0x7ffff7c87000  rw-p
0x7ffff7c87000 - 0x7ffff7cdc000  [unmapped]
0x7ffff7cdc000 - 0x7ffff7ce1000  rw-p
0x7ffff7ce1000 - ...             r-xp guest libffi
```

The old guest RIP maps to an offset in the guest Vulkan thunk image if `0x7ffff7c87000` is treated as its previous base:

```text
0x7ffff7cd21f0 - 0x7ffff7c87000 = 0x4b1f0
```

`addr2line`:

```sh
addr2line -Cfipe \
  /opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so \
  0x4b1f0
```

resolved into a generated `CallHostFunction<...>` in `ThunkLibs/include/common/Guest.h`.

`objdump` around that offset:

```sh
objdump -dC \
  --start-address=0x4b1d0 \
  --stop-address=0x4b220 \
  /opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so
```

showed `0x4b1f0` lies inside the generated thunk body. Because FEX states `State.rip` may be imperfect while JIT is active, this supports the old-image-range conclusion but is not treated as an exact valid branch instruction boundary.

## Unload discriminator 1 — disable guest dlclose

Build x86-64 no-op `dlclose` preload:

```sh
cat > /tmp/nodlclose.c <<'EOF'
int dlclose(void *handle) {
    (void)handle;
    return 0;
}
EOF

clang --target=x86_64-linux-gnu \
  -fuse-ld=lld \
  -shared -fPIC -nostdlib \
  -Wl,-soname,libnodlclose.so \
  -o ./libnodlclose.so \
  /tmp/nodlclose.c

file ./libnodlclose.so
```

Observed file class:

```text
ELF 64-bit LSB shared object, x86-64
```

Run:

```sh
LD_PRELOAD=$PWD/libnodlclose.so \
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary

echo "exit=$?"
```

Observed: `exit=0`.

The native ARM loader warns that it cannot preload the x86 library. The guest loader still sees the environment and the distinguishing result occurs inside FEX's x86 execution environment.

## Negative control — bogus preload

```sh
LD_PRELOAD=$PWD/does-not-exist.so \
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary \
  >/tmp/fex-bogus-preload.log 2>&1

echo "exit=$?"
```

Observed: `exit=139`.

This distinguishes the `dlclose` override from the mere presence of `LD_PRELOAD` warnings.

## Unload discriminator 2 — pin only Vulkan guest thunk

SONAME check:

```sh
readelf -d \
  /opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so \
  | grep SONAME
```

Observed:

```text
Library soname: [libvulkan.so.1]
```

Pinned llvmpipe run:

```sh
LD_PRELOAD=/opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so \
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary \
  >/tmp/fex-pinned-vulkan.log 2>&1

echo "exit=$?"
```

Observed: `exit=0`.

## Final Venus control

```sh
LD_PRELOAD=/opt/fex-2608/share/fex-emu/GuestThunks/libvulkan-guest.so \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary \
  >/tmp/fex-venus-pinned.log 2>&1

echo "exit=$?"
grep -E 'deviceName|driverName|driverInfo' /tmp/fex-venus-pinned.log
```

Observed:

```text
exit=0
deviceName = Virtio-GPU Venus (Apple M5)
driverName = venus
driverInfo = Mesa 25.3.6
deviceName = llvmpipe (LLVM 22.1.0, 128 bits)
driverName = llvmpipe
driverInfo = Mesa 25.3.6 (LLVM 22.1.0)
```

## Disk/coredump note

Repeated systemd coredumps filled the VM's 3.9 GiB `/tmp` tmpfs. Root-owned temporary core files were removed with `sudo rm`. A full diagnostic core was retained at:

```text
~/fex-segv-full.core
```

with size approximately 2.0 GiB. Do not copy that core into the repository.

## Result matrix

| Variant | Driver | Callback lookup | Vulkan thunk pinned | Result |
| --- | --- | --- | --- | --- |
| pristine FEX 2608 | default | baseline | no | SIGILL |
| callback-route candidate | llvmpipe | create custom route | no | enumeration succeeds, exit 139 |
| callback-route + destroy instrumentation | llvmpipe | create + tested destroy route | no | destroy native call returns, exit 139 |
| callback-route + no-op guest `dlclose` | llvmpipe | candidate | effectively retained | exit 0 |
| callback-route + bogus preload | llvmpipe | candidate | no | exit 139 |
| callback-route + pinned `libvulkan-guest.so` | llvmpipe | candidate | yes | exit 0 |
| callback-route + pinned `libvulkan-guest.so` | Venus / M5 | candidate | yes | exit 0; Venus enumerated |

## Evidence classification

- `source-read`: FEX `FEX-2608`, current `main`, historical Vulkan callback PR, FEX contribution policy, FEX dispatcher and guest thunk sources.
- `target-executed`: source-built FEX `FEX-2608` on Fedora 44 ARM64 guest under Lima/krunkit, using Fedora x86-64 `vulkaninfo`.
- `integration-executed`: Venus control reaches the Apple M5 virtio-gpu path and exits 0 with the guest thunk pinned.
- Not `full-gate`: no FEX repository-wide test suite or upstream CI was executed for these changes.
