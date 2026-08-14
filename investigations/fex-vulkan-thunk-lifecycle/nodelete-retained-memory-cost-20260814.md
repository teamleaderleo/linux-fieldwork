# Whole-wrapper NODELETE retained-memory cost — 2026-08-14

## Purpose

Whole-wrapper `DF_1_NODELETE` is a useful containment/reference configuration for the thunk lifetime bug, but the preferred unload-preserving design is a small per-library resident executable companion. This note gives the existing measured cost of pinning whole guest thunk wrappers so that comparison is quantitative.

Source branch: `teamleaderleo/FEX:diagnostic/nodelete-rss-ab-20260814`

Workflow run: `31777233924` — success.

The probe builds and loads six 64-bit guest thunk wrappers in two configurations:

- stock unload policy;
- whole-wrapper NODELETE.

Libraries:

- asound
- vulkan
- drm
- wayland-client
- GL
- EGL

All six wrappers are opened, memory is sampled, all handles are closed, memory is sampled again, and `RTLD_NOLOAD` checks record whether each wrapper remains resident.

## After-close result

Artifact `summary.txt`:

```
STOCK_AFTER_MINUS_BASE_RSS_KB=12612
STOCK_AFTER_MINUS_BASE_PSS_KB=12258
STOCK_AFTER_THUNK_MAP_BYTES=3231744
STOCK_AFTER_THUNK_MAP_COUNT=20
NODELETE_AFTER_MINUS_BASE_RSS_KB=15172
NODELETE_AFTER_MINUS_BASE_PSS_KB=14818
NODELETE_AFTER_THUNK_MAP_BYTES=4902912
NODELETE_AFTER_THUNK_MAP_COUNT=51
NODELETE_MINUS_STOCK_AFTER_RSS_KB=2560
NODELETE_MINUS_STOCK_AFTER_PSS_KB=2560
```

Derived mapping delta:

```
4902912 - 3231744 = 1671168 bytes = 1.59375 MiB
51 - 20 = 31 additional thunk mappings
```

So in this six-wrapper probe, keeping every wrapper NODELETE after all guest handles close adds:

- **2.5 MiB RSS** relative to stock after-close state;
- **2.5 MiB PSS**;
- **1.594 MiB mapped thunk VA**;
- **31 additional thunk mappings**.

## Residency check

Stock after close:

```
NOLOAD after_close lib=libasound.so.2 resident=0
NOLOAD after_close lib=libvulkan.so.1 resident=0
NOLOAD after_close lib=libdrm.so.2 resident=0
NOLOAD after_close lib=libwayland-client.so.0.20.0 resident=0
NOLOAD after_close lib=libGL.so.1 resident=0
NOLOAD after_close lib=libEGL.so.1 resident=0
```

NODELETE after close:

```
NOLOAD after_close lib=libasound.so.2 resident=1
NOLOAD after_close lib=libvulkan.so.1 resident=1
NOLOAD after_close lib=libdrm.so.2 resident=1
NOLOAD after_close lib=libwayland-client.so.0.20.0 resident=1
NOLOAD after_close lib=libGL.so.1 resident=1
NOLOAD after_close lib=libEGL.so.1 resident=1
```

This confirms the measured delta corresponds to keeping the wrappers resident, not merely allocator noise around an equivalent unload state.

## Comparison to the resident-companion direction

The measurement does **not** directly predict the RSS of the final per-library bridge design because pages, relocation dirtiness, sharing, and which libraries actually need companions all affect process RSS.

It does establish the cost direction: whole-wrapper NODELETE retains ordinary wrapper text/data/state that the lifetime fix does not require.

For one concrete comparison, the generalized 64-bit Wayland split has the following `size` receipt:

```
   text   data  bss    dec
  21368   1000    8  22376   ordinary unloadable wrapper
  10713    872    8  11593   NODELETE resident bridge
```

The resident Wayland unit is therefore a small executable companion rather than a reason to keep the whole wrapper resident. The same ownership principle applies to generated caller/unpacker bridges in Vulkan, GL, CUDA, and DRM.

## Design consequence

Use whole-wrapper NODELETE as:

- a containment/reference behavior;
- a diagnostic A/B;
- a fallback if a library's escaping executable family has not yet been split correctly.

Do not make it the default lifetime architecture when the escaped executable family can be identified and isolated in a per-library companion.

A future cost gate should measure an actual multi-library resident-companion set under the same probe so the final comparison is:

```
stock unload
vs whole-wrapper NODELETE
vs per-library resident companions
```

using identical load/close cycles and memory accounting.
