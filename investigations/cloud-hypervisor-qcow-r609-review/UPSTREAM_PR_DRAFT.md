# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: `cloud-hypervisor/cloud-hypervisor`  
Proposed base branch: `main`  
Candidate branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/qcow-l2-refcount-ownership-r609`  
Signed candidate head: `10b729ecdc778ec7a42f36441746650d21fbbffe`  
Tested candidate head before sign-off/message-only amends: `12cb3db040362b5dc0656e6fc1eb6ebe2da6bd1c`  
Candidate tree (unchanged by the amends): `5f2bc5c3a0c54ce532bd5fd231e01826856297d2`  
Candidate base: `1af93ac7035cda77cd87b0c18b1134ebb0928052`  
External contact authorized: `false`

## Proposed title

`block: Own new QCOW L2 tables before L1 publication`

## Proposed public body

Currently, `map_write()` defers some L2 refcount changes until the end of the mapping operation. A newly allocated L2 can therefore become referenced by L1 before its `refcount=1` update has been applied.

```text
before: allocate L2 -> publish L1 -> apply refcount later
after:  allocate L2 -> refcount=1 -> publish L1
```

If later work fails in the old ordering, the deferred refcount update can be lost while the L1 change remains. After shutdown, the image can reopen without rebuilding refcounts, making the still-referenced L2 eligible for allocator reuse.

The same ordering gap affects both initial L2 allocation and L2 relocation. The old relocated L2 is still released later, preserving the ordering introduced by PR #8637.

The added regressions cover fresh-L2 ENOSPC and allocator reuse after reopen, relocated-L2 ownership, and the zero-marker path. The existing failed-relocation regressions continue to pass.

### Validation

`cargo test --locked -p block` — 298 passed  
`cargo test --locked -p block --features io_uring` — 326 passed  
`cargo check`, Clippy with warnings denied, nightly rustfmt, and `git diff --check` also passed.

AI assistance: ChatGPT (GPT-5.6 Sol) was used for source review, test design, and patch refinement.

## Internal reviewer notes

The deferred `set_refcounts` pattern predates the current Cloud Hypervisor QCOW structure and was present in the crosvm-derived implementation imported in 2019. A later L2-cache helper extraction explicitly preserved the existing logic. The deferred vector is useful for collecting metadata updates, but it isn't a transaction: L1 and free-list state can survive an error after the corresponding deferred refcount update has been dropped.

The repair is intentionally framed as `ownership before reachability`, not as a transactional rewrite. It doesn't add a rollback/commit protocol.

The source candidate changes only `block/src/formats/qcow/metadata.rs`. The signed head is one commit ahead of the current upstream base, and GitHub reports its SSH signature as valid.

The source tree at the signed head is byte-for-byte the same Git tree as the tested candidate. The sign-off and wording-only amends changed commit metadata without changing the source tree.

Issue #611 remains a separate shutdown durability problem: metadata flush failure can interact with DIRTY-bit clearing. This candidate doesn't claim to repair that path.

## Submission checklist

- [x] Candidate is one source commit on the current intended upstream base.
- [x] Complete candidate diff reviewed.
- [x] Baseline fresh-L2 regression fails and candidate passes.
- [x] Baseline relocated-L2 ownership regression fails and candidate passes.
- [x] Block tests and io_uring block tests pass on the exact signed-head tree.
- [x] Check, Clippy, rustfmt, and diff-check pass on the exact signed-head tree.
- [x] Existing PR #8637 relocation regressions remain green on the exact signed-head tree.
- [x] Fork/branch delivery path exists.
- [x] Candidate commit has a human `Signed-off-by` trailer.
- [x] Candidate commit is cryptographically signed and GitHub reports the signature as valid.
- [x] Upstream base rechecked after the message-only amend; it remains `1af93ac7035cda77cd87b0c18b1134ebb0928052`.
- [ ] Explicit authorization for upstream contact recorded.
- [ ] Submitted head and public PR recorded after submission.
