#!/usr/bin/env python3
"""Pure model for ordered glibc cache fallback after a stale preferred entry.

This is not a glibc implementation.  It records the intended ordering and
snapshot boundary before changing loader code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    path: str
    marker: int
    flag_compatible: bool = True
    isa_compatible: bool = True
    hwcap_priority: int | None = None

    @property
    def active_named_hwcap(self) -> bool:
        return (
            self.hwcap_priority is not None
            and self.hwcap_priority > 0
            and self.flag_compatible
            and self.isa_compatible
        )

    @property
    def compatible_baseline(self) -> bool:
        return (
            self.hwcap_priority is None
            and self.flag_compatible
            and self.isa_compatible
        )


def candidate_snapshot(entries: list[Entry]) -> tuple[Entry, ...]:
    """Return copied candidate semantics in loader preference order.

    Named HWCAP entries are ordered by runtime priority (smaller is better),
    with original cache order retained for ties.  Compatible ordinary entries
    follow in original cache order.
    """

    indexed = list(enumerate(entries))
    named = [
        (index, entry)
        for index, entry in indexed
        if entry.active_named_hwcap
    ]
    named.sort(key=lambda pair: (pair[1].hwcap_priority, pair[0]))
    baseline = [entry for _, entry in indexed if entry.compatible_baseline]

    # Reconstruct value objects instead of retaining references to mutable
    # cache storage.  The real loader implementation needs the equivalent
    # copied-path lifetime boundary because recursive dlopen can reload cache.
    ordered = [entry for _, entry in named] + baseline
    return tuple(
        Entry(
            path=str(entry.path),
            marker=entry.marker,
            flag_compatible=entry.flag_compatible,
            isa_compatible=entry.isa_compatible,
            hwcap_priority=entry.hwcap_priority,
        )
        for entry in ordered
    )


def current_lookup(entries: list[Entry], present: set[str], default_marker: int) -> int:
    """Model today's one-path cache API plus ordinary default search."""

    candidates = candidate_snapshot(entries)
    if candidates:
        selected = candidates[0]
        if selected.path in present:
            return selected.marker
    return default_marker


def candidate_lookup(
    entries: list[Entry], present: set[str], default_marker: int
) -> int:
    """Try every copied cached candidate before ordinary default search."""

    for entry in candidate_snapshot(entries):
        if entry.path in present:
            return entry.marker
    return default_marker


def check_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> None:
    entries = [
        Entry("/cache/v4.so", 40, hwcap_priority=0),  # inactive
        Entry("/cache/v3.so", 30, hwcap_priority=1),
        Entry("/cache/v2.so", 20, hwcap_priority=2),
        Entry("/cache/baseline.so", 10),
    ]
    all_present = {entry.path for entry in entries}

    check_equal(current_lookup(entries, all_present, 90), 30, "current all-present")
    check_equal(candidate_lookup(entries, all_present, 90), 30, "candidate all-present")

    without_v3 = all_present - {"/cache/v3.so"}
    check_equal(current_lookup(entries, without_v3, 90), 90, "current stale preferred")
    check_equal(candidate_lookup(entries, without_v3, 90), 20, "candidate next hwcap")

    baseline_only = {"/cache/baseline.so"}
    check_equal(candidate_lookup(entries, baseline_only, 90), 10, "candidate baseline")

    check_equal(candidate_lookup(entries, set(), 90), 90, "candidate default fallback")

    incompatible = [
        Entry("/cache/v4-isa.so", 50, isa_compatible=False, hwcap_priority=1),
        Entry("/cache/v3.so", 30, hwcap_priority=2),
        Entry("/cache/baseline.so", 10),
    ]
    check_equal(
        candidate_lookup(incompatible, {entry.path for entry in incompatible}, 90),
        30,
        "skip ISA-incompatible entry",
    )

    duplicate_priority = [
        Entry("/cache/first-v3.so", 31, hwcap_priority=1),
        Entry("/cache/second-v3.so", 32, hwcap_priority=1),
        Entry("/cache/baseline.so", 10),
    ]
    check_equal(
        [entry.marker for entry in candidate_snapshot(duplicate_priority)],
        [31, 32, 10],
        "equal-priority cache order",
    )
    check_equal(
        candidate_lookup(
            duplicate_priority,
            {"/cache/second-v3.so", "/cache/baseline.so"},
            90,
        ),
        32,
        "stale first duplicate",
    )

    # Snapshot lifetime control: mutate the source list after the copy.  The
    # remaining candidate values must not follow later cache storage changes.
    mutable_entries = [
        Entry("/cache/v3.so", 30, hwcap_priority=1),
        Entry("/cache/v2.so", 20, hwcap_priority=2),
        Entry("/cache/baseline.so", 10),
    ]
    snapshot = candidate_snapshot(mutable_entries)
    mutable_entries[:] = [Entry("/replacement/other.so", 77)]
    check_equal(
        [(entry.path, entry.marker) for entry in snapshot],
        [
            ("/cache/v3.so", 30),
            ("/cache/v2.so", 20),
            ("/cache/baseline.so", 10),
        ],
        "copied snapshot survives cache replacement",
    )

    print("classification\tcandidate_snapshot_semantics_hold")
    print("current_stale_preferred\t90")
    print("candidate_stale_preferred\t20")
    print("candidate_baseline_fallback\t10")
    print("candidate_default_fallback\t90")
    print("snapshot_rebind_safe\ttrue")


if __name__ == "__main__":
    main()
