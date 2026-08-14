# Lifecycle tests should cover failure and success

## In simple words

A regression test can prove that a known failure stays fixed. When a patch changes resource ownership or cleanup timing, a second test can preserve the successful lifecycle too.

A useful pair is:

```text
failure path: replacement becomes live -> later work fails -> replacement stays owned
success path: replacement becomes live -> cleanup completes -> predecessor becomes reusable
```

There is an important refinement: **before writing tests that preserve a staged lifecycle, ask whether the staging is required at all.** If review removes an unnecessary deferred state, delete tests that exist only to model losing that state and keep the behavioral lifecycle tests instead.

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

## The current five-test neighborhood

Two failed-relocation regressions were already present. PR 8721 keeps three additional behavioral tests after review removed the deferred old-L2 release mechanism.

| Role | Rust test function | What it arranges | What it proves |
|---|---|---|---|
| Existing regression | `failed_l2_relocate_keeps_live_table_off_free_lists` | Exhaust the allocator at L2 relocation | A failed relocation leaves the still-live old L2 outside the free lists |
| Existing regression | `failed_l2_relocate_after_compressed_write_keeps_live_table` | Reach the same failed relocation through a compressed-cluster write | The compressed-write entry point preserves the same old-L2 safety rule |
| PR regression | `fresh_l2_enospc_reopen_does_not_reuse_live_table` | Allocate a fresh L2, hit later ENOSPC, close, and reopen | The live L2 keeps refcount 1, stays outside the rebuilt free list, and the allocator returns another cluster |
| Review-added success control | `successful_l2_relocation_releases_old_table` | Perform an ordinary successful relocation and then flush metadata | Old L2: refcount 1 -> refcount 0 -> reusable after flush. New L2: refcount 1 -> stays allocated |
| PR alternate-caller regression | `zero_marker_fresh_l2_keeps_refcount_owner` | Create a fresh metadata L2 through the zero-marker deallocation path | The ownership rule also holds for this caller of fresh-L2 allocation |

## Why the successful-lifecycle test matters

The historical failures were mostly about what must **not** happen:

```text
still-live L2 -> allocator-visible free cluster
```

Weltling's review asked the complementary question: what proves ordinary cleanup still releases dead metadata?

`successful_l2_relocation_releases_old_table` follows the normal `map_write()` path and checks both L2 clusters after relocation:

```text
Old L2: refcount 1 -> refcount 0
New L2: refcount 1
```

It then checks the allocator lifecycle. The old L2 first enters `unref_clusters`, where it waits for metadata flush. After `QcowMetadata::flush()`, it moves into `avail_clusters` and becomes reusable. The replacement stays outside the free lists throughout.

So the durable pair is:

```text
                    relocation
                        |
             +----------+----------+
             |                     |
       failed handoff         normal success
             |                     |
 live metadata stays     replacement stays owned
 off the free lists      predecessor is released
```

## The test that review made obsolete

An intermediate PR version contained:

```text
relocated_l2_dropped_deferred_updates_keeps_refcount_owner
```

At that point relocation looked like:

```text
new L2 ownership: immediate
old L2 release: deferred to caller
```

The test called `update_cluster_addr()` directly and deliberately discarded the local deferred-release collection. That was a legitimate way to model the implementation's then-current error window.

Rob Bradford later challenged the premise of that staging: after L1 switches to the replacement, there is no useful reason to carry the predecessor's refcount drop back to `map_write()`.

The final design is:

```text
allocate replacement
-> refcount = 1
-> prepare replacement L2
-> switch L1
-> release predecessor
```

There is no deferred out-parameter or caller cleanup loop anymore, so the implementation-specific dropped-vector regression was deleted too.

That is the stronger testing lesson:

```text
mechanism exists
-> test its meaningful failure boundary

review removes mechanism
-> remove mechanism-specific test
-> retain behavioral contract tests
```

Tests should preserve intended behavior, not force an accidental intermediate architecture to survive.

## A remaining failure edge worth testing if the fixture stays clean

The final handoff has one newly interesting fallible point:

```text
replacement allocated + owned
-> replacement contents prepared
-> L1 switches
-> old-L2 refcount drop fails
```

A clean fault-injection test could check:

```text
L1 -> replacement
replacement stays owned
replacement L2 contains the intended entry
old L2 remains owned
old L2 is not allocator-visible for reuse
```

This is useful if the failure can be injected locally and readably. It should not force the L2 PR to absorb lower-level recursive-refcount failure machinery merely to create a fixture.

## A better way to read tests

For test code with a lot of fixture setup, read the Rust syntax second. First answer four questions:

1. **What state is the test creating?** Here that can mean a clean L2, a capped allocator, a fresh L1 entry, or a reopened image.
2. **What operation does it perform?** Examples are `map_write()`, `update_cluster_addr()`, metadata flush, or zero-marker deallocation.
3. **Where is the distinguishing edge?** ENOSPC, replacement allocation, successful flush, alternate caller, or an injected refcount failure.
4. **What fact must remain true afterward?** A live cluster has refcount 1; a dead old cluster reaches refcount 0; allocator lists agree with those ownership facts.

This turns a long test into a state transition instead of a pile of setup code.

## Review wording can carry technical information

Two small review comments also improved the test contract.

`get_new_cluster()` can either reuse a free cluster or extend the file. An expectation message that says a reusable cluster must exist describes a narrower implementation assumption. The useful condition is simply that the allocator returns a cluster other than the still-live L2.

Likewise, a comment such as “own the new L2 before publishing it” requires the reader to translate two abstractions. “Set the new L2 table's refcount to 1 before the L1 entry points at it” states the exact ordering that future changes must preserve.

## Durable rules

### Pair failure and success where practical

When a patch moves resource ownership, publication, release, or reuse across an error boundary, preserve both sides of the lifecycle:

```text
failure control: live replacement survives interruption
success control: dead predecessor is eventually released
```

The regression keeps the historical bug dead. The success control keeps the intended behavior alive through later refactors.

### Challenge staging before memorializing it

If the test requires constructing a caller that drops deferred work, ask whether the deferred work is itself necessary.

A useful review question is:

> Is this staged state part of the contract, or merely an obligation the current implementation carries around?

If the latter can be eliminated, state reduction may remove more failure paths than another regression can cover.

### Test state transitions, not temporary containers

Prefer:

```text
live object remains owned
predecessor becomes reusable after successful cleanup
```

over:

```text
vector has one element
caller drains vector
helper returns this exact temporary shape
```

## Related work

- [Cloud Hypervisor PR 8721](https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8721)
- [`../../investigations/cloud-hypervisor-qcow-r609-review/README.md`](../../investigations/cloud-hypervisor-qcow-r609-review/README.md)
- [`history-can-change-the-repair-boundary.md`](history-can-change-the-repair-boundary.md)
- [`../../FIELD_GUIDE.md`](../../FIELD_GUIDE.md)
