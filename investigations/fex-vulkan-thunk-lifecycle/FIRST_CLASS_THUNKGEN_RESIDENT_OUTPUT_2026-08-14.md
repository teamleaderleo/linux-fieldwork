# First-class thunkgen resident output and direction-aware callback generation

Date: 2026-08-14

This checkpoint advances Finding B's resident executable companion from a generated-postprocessor experiment into a first-class thunkgen generation design, while preserving the already-proven unload and retained-call behavior.

The key result is that a **single thunkgen analysis/invocation** can emit:

1. the normal unloadable guest wrapper inl;
2. the resident guest-to-host function-pointer invoker inl;
3. typed wrapper accessors into that resident companion.

A follow-up direction-aware candidate uses thunkgen's existing callback analysis to emit resident host-to-guest `CallbackUnpack` entrypoints **only** for signatures that actually appear as ordinary generated callback parameters. This removes the temporary signature-arity heuristic used by the Python extractor prototype.

All work described here is on owned FEX diagnostic branches and Linux Fieldwork. It is evidence/candidate work, not an upstream-submittable FEX patch.

---

## Starting point: extractor-derived GL proof

The earlier generator-derived GL bridge used `ThunkLibs/Generator/extract_guest_bridge.py` to parse the normal generated guest inl and derive a resident companion from the same `MAKE_CALLBACK_THUNK(...)` set.

That path established the real GL runtime baseline:

- normal generated GL signature set: **736** entries;
- resident generated GL signature set: **736** entries;
- exact normalized equality;
- ordinary `libGL.so.1` wrapper physically unloads;
- resident `libfex-GL-bridge.so` remains mapped with `NODELETE`;
- retained `glGetError` native H remains callable after wrapper close;
- forced reload moves the wrapper while native H remains identical;
- retained `glXQueryExtension` remains callable after wrapper close and traverses FEX's X11 callback path through resident guest executable code.

Baseline run:

- run `31784431283`
- job `94717085534`
- marker `DERIVED_GL_BRIDGE_OK`
- artifact ZIP SHA256 `9a361ceb29003cb6276e916925dc5006b7b5152b1da2c781ff497451c4f89977`

Post-unload GLX callback run:

- run `31784704359`
- job `94717922331`
- artifact ID `9213145070`
- artifact ZIP SHA256 `538fa5d261c56d2d0ee0b493d206e911ee8674371aa8155a78de3f18d57dcd24`

Its decisive post-close sequence included:

```text
UNMAPPED 0x7ffff7bd03a0
RETAINED_AFTER_CLOSE error=0
POST_CLOSE_GLX_BEGIN H=0x7ffff7307810 display=0x5615261388a0
GUEST_XSYNC display=0x5615261388a0 discard=0
GUEST_XDISPLAYSTRING display=0x5615261388a0
POST_CLOSE_GLX_END rc=1 error=158 event=95
DERIVED_GLX_CALLBACK_AFTER_CLOSE_OK
GEN2 get_old=0x7ffff7bd03a0 get_new=0x7ffff70403a0 moved=1 H_old=0x7ffff73bd680 H_new=0x7ffff73bd680 same_H=1 bridge=1
FINAL_RETAINED error=0
DERIVED_GL_BRIDGE_OK
GLX_CALLBACK_MARKER_ORDER_OK
```

The guest probe independently held `libX11.so.6` open. That preserves the guest X11 targets and isolates the lifetime of the GL-wrapper-owned callback-unpacker code moved into the resident companion.

---

## First-class resident-output candidate

Owned FEX branch:

- `diagnostic/thunkgen-resident-output-v1`

Diagnostic source transformers on the branch:

- `ThunkLibs/Generator/apply_resident_output_candidate.py`
- `ThunkLibs/Generator/apply_resident_output_candidate_fixups.py`

The candidate adds a guest-resident generation mode to thunkgen and extends its output description with two sibling outputs:

- resident bridge definitions;
- typed resident accessors.

The important implementation property is that the normal guest output and resident outputs are generated during the **same thunkgen invocation from the same analysis result**. Runtime function-pointer signatures are deduplicated once, assigned one callback index, and reused by both outputs.

