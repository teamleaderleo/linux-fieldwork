# NODELETE retained-memory stock/candidate A/B

Date: 2026-08-14

## Question

The ELF build matrix showed that all eight current 64-bit generated guest wrappers contain about 1.69 MiB of aggregate `PT_LOAD` memory, but that is not the same as real post-`dlclose()` process cost.

This A/B measures the incremental process residency of the NODELETE policy after ordinary guest handles have all been closed.

## Test identity

Owned FEX branch: `diagnostic/nodelete-rss-ab-20260814`.

Carrier commit: `bd16151de9ea2a380306384827fcfdfbd22e0b43`.

Hosted ARM64 run: `31777233924`.

Artifact: `nodelete-rss-ab-31777233924`.

Artifact digest:

```text
sha256:1453389c4688f84e3584dbf4279292e6b239b6ea1f78a28001d0e77696ec6fa0
```

The workflow builds one FEX runtime and the real host thunks for six product wrappers, then builds byte-equivalent guest thunk sets differing only in the generic `-z,nodelete` policy:

- ALSA
- Vulkan
- DRM
- Wayland client
- GL
- EGL

CUDA is excluded because the hosted runner has no real CUDA host driver. VDSO is excluded because it is not an ordinary `dlopen`/`dlclose` product DSO.

## Probe

Each A/B arm starts a fresh FEX process and records `/proc/self/smaps_rollup` plus target-library mapping bytes at three points:

```text
baseline
all six wrappers loaded
all six handles closed in reverse order
```

The probe also checks `RTLD_NOLOAD` for every guest SONAME before and after close.

Because FEX's host/native thunk side is process-resident in both variants, the useful comparison is the **difference between NODELETE and stock after all guest handles have closed**, not the absolute post-load process size.

## Stock result

Baseline:

```text
rss_kb=15636
pss_kb=11649
thunk_map_bytes=0
thunk_map_count=0
```

All six guest wrappers loaded:

```text
rss_kb=29648
pss_kb=25307
thunk_map_bytes=4902912
thunk_map_count=51
```

After closing all six handles:

```text
rss_kb=28248
pss_kb=23907
thunk_map_bytes=3231744
thunk_map_count=20
```

Every guest SONAME is absent from guest loader `RTLD_NOLOAD` lookup after close:

```text
libasound.so.2                 resident=0
libvulkan.so.1                 resident=0
libdrm.so.2                    resident=0
libwayland-client.so.0.20.0    resident=0
libGL.so.1                     resident=0
libEGL.so.1                    resident=0
```

The remaining target-named mappings in the process are therefore not live guest loader handles for those wrappers. They include the already-persistent host/native side and related mappings visible through the emulated process map view.

Baseline-adjusted stock post-close memory:

```text
STOCK_AFTER_MINUS_BASE_RSS_KB=12612
STOCK_AFTER_MINUS_BASE_PSS_KB=12258
```

## NODELETE result

Baseline:

```text
rss_kb=15628
pss_kb=11641
thunk_map_bytes=0
thunk_map_count=0
```

All six guest wrappers loaded:

```text
rss_kb=30660
pss_kb=26319
thunk_map_bytes=4902912
thunk_map_count=51
```

After closing all six handles:

```text
rss_kb=30800
pss_kb=26459
thunk_map_bytes=4902912
thunk_map_count=51
```

Every guest SONAME remains discoverable with `RTLD_NOLOAD`, as expected for NODELETE:

```text
libasound.so.2                 resident=1
libvulkan.so.1                 resident=1
libdrm.so.2                    resident=1
libwayland-client.so.0.20.0    resident=1
libGL.so.1                     resident=1
libEGL.so.1                    resident=1
```

Baseline-adjusted NODELETE post-close memory:

```text
NODELETE_AFTER_MINUS_BASE_RSS_KB=15172
NODELETE_AFTER_MINUS_BASE_PSS_KB=14818
```

## Incremental measured cost

The direct stock/candidate difference after logical unload is:

```text
NODELETE_MINUS_STOCK_AFTER_RSS_KB=2560
NODELETE_MINUS_STOCK_AFTER_PSS_KB=2560
```

Target-named mapping difference:

```text
stock after-close map bytes    = 3231744
NODELETE after-close map bytes = 4902912
difference                     = 1671168 bytes
```

and mapping count difference:

```text
stock after-close count    = 20
NODELETE after-close count = 51
difference                 = 31 mappings
```

The approximately 1.59 MiB extra target-library virtual mapping is close to the loadable guest-wrapper footprint expected for these six wrappers. The approximately 2.5 MiB extra RSS/PSS is the stronger practical number from this one hosted run: it includes the resident wrapper pages actually faulted in plus loader/static/allocator effects attributable to keeping the guest generation alive.

## Interpretation

This is evidence **against** the strongest memory-cost objection to whole-wrapper NODELETE.

The incremental retained cost for six real guest wrappers in this workload is measured in a few MiB, not the roughly 10 MiB aggregate ELF file size and not the full host/native thunk footprint. The host/native side remains process-resident in stock FEX too.

That does not make the cost free. A process that touches more wrapper code/data, uses additional guest dependencies, or loads future larger thunks can retain more RSS than this probe.

The result therefore supports the bounded statement:

> On this hosted ARM64 six-wrapper workload, generic guest-wrapper NODELETE costs about 2.5 MiB of additional post-close RSS/PSS relative to stock, while eliminating the guest executable reclamation event that causes the proven thunk lifetime failures.

## Important caveats

1. This is one hosted run, not a statistical distribution. RSS/PSS can move with allocator and page-cache behavior.
2. CUDA and VDSO are not part of the runtime A/B.
3. The target-name mapping sum is intentionally not interpreted as guest-only memory because FEX's emulated `/proc/self/maps` view can expose persistent host/native library mappings with the same SONAME family.
4. The `RTLD_NOLOAD` result is the discriminator for guest loader residency: stock reports all six absent after close; NODELETE reports all six resident.
5. Vulkan manually opens guest X11 in `OnInit()`, so some dependency state is already process-retained even in the stock arm. This A/B naturally includes that existing asymmetry.
6. The result measures a process that loads each wrapper but does not exercise every API path. Heavier workloads can fault in more pages.

## Policy implication

The remaining whole-wrapper NODELETE objections are now primarily semantic/compatibility questions rather than an unbounded memory concern:

- whether any application requires the FEX guest wrapper mapping to physically disappear;
- whether any thunk requires wrapper constructor/destructor/TLS reset on logical reopen;
- whether disposable loader namespaces need reclaimable copies.

A split resident bridge still provides the clean fallback if a real wrapper demonstrates that physical reset is necessary.

All code and CI work described here is confined to owned repositories/forks. No upstream FEX interaction occurred.
