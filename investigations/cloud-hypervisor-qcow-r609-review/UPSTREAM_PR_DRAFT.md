# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: `cloud-hypervisor/cloud-hypervisor`  
Proposed base branch: `main`  
Candidate branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/qcow-l2-refcount-ownership-r609`  
Signed candidate head: `b26d6b70e28dacf0a35463b3bc45494ae2b2028e`  
Candidate tree: `20088ee1b7f2fa69df1ebaff97105d70e9490fa0`  
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

The same ordering gap affects both initial L2 allocation and L2 relocation. New L2 ownership is now synchronous; only release of the old relocated L2 remains deferred, preserving the ordering introduced by PR #8637.

The added regressions cover fresh-L2 ENOSPC and allocator reuse after reopen, relocated-L2 ownership, and the zero-marker path. The existing failed-relocation regressions continue to pass.

### Validation

`cargo test --locked -p block` — 298 passed  
`cargo test --locked -p block --features io_uring` — 326 passed  
`cargo check`, Clippy with warnings denied, nightly rustfmt, and `git diff --check` also passed.

AI assistance: ChatGPT (GPT-5.6 Sol) was used for source review, test design, and patch refinement.

## Internal reviewer notes

The deferred `set_refcounts` pattern predates the current Cloud Hypervisor QCOW structure and was present in the crosvm-derived implementation imported in 2019. A later L2-cache helper extraction explicitly preserved the existing logic. The old vector could represent both ownership and release operations, which made it easy to publish a new L2 before its ownership update was applied.

The current source makes that split structural: new L2 ownership is synchronous, while `deferred_unrefs: Vec<u64>` can represent only old-L2 releases. The relocation regression asserts that the deferred collection contains exactly the old L2 before modeling loss of the later release.

The repair is intentionally framed as `ownership before reachability`, not as a transactional rewrite. It doesn't add a rollback/commit protocol.

The source candidate changes only `block/src/formats/qcow/metadata.rs`. The signed head remains one commit ahead of the current upstream base, and GitHub reports its SSH signature as valid.

Current-tree Linux validation passed in Fieldwork run `31610738323` from carrier head `98c79d6e056244fcdc4e7f063dfb9d2029039bd0`. The focused fresh-L2, relocated-L2, and zero-marker tests passed; both existing failed-relocation controls passed; the block suite passed 298/298; the io_uring block suite passed 326/326; check, Clippy, nightly rustfmt, and diff-check passed. Artifact `9147104092` has digest `sha256:6e54c2bd5db682588f3bb5a2a65d3a6a24a7d70381f8b6f49dee041acca34209`.

Issue #611 remains a separate shutdown durability problem: metadata flush failure can interact with DIRTY-bit clearing. This candidate doesn't claim to repair that path.

## Submission checklist

- [x] Candidate is one source commit on the current intended upstream base.
- [x] Complete candidate diff reviewed.
- [x] Baseline fresh-L2 regression fails and current candidate passes.
- [x] Baseline relocated-L2 ownership regression fails and current candidate passes.
- [x] Block tests pass: 298 passed, 0 failed.
- [x] Block tests with `io_uring` pass: 326 passed, 0 failed.
- [x] Check, Clippy, nightly rustfmt, and diff-check pass.
- [x] Existing PR #8637 relocation regressions remain green.
- [x] Fork/branch delivery path exists.
- [x] Candidate commit has a human `Signed-off-by` trailer.
- [x] Candidate commit is cryptographically signed and GitHub reports the signature as valid.
- [x] Upstream base remains `1af93ac7035cda77cd87b0c18b1134ebb0928052` at the release-only amend.
- [ ] Explicit authorization for upstream contact recorded.
- [ ] Submitted head and public PR recorded after submission.