The GL CMake diagnostic wiring uses `generate(... RESIDENT_BRIDGE)` so one generator command declares all three outputs. The ordinary wrapper links to the resident companion, while only the companion receives `-z,nodelete`.

### Hard postprocessor-elimination discriminator

The CI acceptance test deliberately deletes:

`ThunkLibs/Generator/extract_guest_bridge.py`

**before guest configure/build**.

Therefore a passing guest build cannot silently fall back to the extractor.

### First-class build result

Workflow:

- run `31785499136`
- job `94720375898`
- carrier `ae29bf2fb4d8cebe4e9d4ceb1237d8df50d03fd6`

Results:

- thunkgen builds successfully;
- old extractor is absent before guest configure;
- one invocation emits normal guest, resident bridge, and resident accessors;
- GL normal generated set: **736**;
- GL resident generated set: **736**;
- exact normalized equality;
- wrapper has no `NODELETE`;
- wrapper has `NEEDED libfex-GL-bridge.so`;
- bridge has `NODELETE`;
- bridge ELF size: **2,578,104 bytes**;
- marker `FIRST_CLASS_THUNKGEN_RESIDENT_BUILD_OK`.

Artifact:

- artifact ID `9213442302`
- artifact ZIP SHA256 `6be38da1517179fe77ae16afb567cc0b3f260e7568c73fdd274ef96ca2df0e27`

### First-class runtime result

Workflow:

- run `31785908894`
- job `94721635034`
- carrier `f4bcf594528fb842c761ca3deb55769fcc95b632`

The exact previously-proven GL lifetime discriminator remained green with the extractor absent:

```text
GEN1 get=0x7ffff7bd03a0 H=0x7ffff73bd680 glxH=0x7ffff7307810 error=0 bridge=1
UNMAPPED 0x7ffff7bd03a0
RETAINED_AFTER_CLOSE error=0
POST_CLOSE_GLX_BEGIN H=0x7ffff7307810 display=0x562baa9078a0
GUEST_XSYNC display=0x562baa9078a0 discard=0
GUEST_XDISPLAYSTRING display=0x562baa9078a0
POST_CLOSE_GLX_END rc=1 error=158 event=95
FIRST_CLASS_GLX_CALLBACK_AFTER_CLOSE_OK
GEN2 get_old=0x7ffff7bd03a0 get_new=0x7ffff70403a0 moved=1 H_old=0x7ffff73bd680 H_new=0x7ffff73bd680 same_H=1 bridge=1
FINAL_RETAINED error=0
FIRST_CLASS_THUNKGEN_RESIDENT_RUNTIME_OK
FIRST_CLASS_GLX_CALLBACK_MARKER_ORDER_OK
```

Artifact:

- artifact ID `9213598761`
- artifact ZIP SHA256 `53cd0bf40a613768106a5340080ae0cca223cbe4216a5271103fa14486d6af29`

This proves the postprocessor is unnecessary for the validated GL resident-bridge mechanism.

---

## Direction-aware resident callback generation

The first-class v1 bridge still emitted a resident callback-unpacker accessor/export for every runtime function-pointer signature. GL exposed why that is too broad: some signatures are valid guest-to-host dynamic PFNs but have argument counts that FEX's host-to-guest packed-callback machinery does not support, because that direction is never required for those signatures.

A temporary extractor-era workaround inferred callback eligibility from signature arity. The stronger design uses semantics already discovered by thunkgen.

Diagnostic transformer:

- `ThunkLibs/Generator/apply_resident_direction_candidate.py`

### Analysis change

Thunkgen already discovers ordinary generated callback parameters while processing functions. The candidate records those callback keys in:

`host_to_guest_callback_funcptrs`

For each deduplicated runtime function-pointer signature, the resident entry records:

`used_as_callback`

If the same canonical signature appears both as a guest-to-host runtime PFN and as a real host-to-guest callback, callback use is ORed across deduplication.

Generation then becomes:

- **all** deduplicated runtime function-pointer signatures receive resident guest-to-host invokers;
- only `used_as_callback` signatures receive resident `CallbackUnpack` exports and typed unpacker accessors.

The candidate removes:

- `FEXResidentBridgeCanUnpack`;
- the temporary `sizeof...(Args) <= 19 || sizeof...(Args) == 24` policy;
- eager unpacker generation for signatures used only in guest-to-host direction.

Requesting a resident callback unpacker for a signature that analysis never identified as a generated callback has no generated specialization and therefore fails at compile time.

---

## Direction-aware GL result

GL's ordinary generated interface has **zero ordinary generated callback parameters**. Its relevant post-close X11 callbacks are custom raw escape points handled explicitly by the GL resident bridge helper code.

That gives an important zero-case for the direction-aware generator.

### Build

Workflow:

- run `31786448410`
- job `94723318420`
- carrier `82ab19fd70b526129b1740b152dc8b16e46943e1`

Results:

- normal GL runtime-PFN signatures: **736**;
- resident invoker signatures: **736**;
- exact normalized equality;
- generated resident unpacker exports: **0**;
- generated resident unpacker accessors: **0**;
- arity heuristic absent;
- wrapper/bridge ELF lifetime policy preserved;
- direction-aware bridge ELF size: **1,281,728 bytes**.

The earlier eager bridge was **2,578,104 bytes**, so semantic direction selection removes about half of the resident GL ELF while preserving the complete 736-signature guest-to-host set.

Products:

- bridge generated inl SHA256 `8e273e08607c9df9967004eaf140bdc35ebeb00c9a3e94dc07802e8113d0e8e6`
- bridge accessors SHA256 `a48f507a04dcddef16b051aa24b095472c591e3371e1327858282e0c3301f7ca`
- bridge ELF SHA256 `79f6b9ce2a42d19883a576c4bab51b8e18f422fb04beac1acdf37ec704ea9ffd`

Artifact:

- artifact ID `9213792865`
- artifact ZIP SHA256 `205e0fab2ee0533002d5a964ebb3ef34c4fff492467dc7fd8480f5ddf6a94c20`

Marker:

- `DIRECTION_AWARE_RESIDENT_BUILD_OK`

### Runtime

Workflow:

- run `31786517623`
- job `94723539790`
- carrier `ea08eade4650bd0121ab77a4ba72e1650c0d730c`

Results remain fully green with:

- **736 / 736** exact dynamic-PFN set;
- **0** ordinary generated unpackers;
- resident bridge **1,281,728 bytes**;
- physical wrapper unmap;
- retained `glGetError` after close;
- post-close retained `glXQueryExtension` crossing through explicit resident X11 unpackers to guest `XSync` and `XDisplayString`;
- forced wrapper movement;
- `moved=1 same_H=1`;
- final retained H call.

Markers:

- `FIRST_CLASS_GLX_CALLBACK_AFTER_CLOSE_OK`
- `FIRST_CLASS_THUNKGEN_RESIDENT_RUNTIME_OK`
- `FIRST_CLASS_GLX_CALLBACK_MARKER_ORDER_OK`

Artifact:

- artifact ID `9213839670`
- artifact ZIP SHA256 `edf479d530caf4732a62fe5bb93313a31a5da0e75eb7d51ae24d128e1e1b51d4`

This demonstrates that GL does not need broad generated host-to-guest unpacker coverage for its 736 runtime PFN signatures. Its custom X11 escape points remain explicit and still satisfy the post-unload callback lifetime test.

---

## Vulkan one-pass direction result

The Vulkan resident bridge was also converted experimentally from the Python extractor to the same first-class `RESIDENT_BRIDGE` generation mode.

Diagnostic transformer:

- `ThunkLibs/Generator/apply_resident_vulkan_first_class_candidate.py`

The one-pass Vulkan product build reached:

- normal generated Vulkan runtime-PFN signatures: **476**;
- resident generated invoker signatures: **476**;
- exact normalized equality;
- generated ordinary resident callback unpacker exports: **0**;
- generated ordinary resident callback unpacker accessors: **0**.

The initial workflow asserted a positive unpacker count and therefore reported failure after the products had already built. The zero result is semantically consistent with the Vulkan interface: callback paths relevant to the current lifetime investigation are custom-host/custom raw escape paths rather than ordinary generated callback parameters.

A clean carrier now asserts zero for Vulkan and retains the 476/476 equality gate.

