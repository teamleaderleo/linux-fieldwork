# FEX thunk lifetime — design philosophy and falsifiable experiment ladder

## TL;DR

The teardown failure is useful because it exposes a design contract that FEX has never had to state cleanly:

> Are generated guest thunk DSOs ordinary unloadable guest libraries, or are they process-owned ABI adapters whose executable code may legitimately outlive the guest application's logical `dlclose()`?

That question should be answered before implementing a large unload/reload mechanism.

The current evidence supports three increasingly expensive policies:

1. **Process-resident bridge owners** — keep selected guest thunk images physically resident when their code addresses are published into long-lived FEX bridge state. The Vulkan `DF_1_NODELETE` experiment is the smallest form of this policy.
2. **Explicit bridge retirement** — retain ownership metadata and remove every bridge that can reach a retiring guest image before its pages disappear.
3. **Full generation-aware unload/reload** — combine ownership, rebinding, cache invalidation, and execution draining so the image can truly unmap and later reload at another base.

A fourth architecture is worth prototyping if true unload semantics are required: move the callable guest-side bridge entry itself into a process-owned stable executable arena, and let that stable entry dispatch through generation-aware metadata to unloadable library-specific code. This resembles an idea discussed during the original host-function-pointer design review: generated/copyable function-pointer wrappers plus explicit host↔guest maps rather than treating the native host pointer itself as a permanent guest entrypoint.

The immediate next experiments are deliberately falsifiable. Each one has a result that would make us abandon or demote a hypothesis.

## Why the current design is understandable

FEX documents thunklibs as **special guest libraries that call host code for speed and compatibility**, supporting both guest→host calls and host→guest callbacks. At FEX-2608 the same documentation says there are no unit tests for the guest libraries themselves, only for `OP_THUNK`.

That combination explains a lot about the present implementation:

- the important steady-state path is a fast cross-architecture call;
- generated guest code is treated as an implementation vehicle for those calls;
- host-side thunk state is process-owned and naturally long-lived;
- guest ELF load/unload remains delegated to the ordinary guest loader;
- teardown/reload of the generated guest wrapper image has little direct test coverage.

Source: `ThunkLibs/README.md` at FEX-2608.

The dynamic-function-pointer feature then adds another performance-oriented choice. Vulkan and GL APIs return callable function pointers at runtime. FEX lets the guest receive the native host function address `H`, while a CustomIR registration tells FEX that guest execution at `H` should jump to generated guest helper `T` first:

```text
application-visible pointer: H
FEX registration:           H -> T
T:                          guest CallHostFunction body
```

This avoids requiring the application to receive a separately allocated guest wrapper address for every native PFN. It also lets FEX intercept a host address directly at the guest PC boundary.

The cost is hidden lifetime coupling: `H` can remain valid for the process while `T` lives in an ordinary guest DSO that the guest loader may unmap.

The original 2022 design discussion recognized adjacent complications. Review discussion considered a different model using function-pointer wrappers generated from canonical code with explicit host:guest and guest:host maps, while noting that such a model would perform lookups during pointer marshaling and would stop treating host pointers as directly guest-callable. The same review also called out the collision case where one native host pointer can correspond to different guest thunk targets in different libraries.

External history:

- `https://redirect.github.com/FEX-Emu/FEX/pull/1760`
- `https://redirect.github.com/FEX-Emu/FEX/pull/1770`

This history makes the current implementation look like a reasonable speed/complexity trade made for the primary use case, followed by an unresolved lifetime seam rather than a careless omission.

## Why the seam remained unresolved

The difficult part is not erasing a map entry. FEX already has `RemoveCustomIREntrypoint()`.

The difficult part is identifying the right **pre-unmap owner event** and proving that every path using the old guest address is quiescent before physical unmap.

Later xcb thunk history records the same ownership problem from another direction. Review asked whether FEX could hook `dlclose()` to perform cleanup. The response records that after redirecting the FD used to load the thunk library, FEX loses control of the unload and had no good workaround at that point.

External history:

- `https://redirect.github.com/FEX-Emu/FEX/pull/2583`

Current FEX source still contains the comment that thunk library names ideally should be removed when a library is unloaded and before its backing memory disappears.

So the missing abstraction is best phrased as:

> FEX creates process-owned executable bridges that retain guest code addresses, but the guest loader owns physical lifetime of those addresses and supplies no common retirement transaction to the bridge owners.

## The project-level contract question

Before engineering a general unload transaction, decide what generated thunk libraries *are*.

### Contract A — generated thunk code is process-resident implementation code

Under this contract, guest `dlclose()` releases the application's logical library handle and Vulkan objects as usual, but the emulator may keep its synthetic guest bridge image mapped until process exit.

