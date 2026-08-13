# Ninth pass: exact no-exec fault and late-consumer analysis

Status: internal Linux Fieldwork record for issue #672. FEX upstream remains read-only. No source changes in this note are presented as upstream contribution material.

Executed runtime revision: FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

Reviewed comparison snapshot: `71afe476751deac24adabd1adb575fd2337b6e0a`.

This pass follows `EIGHTH_PASS_BRIDGE_SURVIVOR.md` and tightens two separate questions:

1. how strong is the retained dead guest RIP as proof of the failed target?;
2. who can consume a Vulkan PFN late enough to expose a retained FEX bridge after `dlclose`?

## 1. The old-thunk RIP is stronger than the generic JIT caveat suggests

`CPUState::rip` carries the general comment that it may not be entirely accurate while JIT execution is active. That warning remains valid for arbitrary asynchronous inspection.

The retained terminal fault is more specific, however.

FEX's decoder checks every instruction fetch against `QueryGuestExecutableRange`. If the first instruction byte at the requested entrypoint is outside an executable guest range, `DecodeInstruction()` returns `NOEXEC_INST`.

Core generation maps `NOEXEC_INST` to `OpDispatchBuilder::NoExecOp()`.

`NoExecOp()` emits a synthetic x86 page fault with:

```text
ErrorRegister = X86_PF_PROT | X86_PF_USER | X86_PF_INSTR
Signal        = SIGSEGV
TrapNumber    = #PF
si_code       = SEGV_ACCERR
```

For x86 this is exactly error code `0x15`, matching the retained terminal record.

`BreakOp()` also writes the failing decoded instruction PC into `CPUState::rip` immediately before emitting the break/fault path.

Therefore the retained pair:

```text
State.rip = 0x7ffff7cd21f0
err_code  = 0x15
```

has a stronger interpretation than a generic stale-JIT-state reading:

> FEX attempted to decode/execute guest code at `0x7ffff7cd21f0`, found that address non-executable in guest VMA state, and synthesized the instruction-fetch page fault for that requested PC.

The generic JIT caveat still argues against claiming an exact machine-instruction boundary from `State.rip` alone. It no longer materially weakens the old-image **target-address** conclusion.

The former guest Vulkan image range and `addr2line`/`objdump` receipt therefore remain high-confidence evidence that the attempted target belongs to generated `CallHostFunction<...>` code in the retired guest thunk.

## 2. `SynchronousFaultData` does not contain an independent fault address

`CpuStateFrame::SynchronousFaultDataStruct` stores only:

```text
FaultToTopAndGeneratedException
Signal
TrapNo
si_code
err_code
```

There is no guest `si_addr` field in that record.

The full retained core should therefore be queried for more than the already-saved `State.rip`:

```text
guest R11
guest RSP
word/return address at guest RSP
host PC / JIT block metadata if recoverable
lookup/link record for the active synthetic PFN
```

R11 remains the best single discriminator because the CustomIR bridge explicitly writes native PFN `H` to guest R11 before exiting toward guest invoker `T`.

## 3. Vulkan-Tools teardown does not expose an obvious legal post-unload PFN consumer

Exact Vulkan-Tools source at the retained cross-check revision uses global raw PFN variables populated by `vkGetInstanceProcAddr`.

`AppInstance::~AppInstance()` performs, in order:

```text
vkDestroyDebugReportCallbackEXT(...)
vkDestroyInstance(...)
unload_vulkan_library() -> dlclose(vulkan_library)
```

In the main execution scope, `AppInstance instance` is declared before the vectors of `AppGpu` and `AppSurface` objects. C++ reverse destruction order therefore destroys surfaces/GPUs before the instance.

`AppGpu::~AppGpu()` calls `vkDestroyDevice`; this happens before `AppInstance::~AppInstance()` reaches `dlclose`.

After the `AppInstance` destructor body calls `dlclose`, its remaining members are ordinary handles, vectors, strings, and `SurfaceExtension` values. `SurfaceExtension` has no custom destructor. The global Vulkan PFN variables are raw pointers with trivial destruction.

This source review finds no ordinary application-owned destructor that should legally invoke a Vulkan PFN after the Vulkan library is closed.

### Consequence

The source-level survivor `H -> T` remains a strong owner candidate because `T` is hidden inside FEX's dynamic-PFN machinery and is not normally returned directly to the application.

But the phrase “later application call to H after dlclose” is now too casual. The exact trigger still requires evidence.

Plausible trigger classes now rank as:

1. **FEX bridge/link state consumed during or immediately around loader return/unload** — strong owner fit, trigger unproved.
2. **An in-flight or concurrent bridge use that selected `H` before retirement and reaches `T` after physical unmap** — source race exists; runtime concurrency unproved.
3. **A hidden application/loader path retaining native PFN `H` outside the obvious Vulkan-Tools object lifetime** — possible, no source owner found yet.
4. **Direct stale guest pointer to `T`** — destination fits, provenance is weak because `T` is normally hidden in FEX registration state.
5. **Host-to-guest callback trampoline** — generic stale-address bug exists, but its first dead guest destination should normally be `CallbackUnpack`, which fits the observed `CallHostFunction` target less well.

The runtime goal is therefore no longer merely “show a CustomIR handler lookup after unmap.” The better receipt is:

```text
which live/synthetic entry selected T?
what was R11 at the generated no-exec fault?
what guest return/caller address was on the stack?
was an H bridge already selected before unmap?
```

## 4. Eighth-pass compiled-bridge refinement remains valid

Target-range invalidation at `T` can erase the compiled block for `T` and delink inbound direct JIT links.

It still cannot discover the compiled CustomIR bridge at synthetic key `H`, because that block is generated with `NeedsAddGuestCodeRanges = false` and therefore has no `CodePages` dependency on the guest page containing `T`.

