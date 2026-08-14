# Current FEX Vulkan lifecycle results

## TL;DR

The strongest current result is that the FEX-2608 Vulkan failure is best split into two demonstrated repair components plus one remaining generic callback-lifetime question.

1. Dynamic Vulkan lookup needs the existing custom `VK_EXT_debug_report` create/destroy implementations to be reachable. The combined ARM64 gate exercises both routed functions successfully.
2. FEX guest thunk wrappers that publish executable addresses or dynamic function pointers need to remain executable for as long as native code or an active guest-to-host-to-guest call can return through them. A process-lifetime guest-wrapper self-pin changes the isolated lifetime probe from the expected baseline failure to success and survives the combined real-Vulkan gate.
3. A separate generic host-to-guest trampoline question remains for arbitrary `GuestTarget` addresses that live in unrelated unloadable guest DSOs. Self-pinning the FEX-owned guest thunk protects its unpacker/continuation code but does not by itself own an arbitrary target module.

The next application-level gate is the original x86-64 `vulkaninfo --summary` teardown reproducer with both demonstrated repairs applied together, first against llvmpipe and then against Venus where available, with no preload pin workaround.

## Explain like I'm five

FEX has a small x86 library that acts like a translator doorway between an x86 program and the native ARM Vulkan library.

The old behavior could remove that doorway while somebody still had an address inside it, or while execution still needed to come back through it. The saved address then pointed at unmapped memory.

The lifetime candidate keeps the translator doorway present until the process ends. The routing candidate also makes two special Vulkan callback functions use the code FEX already wrote specifically for them instead of bypassing that special handling.

The focused tests now work with both changes present. The remaining big check is to run the same real `vulkaninfo` program that originally reached the end of enumeration and then crashed.

## Why care

The original failure is an application-visible crash during ordinary Vulkan teardown under FEX. Keeping the guest Vulkan thunk loaded changes the historical exit status from 139 to 0, while a bogus preload does not. A durable repair should make that preload workaround unnecessary and preserve the special callback routing that removed the earlier SIGILL.

## Source and environment boundary

- FEX runtime source under test: `FEX-2608`, commit `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.
- Combined Fieldwork carrier: branch `probe/fex-vulkan-combined-repair`.
- Combined hosted run: `31739326909`, ARM64 Ubuntu runner.
- Combined evidence artifact: `combined-vulkan-evidence-31739326909`, artifact ID `9196671181`, recorded SHA-256 `44627a3cbb1d9cf1798cff88c828c211e6cbdddf130c9fbe510ffb873fa855fc`.
- Earlier full workstation evidence remains in `EVIDENCE.md` on `investigation/fex-vulkan-thunk-lifecycle`.

## Demonstrated result A: guest-wrapper lifetime

The hosted self-pin differential first runs the unmodified FEX-2608 wrapper and then the candidate under the same probe.

Baseline markers:

```text
baseline status=20
SELFPIN call=before-close ... result=0
SELFPIN after-final-app-close ... retained=0
```

Candidate markers:

```text
candidate status=0
SELFPIN call=before-close ... result=0
SELFPIN after-final-app-close ... retained=1
SELFPIN call=old-pfn-after-app-close ... result=0
SELFPIN reopen ... same-gipa=1 same-pfn=1
SELFPIN call=new-pfn-after-reopen ... result=0
SELFPIN after-second-close retained=1
```

This demonstrates that the candidate changes the exact lifetime property under test: after the application's final ordinary close, the FEX guest Vulkan wrapper remains resident and a previously obtained guest PFN is still callable.

## Demonstrated result B: combined real Vulkan routing + lifetime

After the isolated lifetime differential succeeds, the same hosted job restores the real Vulkan guest `OnInit`, keeps the lifetime candidate, applies only the debug-report routing change, rebuilds, installs a guest X11 stub so the real constructor can register its host-to-guest trampolines, and runs through the FEX guest Vulkan wrapper against host lavapipe.

Observed markers:

```text
COMBINED pre-create-version result=0 version=0x403113
COMBINED create-instance result=0 instance=...
COMBINED dynamic-debug create=... destroy=...
COMBINED debug-report-created result=0 callback=...
COMBINED debug-report-destroyed
COMBINED instance-destroyed
COMBINED after-app-close retained=1 gipa=...
COMBINED post-close-version result=0 version=0x403113
COMBINED PASS
```

This demonstrates all of the following in one run:

- Vulkan works through the real guest wrapper far enough to create an instance;
- the two dynamic debug-report entrypoints resolve through the intended special routes;
- create and destroy both complete;
- the Vulkan instance is destroyed;
- the application's Vulkan loader reference is closed;
- the guest wrapper remains mapped afterward;
- a saved Vulkan entrypoint still executes successfully after that close.

The gate does **not** force one of the registered X11 host-to-guest trampolines to be invoked. Therefore it does not close the separate arbitrary-`GuestTarget` lifetime question.

## Historical application-level failure to retest

After the earlier callback-routing diagnostic, x86-64 `vulkaninfo --summary` reached normal Vulkan summary output and then exited 139 during teardown. Forcing llvmpipe produced the same SIGSEGV, so that failure was not Venus-specific.

Historical llvmpipe command shape:

```sh
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json \
FEX_THUNKHOSTLIBS=/opt/fex-2608/lib64/fex-emu/HostThunks \
  /opt/fex-2608/bin/FEX ./usr/bin/vulkaninfo --summary
