# FEX human review desk — 2026-08-14

Status: internal handoff snapshot. This is not an upstream submission queue and does not imply that any AI-assisted source should be forwarded upstream. The purpose is to identify which findings are stable enough for a human to learn, independently re-derive, rewrite, and defend front to back.

Live investigation observed at `teamleaderleo/linux-fieldwork:investigation/fex-vulkan-thunk-lifecycle` head `bde4e844af7823fab0035e7c24580042cb9ca822`. That branch was 41 commits ahead of the previous workstream-status snapshot at `a57468c3055332b5c965454eec9438ac4927f008`, so older readiness labels should not be treated as current.

## On the human desk now

### 1. Vulkan proc-address callback routing and native availability

**Desk status: READY FOR HUMAN STUDY / INDEPENDENT RE-DERIVATION**

Owned-FEX branch: `fix/vulkan-callback-proc-routing`
Current head observed: `c011366706eaf65a00380003989b3a10811212b6`
Internal owned-fork draft: PR #1

The candidate is split into two bounded ideas:

1. route the three callback-sensitive custom host implementations that were missing from dynamic lookup;
2. ask native GIPA/GDPA first so FEX does not manufacture availability, while preserving guest GIPA/GDPA self-entrypoints only when native lookup approves them.

The final hosted ARM64 matrix covers direct and dynamic debug-report/debug-utils callback paths, NULL-instance negative availability, GIPA self-query behavior, and real-device GDPA semantics. A separate stacked draft PR #2 tests equality between `custom_host_impl` metadata and the manual custom-route inventory for both 64-bit and 32-bit thunk modes.

Human task: reproduce the bug statement from clean source, understand why custom routing and availability are separate claims, then independently write/review the minimal implementation and test story. The full 773-name XML-derived proc corpus is useful additional prevention evidence but is not required to understand the bounded existing candidate.

### 2. Thunkgen const-pointee repack correctness

**Desk status: READY FOR HUMAN STUDY / INDEPENDENT RE-DERIVATION**

Owned-FEX branch: `linux-fieldwork/thunkgen-preserve-const-repack`
Head: `715ff36bff2fd9f2353ab31613dc41ae106f3938`
Parent: `71afe476751deac24adabd1adb575fd2337b6e0a`

The candidate is a small generic thunkgen correctness fix: generated repack wrappers must preserve pointee constness so teardown cannot copy converted host state back into caller-owned `const T*` guest input.

Evidence is unusually complete for the size of the change:

- Vulkan allocator causal runtime discriminator passes and preserves guest/host allocator identity across create/destroy;
- targeted generic `StructRepacking` regression passes for both guest ABIs (28 assertions);
- broader hosted-x86 thunkgen suite shows no failure delta against the exact unmodified parent.

Human task: read `repack_wrapper` entry/exit semantics, verify why pointee const controls writeback, re-derive the change in `gen.cpp`, and decide what the smallest maintainable regression should assert.

### 3. Vulkan `vkCreateInstance` pNext callback-node handling

**Desk status: READY FOR HUMAN STUDY; NEWER THAN THE TWO ITEMS ABOVE**

Owned-FEX branch: `fix/vulkan-instance-pnext-callback-restoration`
Head: `27bf25d9fd2f918c577e302cda56bb733cdd04dd`
Parent: proc-routing candidate `c011366706eaf65a00380003989b3a10811212b6`

Two bounded bugs are demonstrated:

- `VkDebugUtilsMessengerCreateInfoEXT` callback-bearing pNext nodes were not suppressed during `vkCreateInstance`, allowing native ARM validation code to invoke a guest callback and producing SIGILL/132 under FEX;
- the existing debug-report splice mutated the marshaled input chain and did not restore predecessor links, making the guest-visible input differ after the call.

The one-file source candidate temporarily splices both callback node classes, re-checks the same predecessor for consecutive nodes, calls native Vulkan, then restores recorded links in reverse order. Hosted ARM64 validation reports exit 0, unchanged guest chain, and zero guest callback invocations under the existing suppression policy.

Human task: verify Vulkan pNext ownership/const expectations and decide whether temporary mutation+restoration is acceptable or whether a copied-chain implementation is preferable for maintainability.

## Near the desk — one more reduction/validation pass preferred