The compiled `H` bridge can retain an `ExitFunctionLinkData::GuestRIP = T` after inbound direct linking to `T` is removed.

Thus a post-unload **CustomIR handler re-hit is not necessary** for stale bridge state to be executable. A previously compiled `H` block is a separate holder from `CustomIRHandlers[H]`.

Any retirement experiment must remove both:

```text
CustomIR registration H -> T
compiled synthetic lookup/cache entry H
```

and must begin before the actual host `munmap` removes `T`.

## 5. Hosted callback CI artifact: earlier diagnosis corrected

The hosted ARM64 callback workflow run `31727031022` completed as a workflow, but every FEX callback case returned status `132`.

Downloaded artifact `fex-vulkan-callback-probe-31727031022` shows:

```text
baseline-report=132
baseline-utils=132
candidate-report=132
family-report=132
family-utils=132
report-candidate-utils-control=132
```

Every corresponding FEX probe log is empty.

Native ARM64 software-Vulkan controls in the same artifact succeed and invoke their callbacks.

The candidate `Host.cpp` retained in the artifact does contain both diagnostic lookup additions, so “candidate source was never generated” is eliminated.

### First-marker boundary

The callback probe's first FEX-side marker is printed only **after**:

```text
dlopen(libvulkan.so.1)
dlsym(vkGetInstanceProcAddr)
dlsym(vkCreateInstance)
vkCreateInstance(...)
```

Therefore empty logs mean the hosted failure occurs somewhere in that prefix. They do not prove that the process dies before `dlopen` or before thunk `OnInit`.

The earlier guess that missing X11 packages alone explained status 132 is not established by the artifact.

### Thunk-config misuse found in that workflow

FEX's own `ThunkFunctionalTests` runs Vulkan with:

```text
FEX_THUNKCONFIG=Data/CI/VulkanThunks.json
```

and that enablement file is simply:

```json
{
  "ThunksDB": {
    "Vulkan": 1
  }
}
```

The hosted workflow instead sets `FEX_THUNKCONFIG` to the installed `ThunksDB.json` file.

Those two files have different purposes in FEX:

- installed `ThunksDB.json` is the library database. `FileManager::LoadThunkDatabase()` expects its `DB` object and uses it for guest overlays/dependencies;
- `FEX_THUNKCONFIG` is scanned as an application/config source for a `ThunksDB` enablement object.

So the hosted harness does not follow FEX's own tested configuration convention.

This is a concrete harness defect and should be fixed before interpreting hosted callback results.

A new owned-repository workflow edit was attempted to create a corrected unload discriminator, but the repository-write connector rejected the workflow creation because it could not determine the safety status of that request. No repeated bypass attempt was made. No FEX upstream write occurred.

## 6. Best next target-side core queries

The retained core at `~/fex-segv-full.core` is now the shortest route to the missing edge.

Useful GDB queries, to be run against the exact retained FEX executable/debug symbols:

```gdb
set $f = (FEXCore::Core::CpuStateFrame*)$x28
p/x $f->State.rip
p/x $f->State.gregs[FEXCore::X86State::REG_R11]
p/x $f->State.gregs[FEXCore::X86State::REG_RSP]
x/8gx $f->State.gregs[FEXCore::X86State::REG_RSP]
p $f->SynchronousFaultData
```

Then compare guest R11 against every native PFN `H` registered for a Vulkan `CallHostFunction` target in the old image.

If the original process/core contains no retained registration log, inspect the corresponding CustomIR/lookup objects in the core if symbols and containers remain readable. Otherwise rerun with registration logging.

### Strong outcomes

**R11 is a known Vulkan native PFN H**

This strongly identifies `AddThunkTrampolineIRHandler` as the immediate route because its generated bridge explicitly loads H into R11 before selecting T.

**R11 is unrelated / normal ABI value**

Demote dynamic-PFN CustomIR as immediate route and inspect guest stack/return address for a direct stale guest transfer.

**R11 cannot be recovered reliably**

Use a target rerun that logs bridge execution and the no-exec translation request. The eighth-pass refinement means the trace must log execution of already-compiled synthetic H blocks, not only `CustomIRHandlers.find()` during generation.

## 7. Regression implication

The legal regression should not rely on calling a saved PFN after its owning library has been closed.

The stronger lifecycle test is:

```text
load generation A
obtain dynamic PFN H
call H successfully
close A completely
force generation B to a different guest base
load B
reacquire the same host PFN H
register its new guest invoker T2
call the fresh PFN through B
expect clean execution through T2
```

This catches stale `H -> T1` ownership without requiring invalid application behavior.

A separate mechanism-only negative probe may deliberately call the old PFN after close to demonstrate what stale bridge state does, but it should remain labeled as a diagnostic misuse probe rather than the correctness regression.

## Exact uncertainty after ninth pass

Established strongly from source plus retained execution:

- the terminal FEX-generated fault is the `NoExecOp` instruction-fetch page-fault class;
- its `State.rip` is explicitly set from the failed decoded guest PC;
- that PC lies in the retired Vulkan guest-thunk image and resolves inside `CallHostFunction<...>`;
- ordinary Vulkan-Tools object teardown provides no obvious legal PFN call after `dlclose`;
- FEX retains both registration and compiled-bridge state capable of naming the old target;
- the hosted callback CI result is not a valid callback differential and has a concrete thunk-config harness error.

Still missing:

- guest R11 at the retained terminal fault;
- the immediate caller/return address that selected the old T;
- proof of whether H was selected before or after physical unmap;
- proof of guest-thread concurrency at that boundary;
- a legal forced-moved-base unload/reload runtime result.

Those remaining questions are narrow enough that another broad source survey is lower value than the retained-core register/stack read or a corrected execution harness.
