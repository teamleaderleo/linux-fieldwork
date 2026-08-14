# Native-PFN duplicate-H rebind on clean resident tip — 2026-08-14

## Question

Does exact native-host-pointer (`H`) rebinding remain a real FEX Core issue at the clean resident-bridge candidate, and does it need to be added to the per-library resident-bridge source stack?

Clean source under test:

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

Diagnostic carrier branch:

`diagnostic/thunk-rebind-current-clean-20260814`

Carrier workflow commit:

`b73867a349413a974c9571d76854bda7a3071c2e`

Workflow:

`.github/workflows/thunk-rebind-current-clean-ab.yml`

Run:

`31817790502`

Retained synthetic fixture source:

`teamleaderleo/linux-fieldwork@9eca19ac8743567ce2af7b4c82f2483d97c19b09`

Fixture archive SHA-256:

`0582bf8832699cfb2614c1781473d07054ba01f03e3342735a45ea04735c2a01`

The fixture forces generation 2 to map its guest invoker at a different address while the native host function address remains stable. It then re-registers the same native `H` against the new guest `T` and probes both the translated `Link` path and fresh/current callback paths.

## Registry-only negative control

Job:

`94823525075`

Artifact:

- ID: `9225817522`
- SHA-256: `5c9bdc5b8ccb481234ccb2b79ded82def9f475a035c7ee6fbdef403d1c48d00f`

This diagnostic only replaces the duplicate `H` entry in the CustomIR registry and lets the existing removal path use its normal one-byte guest-code-range invalidation.

Observed runtime:

```text
reload invoker                    old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT
native host stable                old=0x00007ffff7d80860 new=0x00007ffff7d80860
child retained Link after reload  signal=11 (Segmentation fault)
child retained callback reload    signal=11 (Segmentation fault)
fresh guest direct host call     rv=1001031 want=1001031
fresh/current callback            rv=10010053 want=10010053
child Link after re-register      signal=11 (Segmentation fault)
child first callback after new    signal=11 (Segmentation fault)
child current callback after new  rv=10010093
child current callback after new  exit=0
```

Diagnostic duplicate receipt:

```text
DIAG_REGISTRY_ONLY_DUP H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d781b0
```

Gate:

`CURRENT_CLEAN_REGISTRY_ONLY_NEGATIVE_OK`

Classification: registry replacement alone is insufficient. Fresh/current paths can use the new `T`, while a previously translated path at stable `H` continues to execute stale code and faults.

## Exact all-cache positive control

Job:

`94823525069`

Artifact:

- ID: `9225835259`
- SHA-256: `c5ddb1c8d1935cffed3ebc66aaed31847630ae77e308d308934649f94b94d82d`

This diagnostic adds exact-address eviction for the shared lookup/code cache and each thread-local lookup cache before replacing the CustomIR handler data.

Observed runtime has the same moved `T` and stable `H`:

```text
reload invoker                    old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT
native host stable                old=0x00007ffff7d80860 new=0x00007ffff7d80860
```

The post-rebind translated path is repaired:

```text
fresh guest direct host call     rv=1001031 want=1001031
fresh/current callback            rv=10010053 want=10010053
child Link after re-register      rv=1001035
child Link after re-register      exit=0
child current callback after new  rv=10010093
child current callback after new  exit=0
```

Exact invalidation receipt:

```text
DIAG_CUSTOM_ADD H=0x7ffff7d80860 inserted=1 data=0x7ffff7da21b0
DIAG_CUSTOM_ADD H=0x7ffff7d80860 inserted=0 data=0x7ffff7d781b0
DIAG_DUP H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d781b0
DIAG_EXACT_SHARED H=0x7ffff7d80860 erased=1
DIAG_EXACT_LOCAL H=0x7ffff7d80860 thread=0xff28e0c01000
DIAG_CUSTOM_REMOVE H=0x7ffff7d80860 handler=1
DIAG_CUSTOM_ADD H=0x7ffff7d80860 inserted=1 data=0x7ffff7d781b0
```

Gate:

`CURRENT_CLEAN_EXACT_REBIND_OK`

Classification: the generic `H -> different T` rebind bug is still present at the clean resident candidate, and exact translated-code cache eviction is sufficient in this synthetic case.

## Why this is not automatically tranche 4

The per-library resident-bridge design changes the premise for the targeted libraries. Guest caller/unpacker code that native code can retain is moved into a NODELETE companion. Reloading the ordinary wrapper therefore does not normally create a new resident guest callable address for that role.

The GL moved-reload proof already demonstrated this directly: wrapper generation 2 moved while native `H` and resident `T` both stayed identical (`same_H=1`, `same_T=1` for the tested retained function paths). The clean final matrix also places Vulkan/CUDA proc-call caller roles in their NODELETE companions.

For those paths the desired state is `H -> same resident T` across wrapper generations, so the synthetic `H -> different T` repair is not exercised by the resident bridge mechanism itself.

## Same-generation alias hazard

Current Core source explicitly recognizes that one native Vulkan function can be returned for multiple guest symbol names, for example core/KHR aliases. A generic rule that treats every duplicate `H` with differing guest `T` as a generation replacement would make the latest registration win and can discard a still-valid same-generation alias mapping.

That semantic ambiguity is independent of cache invalidation correctness. The exact-cache diagnostic proves how to evict stale translated code once a rebind is known to be legitimate; it does not provide a generation/ownership discriminator that says when replacement is correct.

## Source-stack decision

Do not add the exact-cache rebind diagnostic as a fourth resident-bridge tranche on the present evidence.

Keep clean source at:

`integration/per-library-resident-bridges-drm-f3ab-20260814`

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

Track generic duplicate-H rebinding separately. A production Core fix needs an ownership/generation identity (or another unambiguous replacement criterion) in addition to exact cache invalidation, so legitimate same-generation aliases are preserved.

## Next useful lifetime lane

The per-library resident bridge now has direct lifetime coverage for retained code mappings. The next independent risk is concurrent revocation/in-flight callback behavior: what happens if a guest mapping or thunk registration is retired while a callback is already selected or executing. Keep that lane separate from duplicate-H rebind semantics.
