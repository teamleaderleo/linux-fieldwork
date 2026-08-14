# Current-main Vulkan callback/proc confirmation

Status: complete on the true upstream main observed during this investigation.

## Upstream movement

The investigation originally started from upstream FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

During the same session upstream `main` advanced to:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

That new upstream commit is the merge of the SharedCodeBufferManager/JIT allocation change and does not touch the Vulkan thunk files. The Vulkan candidates were nevertheless replayed and retested on that exact current main instead of relying on the older baseline result.

## Replayed current-main candidate

Owned fork branch:

`fix/vulkan-callback-routing-current-main`

Upstream base:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

Three previously validated Vulkan commits were cherry-picked cleanly:

1. callback-family custom proc routing
2. native-first GIPA/GDPA availability preservation
3. non-mutating `vkCreateInstance` temporary callback-node suppression

Final replayed source:

`2665bfecd29387357c40e63432c684b36f21849a`

Only these files differ from the upstream base:

- `ThunkLibs/libvulkan/Guest.cpp`
- `ThunkLibs/libvulkan/Host.cpp`

Replay workflow:

- run `31798168267`
- job `94759767776`

## Consolidated hosted regression

Workflow run:

`31798502087`

Job:

`94760791217`

Workflow source commit:

`70050051c4a3c406e17875e435585b063b78cafe`

Exact source identities checked by the workflow:

- upstream base: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`
- candidate: `2665bfecd29387357c40e63432c684b36f21849a`
- Fieldwork probes: `6a03da49448260780731a4fb72a01f1d51f3967f`

Runner:

- `ubuntu-24.04-arm`
- runner image version `20260810.90.1`
- Lavapipe ICD `/usr/share/vulkan/icd.d/lvp_icd.json`

The workflow built one focused FEX Vulkan host/guest thunk pair and one amd64 rootfs, then ran all current Vulkan gates through that same build.

### 1. Callback routing matrix

All four x86/FEX cases completed with FEX's intentional callback suppression policy:

```text
report-direct=0
report-gipa=0
utils-direct=0
utils-gipa=0
```

Native ARM64 positive controls for debug-report and debug-utils ran first and required positive callback delivery.

### 2. Mixed instance `pNext` preservation

The consecutive debug-report -> debug-utils instance-create chain completed through FEX without delivering guest callbacks and without changing the guest-visible chain:

```text
RESTORE_AFTER_CREATE result=0 instance=0xfffa1c0256b0 ici_same=1 report_same=1 utils_same=1 callbacks=0/0
RESTORE_AFTER_DESTROY ici_same=1 report_same=1 utils_same=1 callbacks=0/0
RESTORE_RETURN unchanged=1 callbacks=0
```

Summary:

```text
pnext_exit=0
guest_chain_unchanged=1
guest_callbacks=0
```

### 3. Full non-beta proc-availability parity

The workflow regenerated the exact current Vulkan XML inventory and asserted the known scope before running:

```text
all_regular_spellings=773
nonbeta_spellings=760
beta_only_spellings=13
nonbeta_alias_spellings=105
nonbeta_canonical_commands=655
```

Native ARM64 and x86/FEX then queried all 760 non-beta names through the same Lavapipe stack.

Comparison:

```text
command_count=760
direct: matches=294 fex_extra_nonnull=466 fex_missing_nonnull=0
gipa_null: matches=760 fex_extra_nonnull=0 fex_missing_nonnull=0
gipa_instance: matches=760 fex_extra_nonnull=0 fex_missing_nonnull=0
gdpa_device: matches=760 fex_extra_nonnull=0 fex_missing_nonnull=0
```

The direct `dlsym` export-surface difference is separate from Vulkan proc-address availability. The GIPA/GDPA result is exact across all 760 non-beta names.

### Final emitted workflow summary

```text
upstream_base=f3ab82a73fb48271ee12a882c98bc5d823a2b4d1
candidate=2665bfecd29387357c40e63432c684b36f21849a
callback_matrix=pass
pnext_restoration=pass
nonbeta_proc_count=760
gipa_null=760/760
gipa_instance=760/760
gdpa_device=760/760
```

## Artifact

- ID `9218438678`
- ZIP SHA-256 `19a320e9782c08c3cd579037a44e8b4bc6736c349d047160904d945cbfc72036`

## Conclusion

All validated Vulkan callback/proc behavior survives the true upstream main observed during the session. The current combined candidate is therefore no longer tied to the earlier `71afe...` baseline.

The remaining work is source-quality/test-quality work rather than finding another failure in this lane:

- compare the proven pNext splice/restore implementation against a cleaner temporary callback-field substitution + restoration implementation;
- use the stronger full-integrity probe that also checks callback function fields and `pUserData`, not just pNext links;
- settle a permanent small regression seam and account for the currently unreachable thunk-functional CI gate.