This is conceptually similar to an implementation cache or runtime support image. The application's original library API semantics remain the primary contract; physical reclamation of an emulator-generated adapter is secondary unless software can observe and depend on it.

Consequences:

- stale code destinations cannot become unmapped;
- constructors/static state are initialized once per process;
- destructors/finalizers for the synthetic image occur at process exit;
- physical reload at a new base disappears as a behavior;
- bridge metadata may remain stale but points to executable code;
- retained memory becomes an explicit cost rather than an accidental leak.

This is what the Vulkan `DF_1_NODELETE` experiment tests.

### Contract B — generated thunk DSOs obey ordinary physical unload/reload

Under this contract, `dlclose()` must eventually be allowed to unmap `libvulkan-guest.so` and a later load may create a fresh image at another base.

Then FEX owes the guest loader a real retirement protocol:

```text
begin unload generation G
  -> reject/block new bridge acquisition for G
  -> retire or rebind PFN bridges
  -> retire or rebind callback bridges
  -> invalidate translated paths embedding G addresses
  -> drain executions that already selected G
  -> permit physical unmap
  -> reclaim metadata
```

This is a stronger semantic contract and requires substantially more code and synchronization.

### Contract C — stable process-owned entry stubs, unloadable library-specific state

A hybrid architecture can decouple *callable entrypoint lifetime* from *library implementation lifetime*.

Conceptually:

```text
native host PFN H
      |
      v
stable guest bridge S        (process-owned executable arena)
      |
      v
owner/generation descriptor
      |
      +--> live guest target T1
      +--> rebound guest target T2
      +--> retired / fail-safe path
```

`S` never disappears. The library-specific target can.

This costs one more indirection or descriptor lookup but gives a clean place to encode generation, rebinding, retirement, and diagnostics. It may also address the historical same-native-PFN/multiple-guest-thunk collision more naturally than a single `H -> T` registration.

This should be prototyped rather than assumed superior; the additional dispatch cost is directly measurable.

## Working hypotheses and their falsifiers

### H1 — `DF_1_NODELETE` is a legitimate Vulkan thunk policy

Prediction:

- ordinary guest `dlclose()` succeeds logically;
- `libvulkan-guest.so` remains mapped;
- normal llvmpipe teardown changes exit 139 -> 0;
- Venus also exits 0;
- repeated logical open/close/reopen continues working;
- retained memory/static state produces no meaningful compatibility regression in tested workloads.

Falsifiers:

- an application requires Vulkan guest-thunk constructors/destructors or static/TLS state to reset on physical reload;
- repeated logical reopen produces stale API state that a real physical reload would have reset;
- `NODELETE` causes an observable Vulkan/loader regression;
- retained memory is large enough to make the policy unacceptable;
- the original crash survives even though the old guest target remains executable.

### H2 — stale dynamic-PFN CustomIR is the immediate final transfer in the exit-139 reproducer

Prediction:

- at the first transfer to the retired `CallHostFunction` target, guest `r11` equals a previously registered native Vulkan PFN `H`;
- an execution trace identifies a cached or freshly generated CustomIR path `H -> old T`;
- removing/retiring that registration before unmap prevents the dead-target transfer.

Falsifiers:

- the dead `CallHostFunction` target is entered with `r11` unrelated to any recorded host PFN;
- the immediate branch provenance is an ordinary guest branch or a FEX return/resume path rather than the CustomIR redirect;
- a generic changed-base reload test shows FEX correctly replaces `H -> old T` with `H -> new T`.

Important tracing detail: `CustomIRHandlers.find()` runs when IR is generated. A cached CustomIR block can execute later without another handler lookup. Instrument `CUSTOMIR_GENERATE` and `CUSTOMIR_EXEC` separately.

### H3 — host→guest callback trampolines are a second real lifetime class but not the terminal Vulkan edge

Prediction:

- Vulkan's X11 callback trampolines retain `GuestUnpacker`/`GuestTarget` addresses inside the guest Vulkan image;
- disabling those registrations leaves the observed final dead `CallHostFunction` failure unchanged;
- a separate targeted callback test can demonstrate stale callback addresses across unload.

Falsifier for the “secondary in this reproducer” ranking:

- removing the Vulkan X11 callback registrations eliminates the teardown crash or changes the first dead target to a callback unpacker.

### H4 — ordinary guest-range JIT invalidation is sufficient for ordinary guest code but insufficient for native-keyed bridge entries

Prediction:

- the entire retiring guest image range receives normal code invalidation;
- the native-keyed CustomIR registration/cached redirect remains independently reachable;
- changing SMC modes does not eliminate the stale bridge when the target image is allowed to unmap.

Falsifier:

- exact invalidation logs show the native-keyed bridge is already retired synchronously as a side effect of the guest image unmap.

### H5 — true physical thunk unload is unnecessary for foundational graphics thunks

Prediction:

- GL/Vulkan-style thunks behave correctly with process-resident wrapper code across real applications, logical close/reopen loops, fork/exec, and process exit;
- memory cost stays small;
- user-visible semantics depend on native API object lifetime rather than synthetic wrapper DSO finalization.

Falsifiers:

- software relies on physical adapter reload to reset thunk-local state;
- namespace isolation (`dlmopen` or equivalent) requires separate physical generations;
- retained wrapper state crosses an isolation boundary that FEX intends to preserve.

### H6 — stable process-owned bridge stubs are a better general architecture if unload fidelity is required

Prediction:

- a stable stub + owner descriptor passes changed-base reload, shared-native-PFN, alias, callback, stale-cache, and in-flight-unload tests;
- per-call overhead is acceptably small relative to the thunk call itself;
- it removes the requirement for a guest-loader hook at every call site while still requiring a clear generation retirement signal.

Falsifiers:

- the extra indirection materially harms hot graphics call performance;
- pointer identity/ABI assumptions require the existing direct-host-address behavior;
- stable stubs become as difficult to invalidate or reclaim as the current mapping.

## Experiment ladder

Run these in order because each stage answers a cheaper question before the expensive one.

### E0 — loader primitive on GitHub-hosted architectures

Disposable Fieldwork branch: `probe/fex-nodelete-gha`.

Workflow: `.github/workflows/fex-nodelete-runner-probe.yml`.

First run:

- workflow run: `31733833720`;
- commit: `884ce1580a341cb5cc819b9641616aef27dc38a8`;
- GitHub-hosted `ubuntu-24.04` x86-64: passed;
- GitHub-hosted `ubuntu-24.04-arm` AArch64: passed.

The probe builds ordinary and `DF_1_NODELETE` DSOs, verifies the dynamic flag, closes the normal DSO and requires it to disappear, closes the NODELETE DSO and requires it to remain mapped, then invokes a saved function pointer from the retained image.

Established: the ELF lifetime primitive behaves as expected on both hosted architectures used for future CI experiments.

Does not establish: anything FEX-specific.

### E1 — prove hosted ARM64 can execute an x86-64 guest through FEX

Disposable workflow: `.github/workflows/fex-arm64-static-smoke.yml` on the same probe branch.

The first version installs packaged FEX on GitHub-hosted ARM64, cross-compiles a tiny static x86-64 executable, and invokes it through FEX. The guest prints its emulated `uname` machine and the value `42`.

Interpretation:

- pass: GitHub-hosted ARM64 is a usable FEX execution lab;
- package/install failure: harness/environment problem, repair without changing product hypotheses;
- FEX executes but guest result is wrong: investigate runner/FEX compatibility before any Vulkan inference.

### E2 — build the owned FEX source head on hosted ARM64

Source candidate to test first:

- fork: `teamleaderleo/FEX`;
- base: FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`;
- branch: `diagnostic/vulkan-elf-nodelete-clean`;
- commit: `5982a38f1a8e6fcd8aadd2e58e033223c865714f`;
- diff: `ThunkLibs/GuestLibs/CMakeLists.txt`, +3 / -0;
- policy: `target_link_options(vulkan-guest PRIVATE "LINKER:-z,nodelete")`.

First build only enough FEX to run a static x86 guest. Then enable thunk targets. Keep execution machinery in Fieldwork, not the source candidate branch.

### E3 — generic `libfex_thunk_test` lifetime reproducer

FEX already contains a small dummy thunk library specifically for generator behavior. Extend a diagnostic branch of that test library with an API that returns a stable native host function pointer and uses the same indirect-guest-call mechanism as Vulkan.

Target sequence:

```text
load generation G1
obtain host PFN H
register H -> guest invoker T1
call H successfully
close G1
reserve old guest image range so it cannot be reused
load generation G2 at a different base
obtain the same host PFN H
new invoker is T2
call H
```

Distinguishing outcomes:

- FEX reports/retains `H -> T1` and the call reaches T1: generic stale-registration bug established without Vulkan;
- FEX replaces/rebinds to `T2` and succeeds: dynamic-PFN stale-registration theory loses substantial weight for the Vulkan crash;
- registration collision is detected before execution: lifetime defect still exists, but the failure class is stale metadata rather than silent use-after-unmap;
- NODELETE prevents G1 physical retirement: confirms residency is a containment policy rather than cleanup.

A second generic test should exercise host→guest callback trampoline retention independently.

### E4 — real Vulkan llvmpipe on hosted ARM64

Only after E1/E2 establish the runner:

- provide an x86-64 userspace/rootfs suitable for `vulkaninfo`;
- use native ARM64 Mesa llvmpipe as the host Vulkan implementation;
- reproduce callback-routing-fixed baseline teardown;
- compare ordinary guest Vulkan thunk vs `DF_1_NODELETE` guest thunk;
- retain exit status, guest mapping at logical close, and ordered teardown trace.

The hosted runner cannot reproduce Apple M5/Venus, but llvmpipe already reproduces the teardown defect on the original Fedora VM, so it is the correct portable target.

### E5 — target Fedora VM / Apple M5 confirmation

Preserve the existing controls:

| Variant | Expected discriminator |
| --- | --- |
| callback-fix baseline + llvmpipe | exit 139 |
| `DF_1_NODELETE` + llvmpipe | predicted exit 0 |
| callback-fix baseline + Venus | exit 139 |
| `DF_1_NODELETE` + Venus | predicted exit 0 |
| pinned guest thunk | exit 0 control |
| no-op guest `dlclose` | exit 0 control |
| bogus preload | exit 139 negative control |

Also verify the application still performs its ordinary logical `dlclose()` and that the guest thunk remains mapped afterward because of ELF policy rather than because the call was bypassed.

### E6 — compatibility attacks on NODELETE

If E4/E5 pass, try to make residency lose:

1. repeated `dlopen -> procaddr -> use -> dlclose` loops;
2. hundreds/thousands of logical reloads while recording RSS and mapping count;
3. constructor/destructor counters;
4. TLS/static-state mutation across logical close/reopen;
5. `fork()` after initialization and use in the child;
6. `exec()` reset;
7. loader namespaces where supported;
8. same native PFN requested through aliases;
9. multiple Vulkan devices/instances;
10. simultaneous threads calling PFNs while another thread closes the logical library handle, within the API/loader behavior we can exercise safely.

A failure here determines whether Vulkan-only NODELETE is a legitimate contract or merely a diagnostic workaround.

### E7 — stable-stub prototype

If physical unload fidelity is required, implement a local model and then an owned-FEX diagnostic prototype:

```text
H -> stable S
S -> atomic/current descriptor for generation G
G -> target T
```

Measure:

- one-call overhead against current CustomIR direct exit;
- alias/native-pointer collision behavior;
- reload at different guest base;
- callback symmetry;
- retirement while calls are already in flight;
- stale descriptor behavior;
- memory reclamation.

Require a dead/retired generation to fail in a controlled FEX path rather than executing unmapped guest bytes.

## What I would optimize for

In priority order:

1. **Correct executable lifetime.** No process-owned bridge may target physically retired guest code.
2. **A simple ownership rule.** A reviewer should be able to state who owns each retained executable address and when that owner retires.
3. **Fast steady-state calls.** Thunks exist partly to avoid emulating graphics APIs instruction-by-instruction.
4. **Predictable loader semantics.** Any deviation from ordinary DSO physical unload should be explicit and bounded to synthetic thunk images.
5. **Diagnosability.** Registrations should carry enough identity to log `bridge -> owner generation -> target` without reverse-engineering addresses after a crash.
6. **Generalization only after proof.** Vulkan can legitimately choose NODELETE even if arbitrary plugin callbacks cannot.

I would avoid paying the complexity cost of full generation-aware reclamation unless an experiment demonstrates that physical unload of the synthetic Vulkan thunk provides a compatibility property we actually need.

I would also avoid generalizing NODELETE to every guest thunk just because it solves Vulkan. The correct policy boundary may be “guest thunks that publish executable addresses into process-owned FEX state,” and even that needs callback/plugin tests.

## Evidence boundary

Already demonstrated on the original Fedora/Apple-M5 investigation:

- enumeration succeeds after the separate callback-routing diagnostic;
- teardown exit 139 reproduces under llvmpipe;
- saved guest RIP belongs to the retired Vulkan guest thunk image and resolves in generated `CallHostFunction` code;
- no-op guest `dlclose()` rescues the run;
- bogus preload does not;
- pinning only `libvulkan-guest.so` rescues the run;
- pinned Vulkan thunk also rescues the Venus path.

Demonstrated in local/hosted loader experiments:

- `DF_1_NODELETE` keeps a DSO executable after logical `dlclose()`;
- exact CMake `LINKER:-z,nodelete` spelling produces the ELF flag;
- GitHub-hosted x86-64 and ARM64 runners both pass the ordinary-vs-NODELETE differential probe.

Still open:

- exact immediate caller of the final dead `CallHostFunction` transfer;
- whether hosted ARM64 can run the required FEX workloads end-to-end;
- whether NODELETE passes real FEX/Vulkan execution and reload compatibility;
- whether physical guest-thunk unload is an intended FEX compatibility contract or merely inherited loader behavior;
- whether a stable process-owned bridge-stub architecture provides a better general solution if true unload is required.

## External-contact state

FEX upstream remains read-only. All source experiments are confined to owned forks and Linux Fieldwork. No upstream issue, comment, review, pull request, or other interaction is authorized or made by this investigation.
