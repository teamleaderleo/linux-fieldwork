# Lifecycle tests should cover failure and success

## In simple words

A regression test can prove that a known failure stays fixed. When a patch changes resource ownership or cleanup timing, a second test can preserve the successful lifecycle too.

A useful pair is:

```text
failure path: replacement becomes live → later work fails → replacement still stays owned
success path: replacement becomes live → cleanup completes → old resource becomes reusable
```

This came up during review of Cloud Hypervisor QCOW L2 refcount ordering in [PR 8721](https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721).

## A small Rust syntax note

The QCOW tests live in `block/src/formats/qcow/metadata.rs` inside a test-only module. Rust uses the `#[test]` attribute on a function to tell the test harness that the function is a test. So this is a production source file that also contains test-only code, rather than a separate test file.

The nearby pattern is:

```rust
#[cfg(test)]
mod unit_tests {
    #[test]
    fn some_behavior() {
        // setup, operation, assertions
    }
}
```

## The six-test neighborhood

Two relocation regressions were already present. PR 8721 originally added three tests, and review added one successful-relocation test. The exact function names are useful anchors when reading the source.

| Role | Rust test function | What it arranges | What it proves |
|---|---|---|---|
| Existing regression | `failed_l2_relocate_keeps_live_table_off_free_lists` | Exhaust the allocator at L2 relocation | A failed relocation leaves the still-live old L2 outside the free lists |
| Existing regression | `failed_l2_relocate_after_compressed_write_keeps_live_table` | Reach the same failed relocation through a compressed-cluster write | The compressed-write entry point preserves the same old-L2 safety rule |
| PR regression | `fresh_l2_enospc_reopen_does_not_reuse_live_table` | Publish a fresh L2, hit later ENOSPC, close, and reopen | The live L2 keeps refcount 1, stays outside the rebuilt free list, and the allocator returns another cluster |
| PR regression | `relocated_l2_dropped_deferred_updates_keeps_refcount_owner` | Relocate a clean L2, then deliberately drop the local deferred-release list | The replacement L2 already has refcount 1 before later cleanup can be lost |
| Review-added success control | `successful_l2_relocation_releases_old_table` | Perform an ordinary successful relocation and then flush metadata | Old L2: refcount 1 → refcount 0 → reusable after flush. New L2: refcount 1 → stays allocated |
| PR alternate-caller regression | `zero_marker_fresh_l2_keeps_refcount_owner` | Create a fresh metadata L2 through the zero-marker deallocation path | The ownership rule also holds for this caller of fresh-L2 allocation |

## Why the review-added test is different

The failure-path relocation test deliberately stops halfway through the lifecycle.

It creates this state:

```text
L1 → old L2
old L2 refcount = 1
```

Then it makes the L2 clean, relocates it, and reaches:

```text
L1 → new L2
new L2 refcount = 1
old L2 queued for deferred release
```

The test then throws away the local deferred-release vector on purpose. That models a caller error after L1 has switched to the replacement. After close and reopen, it checks that the replacement still has refcount 1 and stays outside the allocator free list.

That test protects the bug fix:

```text
replacement becomes live → later cleanup is lost → replacement still stays owned
```

The reviewer pointed out the complementary question: what proves the ordinary successful cleanup still works?

The added `successful_l2_relocation_releases_old_table` test follows the normal `map_write()` path all the way through. It checks both L2 clusters after relocation:

```text
Old L2: refcount 1 → refcount 0
New L2: refcount 1
```

It then checks the allocator lifecycle. The old L2 first enters `unref_clusters`, where it waits for metadata flush. After `QcowMetadata::flush()`, it moves into `avail_clusters` and becomes reusable. The replacement stays outside the free lists throughout.

So the pair protects both sides of the ownership change:

```text
                    relocation
                        │
             ┌──────────┴──────────┐
             │                     │
        later failure         normal success
             │                     │
 new L2 stays owned      new L2 stays owned
                         old L2 is released
```

## A better way to read tests

For test code with a lot of fixture setup, read the Rust syntax second. First answer four questions:

1. **What state is the test creating?** Here that can mean a clean L2, a capped allocator, a fresh L1 entry, or a reopened image.
2. **What operation does it perform?** Examples are `map_write()`, `update_cluster_addr()`, or zero-marker deallocation.
3. **Where is the distinguishing edge?** ENOSPC, dropping deferred cleanup, successful flush, or an alternate caller.
4. **What fact must remain true afterward?** A live cluster has refcount 1; a dead old cluster reaches refcount 0; allocator lists agree with those ownership facts.

This turns a long test into a state transition instead of a pile of setup code.

## Review wording can carry technical information

Two small review comments also improved the test contract.

`get_new_cluster()` can either reuse a free cluster or extend the file. An expectation message that says a reusable cluster must exist describes a narrower implementation assumption. The useful condition is simply that the allocator returns a cluster other than the still-live L2.

Likewise, a comment such as “own the new L2 before publishing it” requires the reader to translate two abstractions. “Set the new L2 table's refcount to 1 before the L1 entry points at it” states the exact ordering that future changes must preserve.

## Durable rule

When a patch moves resource ownership, publication, release, or reuse across an error boundary, test the lifecycle as a pair where practical:

```text
failure control: live replacement survives interruption
success control: dead predecessor is eventually released
```

The regression keeps the old bug dead. The success control keeps the intended behavior alive through later refactors.