```

Historical unload controls:

- no-op guest `dlclose` preload: exit 0;
- bogus preload: exit 139;
- pin only `libvulkan-guest.so`: exit 0.

Those controls establish that executable guest-wrapper lifetime is a distinguishing variable in the original application failure.

## Regression-test caveat

The first attempted permanent FEX regression test is invalid as evidence and should not be promoted.

Reason: the pre-existing Catch2 `Fixture` opens the test thunk library and does not close it. Because another test can run before the lifetime assertion, `RTLD_NOLOAD` can succeed because of an earlier retained loader reference rather than because the candidate self-pin worked. A valid permanent regression needs a fresh process/executable with exactly one application library handle and exactly one application `dlclose` before checking residency.

The earlier workflow failure at `enable_language(ASM_NASM)` was also harness setup, not product behavior. It lacked NASM before any new test code compiled.

## FEX contribution boundary

The FEX checkout itself contains explicit project guidance:

```text
AGENTS.md: AI must not be used to generate code for contributions to this project.
CONTRIBUTING.md: No AI/ML/LLM/etc code contributions.
```

Therefore Fieldwork may retain AI-assisted research, diagnostics, synthetic fixtures, experimental owned-fork branches, source analysis, and evidence, but AI-authored FEX product code must not be represented as an upstream-ready contribution. No upstream contact is authorized or performed by this record.

## Current interpretation

The evidence supports a broader executable-lifetime failure rather than only a stale cache-key problem.

A guest thunk can be executing when it calls native host code. Returning from that host call can require execution to resume in generated guest thunk code. If the guest DSO loses its final loader reference during that interval, erasing a lookup/cache entry cannot repair the already-active frame. Keeping the guest wrapper resident preserves both generated guest continuations and guest-side unpacker code.

This interpretation is consistent with the historical crash receipt where the old guest RIP fell in an unmapped former `libvulkan-guest.so` image range and resolved into generated `CallHostFunction<...>` code.

## Remaining generic question

FEX host-to-guest trampolines also retain an arbitrary guest target address. For Vulkan's X11 registrations:

- `GuestUnpacker` lives in `libvulkan-guest.so`;
- `GuestTarget` is a guest X11 function;
- native host state retains a host-callable trampoline pointer.

The process-lifetime wrapper pin protects the first address. It does not automatically keep an unrelated guest X11 DSO alive if that DSO is later unloaded while native code still retains the trampoline.

The clean discriminator is a fresh-process synthetic FEX thunk test where the callback target is supplied by a separate unloadable guest DSO, native host state retains the host trampoline, the target DSO is unloaded, and the retained callback is invoked afterward. That is a successor lifetime test, separate from the original Vulkan-wrapper teardown fix.

## Next gate

Run the original x86-64 `vulkaninfo --summary` application reproducer with **both** demonstrated repair components together and without any preload pinning workaround.

Required phases:

1. llvmpipe: expect enumeration plus clean exit 0;
2. same run again from clean process state: expect exit 0;
3. Venus when the runner/testbed exposes it: expect enumeration plus clean exit 0;
4. preserve stderr, exit status, Vulkan summary, relevant mapping/lifetime markers, exact FEX source identity, and artifact digest.

If llvmpipe still exits 139, capture the first terminal guest RIP/mapping class before changing either repair. That would mean the focused lifetime property is fixed but another teardown edge remains.

## Cleanup and authority

- Temporary hosted execution machinery remains in Linux Fieldwork/disposable branches.
- A contaminated owned FEX research branch may be left as provenance; it does not need to be force-cleaned to continue the investigation.
- Any future clean source candidate should be reconstructed from the intended FEX base and contain only the intended product files, but FEX's no-AI-code contribution rule still governs whether that candidate may be presented upstream.
- No FEX upstream issue, pull request, comment, review, branch, or other interaction has been created or modified by this investigation.
