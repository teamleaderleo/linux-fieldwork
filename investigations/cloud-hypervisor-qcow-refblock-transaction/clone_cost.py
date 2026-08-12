#!/usr/bin/env python3
from math import ceil

MAX_QCOW_FILE_SIZE = 1 << 44
MAX_RAM_POINTER_TABLE_SIZE = 35_000_000


def div_round_up(n: int, d: int) -> int:
    return (n + d - 1) // d


def max_refcount_clusters(refcount_order: int, cluster_size: int, num_clusters: int) -> int:
    # Exact arithmetic from block/src/formats/qcow/header.rs::max_refcount_clusters().
    refcount_bits = 1 << refcount_order
    cluster_bits = cluster_size * 8
    for_data = div_round_up(num_clusters * refcount_bits, cluster_bits)
    for_refcounts = div_round_up(for_data * refcount_bits, cluster_bits)
    return for_data + for_refcounts


def parser_geometry(cluster_bits: int, refcount_order: int, virtual_size: int):
    cluster_size = 1 << cluster_bits
    pointers_per_cluster = cluster_size // 8
    num_clusters = div_round_up(virtual_size, cluster_size)
    num_l2_clusters = div_round_up(num_clusters, pointers_per_cluster)
    l1_clusters = div_round_up(num_l2_clusters, pointers_per_cluster)
    header_clusters = 1
    refcount_clusters = max_refcount_clusters(
        refcount_order,
        cluster_size,
        num_clusters + l1_clusters + num_l2_clusters + header_clusters,
    )
    accepted = l1_clusters + refcount_clusters <= MAX_RAM_POINTER_TABLE_SIZE
    return cluster_size, l1_clusters, refcount_clusters, accepted


def main():
    # A deliberately adversarial but parser-accepted geometry: 16 TiB virtual
    # size, 1 KiB clusters, default 16-bit refcounts.
    cluster_size, l1_clusters, refcount_entries, accepted = parser_geometry(
        cluster_bits=10,
        refcount_order=4,
        virtual_size=MAX_QCOW_FILE_SIZE,
    )
    clone_bytes = refcount_entries * 8
    print(f"virtual_size={MAX_QCOW_FILE_SIZE}")
    print(f"cluster_size={cluster_size}")
    print("refcount_bits=16")
    print(f"l1_clusters={l1_clusters}")
    print(f"refcount_table_entries={refcount_entries}")
    print(f"refcount_table_clone_bytes={clone_bytes}")
    print(f"refcount_table_clone_mib={clone_bytes / 1024 / 1024:.3f}")
    print(f"parser_accepted={str(accepted).lower()}")
    assert accepted
    assert refcount_entries == 33_884_678
    assert clone_bytes == 271_077_424


if __name__ == "__main__":
    main()
