# Cloud Hypervisor QCOW L2 ownership repair review

Updated: 2026-08-12
Owning issue: #609
Disposition: SUBMITTED UPSTREAM; AWAIT CI / MAINTAINER REVIEW

## Submitted source

- Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721
- Base: `1af93ac7035cda77cd87b0c18b1134ebb0928052` (`main` at submission).
- Source branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/qcow-l2-refcount-ownership-r609`.
- Submitted head: `b26d6b70e28dacf0a35463b3bc45494ae2b2028e`.
- Submitted tree: `20088ee1b7f2fa69df1ebaff97105d70e9490fa0`.
- Source fence: `block/src/formats/qcow/metadata.rs` only.
- Submitted diffstat: 177 insertions, 25 deletions.
- Commit has `Signed-off-by: Leo Li <cheerleaderleo@outlook.com>` and `Assisted-by: ChatGPT:GPT-5.6 Sol`; GitHub reports the SSH signature as valid.

The public PR was opened by the human contributor. Internal references to the upstream PR use `redirect.github.com` to avoid creating additional cross-repository backlinks.

## Defect and invariant

The baseline QCOW write path could publish a newly allocated L2 table through L1 while its `refcount=1` ownership remained only in `map_write()`'s deferred vector. A later error could drop that vector while the L1 mutation survived. After shutdown with the DIRTY bit clear, reopen could trust the refcount metadata, place the still-referenced L2 in the free pool, and hand it back to the allocator.

Independent review found the same ownership-before-publication violation at both new-L2 publication sites:

1. first L2 allocation for an empty L1 slot in `cache_l2_cluster_alloc()`;
2. replacement L2 allocation during relocation in `update_cluster_addr()`.

The submitted patch applies one rule at both sites:

```text
allocate new L2
-> establish refcount=1 ownership
-> publish L1 pointer
```

The cleanup also makes the split structural. New L2 ownership is synchronous, while `deferred_unrefs: Vec<u64>` can represent only release of an old relocated L2:

```text
new L2 ownership -> synchronous
old L2 release   -> deferred
```

This preserves the replacement-before-release ordering from upstream PR 8637 without allowing a newly published replacement to remain refcount 0. Upstream context: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8637

## Failure direction

The intended failure behavior is conservative:

- allocation failure -> L1 remains unchanged;
- ownership failure -> L1 remains unchanged and the prospective L2 is unreachable;
- ownership succeeds and later work fails -> the new L2 may remain allocated, but it cannot be exposed as refcount-0 free space;
- an old relocated L2 release remains deferred, so losing that later release can retain old metadata rather than free live metadata.

This is not a transactional rewrite and does not add rollback/commit machinery. It moves ownership ahead of reachability.

## Regression coverage

Focused regressions in the submitted source:

- `fresh_l2_enospc_reopen_does_not_reuse_live_table` — forces the original ENOSPC unwind, reopens through the production parser, verifies refcount ownership/free-list exclusion, and asks the allocator for another cluster.
- `relocated_l2_dropped_deferred_updates_keeps_refcount_owner` — models loss of the deferred old-L2 release after publication and verifies the replacement already owns refcount 1; it also asserts the deferred collection contains exactly the old L2.
- `zero_marker_fresh_l2_keeps_refcount_owner` — guards the second caller of `cache_l2_cluster_alloc()` after ownership moved into the helper.

Existing upstream relocation controls remain unchanged and pass:

- `failed_l2_relocate_keeps_live_table_off_free_lists`;
- `failed_l2_relocate_after_compressed_write_keeps_live_table`.

Baseline discriminators remain useful historical evidence:

- fresh-L2 baseline: expected red, exit 101; reopened allocator returned the still-referenced L2 at `327680` (`0x50000`);
- relocated-L2 baseline: expected red, exit 101; reopened replacement refcount was 0;
- zero-marker baseline: pass, serving as a control.

## Current-tree Linux validation

Fieldwork branch: `research/r609-qcow-l2-owner-review`
Validation carrier head: `98c79d6e056244fcdc4e7f063dfb9d2029039bd0`
Workflow run: `31610738323`
Job: `94161115529`
Result: success
Artifact: `9147104092` (`r609-qcow-l2-owner-review`)
Artifact digest: `sha256:6e54c2bd5db682588f3bb5a2a65d3a6a24a7d70381f8b6f49dee041acca34209`
Runner: Ubuntu 24.04
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Rustfmt: `rustfmt 1.10.0-nightly (3d6c19bb9a 2026-08-11)`
Candidate-only diff SHA-256: `0c45437e68eeca0788357b268dc5e2460b3a54ce660dc288c1bf626cb00f5e15`
Candidate `metadata.rs` SHA-256: `59e2454f34711748fae267fdb13541d07682a0c6b26cd5476bedea339ceb2188`

Results:

```text
fresh focused regression                          PASS
relocated focused regression                      PASS
zero-marker control                               PASS
existing failed-relocation controls               2 passed
cargo +nightly fmt --all -- --check              PASS
git diff --check                                  PASS
cargo check --locked -p block --all-targets --tests  PASS
cargo test --locked -p block                      298 passed, 0 failed
cargo test --locked -p block --features io_uring  326 passed, 0 failed
cargo clippy --locked -p block --all-targets --tests -- -D warnings  PASS
```

Execution limits remain deterministic block-level fixtures on hosted Linux; no host-wide ENOSPC run, power-cut injection, KVM integration suite, or failpoint for every individual filesystem write.

## Upstream submission state

Public PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721
Submitted head: `b26d6b70e28dacf0a35463b3bc45494ae2b2028e`
Canonical upstream CI run: `31611611323` (in progress at the latest housekeeping check).

No assistant-authored upstream mutation is part of this record. Further upstream comments/reviews/edits remain human-driven unless explicitly requested.

## Adjacent boundary

Issue #611 remains separate: `QcowMetadata::shutdown()` can clear DIRTY after a metadata flush failure. This patch does not repair that durability path and does not claim power-loss atomicity.
