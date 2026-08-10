# Cloud Hypervisor AArch64 PPTT cache-handle sharing — negative result

Updated: 2026-08-10
State: RETIRED AFTER SPEC REVIEW
Canonical source generation reviewed: `a1fcb9f790616ac615f66de73be540b0b20844b1`
External-contact state: `false; none occurred`

## Hypothesis

While reviewing the AArch64 cache portability work, `CpuManager::create_pptt()` looked suspicious because it constructs one L1D cache node, one L1I cache node, one L2 cache node, and one L3 cache node before walking the processor hierarchy, then reuses those cache handles on multiple processor/cluster nodes.

The introducing commit `ec73733b2112d231f3ad8cf14d623002ad920cf7` says the intended model is L2 unique per CPU and L3 shared at the cluster level. A naive interpretation of a reused cache handle would therefore make the implementation look like it reports one globally shared L1/L2/L3 instance.

## Why the hypothesis is wrong

The ACPI PPTT processor-hierarchy rules explicitly permit separate instances of an identical private resource to be represented by a single resource structure referenced from multiple processor nodes. The private-resource relationship belongs to each processor hierarchy node; sharing the descriptor is a table-compaction mechanism and does not by itself mean one physical cache instance.

The ACPI cache example describes private L1/L2 caches at processor nodes and a shared L3 cache at the parent cluster node. Cloud Hypervisor follows that hierarchy:

- L1D/L1I handles are listed as private resources of each processor leaf;
- L1 cache descriptors link to the L2 descriptor;
- L3 is listed as a private resource of each cluster/package node.

Reusing identical cache descriptors across processor or cluster nodes is therefore valid unless an implementation requires unique references to each resource instance.

The `acpi_tables` crate implementation is consistent with this representation: `add_cache()` returns the table offset of a cache structure, and `ProcessorNode::add_cache()` records that resource reference. Its own PPTT unit test deliberately reuses identical cache handles across many processor nodes.

## Existing Cloud Hypervisor integration-test limitation

The AArch64 ACPI cache integration test added in commit `0b150ea5609c65a39d6ff35eae8ad430a2763c2f` compares only host/guest `lscpu -C=NAME,ONE-SIZE` values. It does not test cache instance counts. That initially made the handle reuse look more suspicious, but the ACPI compaction rule means the missing cardinality assertion is not evidence of a product defect by itself.

## Disposition

Do not open a product bug for cache-handle reuse alone.

Revisit only if guest behavior demonstrates an incorrect sharing relationship, the PPTT hierarchy attaches a cache at the wrong processor node level, a cache requires a unique reference/ID, or a future cache model introduces non-identical instances that can no longer share one descriptor safely.