### 4. MREMAP destination translation invalidation

Owned-FEX branch: `candidate/fex2608-mremap-destination-codecache`
Head: `f42a66b4e9e23287ae22c82d83ad778d659dff87`
Parent: exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`

The source candidate is only one file and one conceptual change: after a moved `mremap`, invalidate translations covering the destination address/range as well as the old source range. The diagnostic split proof already demonstrated that stale translated code at a `MREMAP_FIXED` destination survives replacement until separately invalidated.

Reason to keep this one just off the main desk: the clean candidate branch currently has no branch-local Actions run, and the separate owner-claim retirement problem remains intentionally outside this fix. Before human handoff, retain one direct candidate-vs-parent runtime gate showing only the stale destination-code effect is repaired and the owner-identity issue remains separately reproducible.

### 5. Selective whole-wrapper NODELETE containment

Owned-FEX branch: `candidate/selective-nodelete-guest-thunks-20260814`

The containment logic is small and the affected-library audit is mature. Whole-wrapper NODELETE now also has a measured six-wrapper after-close cost: +2.5 MiB RSS/PSS, +1.594 MiB mapped thunk VA, and +31 thunk mappings versus stock unload in that probe.

Reason to keep it behind the first three: the resident-companion design has become the preferred unload-preserving direction, so NODELETE is now best understood as containment/reference policy rather than the likely final architecture. Human review is still useful if a small containment proposal is desired.

## Architecture reading is now worthwhile, but do not freeze for rewrite yet

### 6. Per-library resident guest bridges

Clean source integration branch: `integration/per-library-resident-bridges-f3ab-20260814`
Head: `48e28a2ce9da1334feb8d7b77dbade66efa24be2`
Base: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

This lane has advanced substantially since the previous status snapshot:

- direct thunkgen `-guest-bridge` and `-guest-bridge-accessors` role/accessor gate is green;
- canonical signatures carry orthogonal `needs_caller` / `needs_unpacker` roles and use stable signature-hash identity;
- parser-free CUDA retained-callback moved-reload A/B is green;
- common `add_guest_bridge(...)` helper is green across Vulkan, CUDA, and Wayland packaging classes;
- clean source tranche 1 integrates generator work, callback_member support, common packaging helper, and Vulkan/CUDA/Wayland companions with diagnostic files excluded;
- GL direct-helper runtime has since gone green on the live investigation branch, but GL is not yet included in tranche 1.

This is mature enough for architecture study. It is still a moving implementation target: GL integration, DRM library annotations, 32-bit Wayland `wl_array` handling, and final source reduction remain open. Prefer learning the invariant and generated/build ownership boundaries now; defer a full human rewrite until the source tranche stops changing materially.

## Keep off the human desk for now

### 7. Application callback execution leases / generation retirement

This lane has become much stronger, including a real retained-libdrm proof where the generated unpacker is resident and the actual callback target belongs to a separately unloadable plugin owner generation. The active callback target is kept mapped until its lease releases; later physical reclaim succeeds. A synthetic MAP_FIXED reject/release/retry proof also works.

It is still actively defining product ownership semantics: VMA OwnerID vs load-generation/dependency identity, stale retained-callback behavior, multi-callback aggregation, and wider destructive memory operations remain open. Preserve and keep testing; do not ask the human to rewrite it yet.

### 8. H->T owner-generation / generalized VM lifetime

The stale-generation and VM-replacement diagnoses remain important, and the MREMAP destination-code half has now been isolated into the small candidate listed above. The broader owner-generation/transition/lease model should remain research material until its individual repair obligations are separated into similarly bounded candidates.

## Recommended human order

1. Vulkan proc-address callback routing (`fix/vulkan-callback-proc-routing`)
2. thunkgen const-pointee repack (`linux-fieldwork/thunkgen-preserve-const-repack`)
3. Vulkan instance pNext callback restoration (`fix/vulkan-instance-pnext-callback-restoration`)
4. after one direct clean-candidate gate, MREMAP destination translation invalidation
5. optional containment-policy review of selective NODELETE
6. architecture study of resident per-library bridges, without freezing implementation yet

Everything else remains recoverable research/provenance. No deletions or upstream contact are implied by this desk classification.
