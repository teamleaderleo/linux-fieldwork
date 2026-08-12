# Upstream pull request record

Status: `SENT`  
Destination: `cloud-hypervisor/cloud-hypervisor`  
Base branch: `main`  
Source branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/qcow-l2-refcount-ownership-r609`  
Submitted head: `b26d6b70e28dacf0a35463b3bc45494ae2b2028e`  
Candidate tree: `20088ee1b7f2fa69df1ebaff97105d70e9490fa0`  
Base at submission: `1af93ac7035cda77cd87b0c18b1134ebb0928052`  
Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721  
Submission performed by the human contributor. No assistant-authored upstream mutation is recorded.

## Submitted title

`block: Own new QCOW L2 tables before L1 publication`

## Submitted public body

Currently, `map_write()` defers some L2 refcount changes until the end of the mapping operation. A newly allocated L2 can therefore become referenced by L1 before its `refcount=1` update has been applied.

```text
before: allocate L2 -> publish L1 -> apply refcount later
after:  allocate L2 -> refcount=1 -> publish L1
```

If later work fails in the old ordering, the deferred refcount update can be lost while the L1 change remains. After shutdown, the image can reopen without rebuilding refcounts, making the still-referenced L2 eligible for allocator reuse.

The same ordering gap affects both initial L2 allocation and L2 relocation. New L2 ownership is now synchronous; only release of the old relocated L2 remains deferred, preserving the ordering introduced by upstream PR 8637.

The added regressions cover fresh-L2 ENOSPC and allocator reuse after reopen, relocated-L2 ownership, and the zero-marker path. The existing failed-relocation regressions continue to pass.

### Validation

`cargo test --locked -p block` — 298 passed  
`cargo test --locked -p block --features io_uring` — 326 passed  
`cargo check`, Clippy with warnings denied, nightly rustfmt, and `git diff --check` also passed.

AI assistance: ChatGPT (GPT-5.6 Sol) was used for source review, test design, and patch refinement.

## Internal reviewer notes

The deferred `set_refcounts` pattern predates the current Cloud Hypervisor QCOW structure and was present in the crosvm-derived implementation imported in 2019. A later L2-cache helper extraction explicitly preserved the existing logic. The old vector could represent both ownership and release operations, which made it easy to publish a new L2 before its ownership update was applied.

The submitted source makes that split structural: new L2 ownership is synchronous, while `deferred_unrefs: Vec<u64>` can represent only old-L2 releases. The relocation regression asserts that the deferred collection contains exactly the old L2 before modeling loss of the later release.

The repair is intentionally framed as `ownership before reachability`, not as a transactional rewrite. It doesn't add a rollback/commit protocol.

The submitted patch changes only `block/src/formats/qcow/metadata.rs`. GitHub reports the signed head's SSH signature as valid.

Current-tree Linux validation passed in Fieldwork run `31610738323` from carrier head `98c79d6e056244fcdc4e7f063dfb9d2029039bd0`. The focused fresh-L2, relocated-L2, and zero-marker tests passed; both existing failed-relocation controls passed; the block suite passed 298/298; the io_uring block suite passed 326/326; check, Clippy, nightly rustfmt, and diff-check passed. Artifact `9147104092` has digest `sha256:6e54c2bd5db682588f3bb5a2a65d3a6a24a7d70381f8b6f49dee041acca34209`.

Upstream context for the earlier relocation ordering is https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8637.

Issue #611 remains a separate shutdown durability problem: metadata flush failure can interact with DIRTY-bit clearing. This patch doesn't claim to repair that path.

## Submission state

- [x] One source commit on the intended upstream base at submission.
- [x] Complete submitted diff reviewed.
- [x] Baseline fresh-L2 regression fails and submitted candidate passes.
- [x] Baseline relocated-L2 ownership regression fails and submitted candidate passes.
- [x] Block tests pass: 298 passed, 0 failed.
- [x] Block tests with `io_uring` pass: 326 passed, 0 failed.
- [x] Check, Clippy, nightly rustfmt, and diff-check pass.
- [x] Existing upstream PR 8637 relocation regressions remain green.
- [x] Candidate commit has a human `Signed-off-by` trailer.
- [x] Candidate commit is cryptographically signed and GitHub reports the signature as valid.
- [x] Public PR recorded via redirect link.
- [x] Submitted head recorded: `b26d6b70e28dacf0a35463b3bc45494ae2b2028e`.
- [x] Canonical upstream CI started: run `31611611323`.
- [ ] Canonical upstream CI complete.
- [ ] Maintainer review outcome recorded.
- [ ] Merge outcome recorded.

Latest housekeeping check: upstream CI run `31611611323` is in progress. No upstream mutation is performed by this internal record.