The existing completed generator-derived Vulkan runtime proof remains the stronger behavioral evidence for Vulkan itself:

- 476/476 generated signature equality;
- dynamic `vkEnumerateInstanceVersion` retained after wrapper unmap;
- real X11 callback path retained after wrapper unmap;
- forced wrapper movement;
- same native H;
- marker `DERIVED_VULKAN_BRIDGE_RUNTIME_OK`.

This first-class work changes how the resident outputs are produced; it does not replace that earlier Vulkan runtime proof.

---

## Positive callback-direction control

Because both GL and Vulkan produce zero ordinary generated callback unpackers, a dedicated synthetic positive control was added to prove that the analysis bit actually selects a normal callback signature.

Workflow:

- run `31787344277`
- job `94726123816`
- carrier `5795c19d21f1b4f425f0ccd88ea3e1cbfaec0516`

The fixture adds one ordinary generated callback parameter to `libfex_thunk_test`:

```cpp
using ResidentDirectionCallback = uint32_t (*)(uint32_t);
uint32_t InvokeResidentDirectionCallback(ResidentDirectionCallback callback, uint32_t value);
```

The workflow applies the first-class and direction-aware generator candidates, deletes the Python extractor, enables resident output for the fixture, builds the generated guest output, and asserts the resident callback subset.

Result:

```text
resident-unpacker-count = 1
accessor-unpacker-count = 1
...fex_bridge_libfex_thunk_test_unpacker_0()...
POSITIVE_DIRECTION_RESIDENT_UNPACKER_OK
```

The generated resident output contains exactly:

- **1** resident unpacker export;
- **1** typed unpacker accessor.

The arity helper and arity heuristic are absent.

Artifact:

- artifact ID `9214124685`
- artifact ZIP SHA256 `a7e757a4b32dff858e51ebe8ae474fbedcecfddc31c44ee45a27dc8fcf89aa57`

Together with the real GL/Vulkan zero-cases, this proves callback-direction selection is driven by thunkgen's semantic analysis rather than function-name matching or signature arity.

---

## Current generator judgment

The strongest production direction is now:

1. run normal thunkgen interface analysis **once**;
2. deduplicate runtime function-pointer signatures once and preserve one callback numbering;
3. emit the ordinary guest wrapper output;
4. emit resident guest-to-host invokers for the full runtime function-pointer signature set;
5. emit resident host-to-guest unpackers only for signatures analysis identified as ordinary generated callbacks;
6. have the unloadable wrapper use typed generated accessors into the resident companion;
7. keep custom raw escape points explicit when they are invisible to normal thunkgen analysis.

For GL and Vulkan today, the X11 setters/helpers are examples of custom persistent escape points that remain explicit. A small explicit resident escaped-signature/type declaration mechanism is preferable to a giant manually maintained PFN list.

The Python extractor has served its diagnostic purpose. The validated first-class paths can build and run with it deleted before guest configure.

The temporary arity-based callback policy has likewise served its diagnostic purpose. Direction-aware generation replaces it with analysis semantics and has both zero and positive controls.

---

## Relationship to the separate CustomIR cache-retirement defect

This generator/resident-companion work addresses **escaped guest executable lifetime**: executable addresses already published into persistent host/native state remain legal after the ordinary wrapper unloads.

The CustomIR cache-retirement defect remains independent. When a stable host address H must be rebound from old guest target T1 to new guest target T2, FEX must retire any already-compiled redirect for H. Exact-entry eviction and synthetic range indexing have independently proven that owner.

A robust unloadable-wrapper design can need both repairs:

- resident executable ownership for already-published executable addresses;
- CustomIR retirement for future H -> T rebinding.

They should keep separate claims and tests.

---

## Execution boundary

These results are hosted ARM64 mechanism proof. They establish:

- physical wrapper unmap;
- resident executable survival;
- retained dynamic PFNs;
- retained callback traversal;
- forced wrapper relocation;
- stable native H across moved guest generations;
- one-pass resident generation;
- semantic callback-direction selection.

They do not claim an instruction-for-instruction replay of the original Apple M5 final teardown edge. That historical boundary remains explicit.