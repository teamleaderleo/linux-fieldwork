#!/usr/bin/env python3
"""Model the smallest legacy-cache-compatible fix for issue #502.

This is deliberately not a glibc implementation.  It isolates one policy
question: after the historical numeric comparator locates an equivalence group,
filter that group by byte-exact SONAME before applying the ordinary preference
ordering inside one real library name.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    name: str
    marker: int
    hwcap_priority: int | None


def decimal_run(text: str, start: int) -> tuple[int, int]:
    value = 0
    index = start
    while index < len(text) and text[index].isdigit():
        # The model intentionally uses unbounded Python integers.  This models
        # the historical comparator's *intended* numeric relation for the small
        # leading-zero case; overflow is a separate compatibility problem.
        value = value * 10 + ord(text[index]) - ord("0")
        index += 1
    return value, index


def legacy_relation(left: str, right: str) -> int:
    li = ri = 0
    while li < len(left):
        lb = left[li]
        rb = right[ri] if ri < len(right) else "\0"
        if lb.isdigit():
            if not rb.isdigit():
                return 1
            lv, li = decimal_run(left, li)
            rv, ri = decimal_run(right, ri)
            if lv != rv:
                return -1 if lv < rv else 1
            continue
        if lb != rb:
            return -1 if lb < rb else 1
        li += 1
        ri += 1
    rb = right[ri] if ri < len(right) else "\0"
    return -ord(rb) if rb != "\0" else 0


def current_style_select(entries: list[Entry], requested: str) -> Entry:
    group = [entry for entry in entries if legacy_relation(entry.name, requested) == 0]
    if not group:
        raise LookupError(requested)
    # Lower non-None priority is more preferred.  Baseline is last.
    return min(group, key=lambda entry: entry.hwcap_priority if entry.hwcap_priority is not None else 999)


def candidate_select(entries: list[Entry], requested: str) -> Entry:
    group = [entry for entry in entries if legacy_relation(entry.name, requested) == 0]
    exact = [entry for entry in group if entry.name == requested]
    if not exact:
        raise LookupError(requested)
    return min(exact, key=lambda entry: entry.hwcap_priority if entry.hwcap_priority is not None else 999)


def main() -> None:
    entries = [
        # Byte-distinct alias with an artificially better priority.  The current
        # comparator-equivalence policy can let this steal a request for .1.
        Entry("libalias.so.01", 201, 0),
        # Two entries for the exact requested SONAME: an active optimized copy
        # and a baseline.  The candidate must retain the optimized preference.
        Entry("libalias.so.1", 101, 2),
        Entry("libalias.so.1", 100, None),
    ]

    current = current_style_select(entries, "libalias.so.1")
    assert current.name == "libalias.so.01" and current.marker == 201

    fixed = candidate_select(entries, "libalias.so.1")
    assert fixed.name == "libalias.so.1" and fixed.marker == 101

    alias = candidate_select(entries, "libalias.so.01")
    assert alias.name == "libalias.so.01" and alias.marker == 201

    # A cache group may contain several entries for one exact SONAME.  Exact
    # filtering must happen before normal same-name HWCAP preference, not in
    # place of it.
    assert candidate_select(entries, "libalias.so.1").hwcap_priority == 2

    # The historical relation really does collapse the two spellings, which is
    # why a byte-exact eligibility check can be added without changing how old
    # cache groups are located.
    assert legacy_relation("libalias.so.1", "libalias.so.01") == 0

    print("PASS: exact-name filtering separates comparator aliases")
    print("PASS: same-name HWCAP preference survives exact-name filtering")


if __name__ == "__main__":
    main()
