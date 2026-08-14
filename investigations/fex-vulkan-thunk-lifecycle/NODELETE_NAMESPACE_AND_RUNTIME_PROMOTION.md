# NODELETE namespace behavior and runtime promotion option

## Native namespace behavior

A native glibc micro-test on owned branch `ci/agent-r-nodelete-dlmopen-20260814`, commit `fc0617083cb13410c1f436d171c8c81fe3dd8142`, run `31775029885`, job `94688589204` established the static-flag namespace tradeoff.

A normal DSO survived 40 cycles of:

```text
dlmopen(LM_ID_NEWLM) -> dlsym -> call -> dlclose
```

because glibc could recycle the disposable namespace. An otherwise identical `DF_1_NODELETE` DSO accumulated one resident copy per namespace and failed at iteration 15:

```text
COMPLETE path=/tmp/libns-normal.so count=40
FAIL path=/tmp/libns-nodelete.so iteration=15 error=/tmp/libns-nodelete.so: no more namespaces available for dlmopen(): Invalid argument
RESULT normal=40 nodelete=15
```

So unconditional ELF NODELETE has a real namespace-lifetime side effect.

## Real FEX/Vulkan namespace A/B

Owned branch `ci/nodelete-vulkan-dlmopen-fex-20260814`, commit `8d67b14194305a6dd72c603aa3ba7db4cc57fb50`, hosted ARM64 run `31775115421`, job `94688845194`, artifact `9209650000` compared a normal generated Vulkan guest wrapper against the NODELETE candidate under the real FEX runtime and host Vulkan thunk.

The x86 probe repeatedly opened `libvulkan.so.1` in a fresh `LM_ID_NEWLM` namespace, resolved guest `vkGetInstanceProcAddr`, obtained `vkEnumerateInstanceVersion`, called the native PFN through FEX, and closed the namespace.

The **normal** wrapper completed 12 iterations, with glibc reusing the same guest wrapper/invoker addresses each time, then failed before iteration 12 could open because a new libc copy could no longer allocate static TLS:

```text
ITERATION 0 version=4206867 gipa=0x7ffff7ea22b0 pfn=0x7ffff73880f4
...
ITERATION 11 version=4206867 gipa=0x7ffff7ea22b0 pfn=0x7ffff73880f4
DLMOPEN_FAIL iteration=12 error=/lib/x86_64-linux-gnu/libc.so.6: cannot allocate memory in static TLS block
DLMOPEN_RESULT ok=12
```

The **NODELETE** wrapper also completed 12 iterations successfully. Its guest Vulkan copies landed at different addresses in each namespace while the native Vulkan PFN address stayed constant:

```text
ITERATION 0  gipa=0x7ffff7ea22b0 pfn=0x7ffff73880f4
ITERATION 1  gipa=0x7ffff73312b0 pfn=0x7ffff73880f4
ITERATION 2  gipa=0x7ffff6be12b0 pfn=0x7ffff73880f4
...
ITERATION 11 gipa=0x7ffff2ee12b0 pfn=0x7ffff73880f4
DLMOPEN_FAIL iteration=12 error=/lib/x86_64-linux-gnu/libc.so.6: cannot allocate memory in static TLS block
DLMOPEN_RESULT ok=12
```

This means the native 15-namespace NODELETE ceiling does **not** become an earlier failure in this real Vulkan/FEX workload: both variants hit the guest glibc static-TLS limit at 12 first.

The NODELETE arm is also a useful lifetime stress test. Each namespace produced a different guest Vulkan invoker generation, yet the retained native PFN continued to work through all successful iterations because the earlier guest generation remained resident.

## Base-namespace-only runtime promotion

A separate native glibc experiment found a cleaner lifetime primitive that avoids pinning disposable namespaces.

Owned branch `ci/agent-s-runtime-nodelete-promotion-20260814`, commit `9ee1afd31502d18717426bda7d8e9abe976d67f4`, run `31775371984`, job `94689610578` built an ordinary DSO **without** an ELF NODELETE flag. Its constructor:

1. used `dladdr()` to identify its own loaded path;
2. reopened itself with `RTLD_NOLOAD`;
3. queried `RTLD_DI_LMID` with `dlinfo()`;
4. if the object lived in `LM_ID_BASE`, reopened the existing object with `RTLD_NOLOAD | RTLD_NODELETE` and closed the temporary handle.

The base-namespace copy was promoted successfully:

```text
CTOR lmid=0 path=/tmp/libpromote.so
PROMOTE pin=<non-null> err=none
BASE_BEFORE value=1
BASE_AFTER value=2
BASE_NOLOAD handle=<non-null>
```

The same DSO loaded in `LM_ID_NEWLM` observed `lmid=1`, skipped promotion, and recycled cleanly for all 40 iterations:

```text
CTOR lmid=1 path=/tmp/libpromote.so
...
NEWLM_RESULT ok=40
RUNTIME_NODELETE_PROMOTION_OK
```

So glibc supports promoting an already-loaded object to NODELETE at runtime, and the promotion can be conditioned on loader namespace.

## Relevance to a FEX patch

There are now three containment-policy variants worth distinguishing:

### 1. Static NODELETE on every generated shared guest thunk

Pros:
- one tiny CMake change;
- already has extensive build/runtime proof;
- no thunk hot-path cost;
- automatically covers current and future hidden guest-code references.

Cons:
- every namespace copy is pinned;
- changes unload semantics even for simple thunks that do not publish guest executable addresses.

### 2. Static NODELETE on a selected thunk set

Current source audit identifies the strongest existing candidates:
- Vulkan: `LinkAddressToFunction` proc-address mapping plus persistent X11 helper callbacks;
- GL: `LinkAddressToFunction` plus persistent malloc/X11 callbacks;
- CUDA: `LinkAddressToFunction` proc-address mapping;
- Wayland client: custom host-to-guest listener trampolines/unpackers.

ALSA is documented by the thunk README as a non-callback example. EGL's `eglGetProcAddress` delegates to GL's proc-address thunk. Pinning only lifetime-sensitive wrappers reduces semantic reach, but requires maintaining an explicit policy list as thunks evolve.

### 3. Runtime promotion of the base-namespace copy

Pros:
- normal application thunk copy gains process lifetime;
- disposable `LM_ID_NEWLM` copies keep ordinary reclamation;
- could be applied selectively to wrappers that publish persistent cross-ISA pointers.

Cons:
- requires guest-side loader calls (`dladdr`, `dlopen`, `dlinfo`) and glibc/other-libc compatibility decisions;
- may require explicit `libdl` linkage on older glibc targets;
- generic application inside `LOAD_LIB_BASE` would interact poorly with special targets such as the VDSO unless carefully scoped;
- more implementation surface than the one-line ELF policy.

## Current engineering read

The real FEX namespace test weakens the practical `dlmopen` objection to the simple static policy for Vulkan: guest glibc hits a static-TLS ceiling before NODELETE's namespace ceiling.

Runtime base-namespace promotion is technically attractive and now proven at the glibc-loader level, but it earns its extra code only if preserving disposable namespace semantics is considered important enough to justify the compatibility work.

For a near-term containment patch, unconditional or selectively applied static NODELETE remains the lower-risk implementation. Runtime promotion is a credible refinement if maintainers push back specifically on `dlmopen`/namespace lifetime semantics.

All code and CI work described here lives on owned fork/investigation surfaces. No upstream FEX interaction occurred.
