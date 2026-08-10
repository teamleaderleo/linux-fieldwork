#!/usr/bin/env python3
"""Reduced discriminator for systemd/mkosi BindOperation optimization.

Source boundary: systemd/mkosi f7401bdc8d23486bb346790dc92508381a062f3b
This intentionally copies only the identity and redundancy logic needed to
separate current behavior from the candidate semantic-key behavior.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def splitpath(path: str) -> tuple[str, ...]:
    return tuple(p for p in path.split("/") if p)


def is_relative_to(one: str, two: str) -> bool:
    return os.path.commonpath((one, two)) == two


@dataclass(eq=False)
class CurrentBind:
    src: str
    dst: str
    readonly: bool = False
    required: bool = True
    foreign: bool = False
    relative: bool = False
    nofollow: bool = False

    def __hash__(self) -> int:
        # Exact current mkosi identity fields at the pinned source revision.
        return hash((splitpath(self.src), splitpath(self.dst), self.readonly, self.required, self.nofollow))

    def __eq__(self, other: object) -> bool:
        # Exact current mkosi equality form at the pinned source revision.
        return isinstance(other, CurrentBind) and self.__hash__() == other.__hash__()


def current_optimize(fsops: list[CurrentBind]) -> list[CurrentBind]:
    binds: dict[CurrentBind, None] = {}
    for fsop in fsops:
        binds[fsop] = None

    optimized = [
        m
        for m in binds
        if not any(
            m != n
            and m.readonly == n.readonly
            and m.required == n.required
            and m.relative == n.relative
            and m.nofollow == n.nofollow
            and is_relative_to(m.src, n.src)
            and is_relative_to(m.dst, n.dst)
            and os.path.relpath(m.src, n.src) == os.path.relpath(m.dst, n.dst)
            for n in binds
        )
    ]
    return sorted(optimized, key=lambda fsop: (fsop.relative, splitpath(fsop.dst)))


@dataclass(frozen=True)
class CandidateBind:
    src: str
    dst: str
    readonly: bool = False
    required: bool = True
    foreign: bool = False
    relative: bool = False
    nofollow: bool = False

    def key(self) -> tuple[object, ...]:
        return (
            splitpath(self.src),
            splitpath(self.dst),
            self.readonly,
            self.required,
            self.foreign,
            self.relative,
            self.nofollow,
        )

    def __hash__(self) -> int:
        return hash(self.key())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CandidateBind) and self.key() == other.key()


def candidate_optimize(fsops: list[CandidateBind]) -> list[CandidateBind]:
    binds: dict[CandidateBind, None] = {}
    for fsop in fsops:
        binds[fsop] = None

    optimized = [
        m
        for m in binds
        if not any(
            m != n
            and m.readonly == n.readonly
            and m.required == n.required
            and m.foreign == n.foreign
            and m.relative == n.relative
            and m.nofollow == n.nofollow
            and is_relative_to(m.src, n.src)
            and is_relative_to(m.dst, n.dst)
            and os.path.relpath(m.src, n.src) == os.path.relpath(m.dst, n.dst)
            for n in binds
        )
    ]
    return sorted(optimized, key=lambda fsop: (fsop.relative, splitpath(fsop.dst)))


def flags(bind: object) -> tuple[bool, bool]:
    return (getattr(bind, "foreign"), getattr(bind, "relative"))


def main() -> None:
    duplicate_cases = [
        (
            "normal then foreign",
            [CurrentBind("/src", "/dst"), CurrentBind("/src", "/dst", foreign=True)],
            [(False, False)],
        ),
        (
            "foreign then normal",
            [CurrentBind("/src", "/dst", foreign=True), CurrentBind("/src", "/dst")],
            [(True, False)],
        ),
        (
            "absolute then relative",
            [CurrentBind("/src", "/dst"), CurrentBind("/src", "/dst", relative=True)],
            [(False, False)],
        ),
        (
            "relative then absolute",
            [CurrentBind("/src", "/dst", relative=True), CurrentBind("/src", "/dst")],
            [(False, True)],
        ),
    ]

    for name, case, expected in duplicate_cases:
        got = [flags(x) for x in current_optimize(case)]
        print(f"current duplicate {name}: {got}")
        assert got == expected

    nested_cases = [
        (
            "foreign parent normal child",
            [CurrentBind("/src", "/dst", foreign=True), CurrentBind("/src/sub", "/dst/sub")],
            [(True, False)],
        ),
        (
            "normal parent foreign child",
            [CurrentBind("/src", "/dst"), CurrentBind("/src/sub", "/dst/sub", foreign=True)],
            [(False, False)],
        ),
    ]

    for name, case, expected in nested_cases:
        got = [flags(x) for x in current_optimize(case)]
        print(f"current nested {name}: {got}")
        assert got == expected

    candidate_cases = [
        [CandidateBind("/src", "/dst"), CandidateBind("/src", "/dst", foreign=True)],
        [CandidateBind("/src", "/dst"), CandidateBind("/src", "/dst", relative=True)],
        [CandidateBind("/src", "/dst", foreign=True), CandidateBind("/src/sub", "/dst/sub")],
        [CandidateBind("/src", "/dst"), CandidateBind("/src/sub", "/dst/sub", foreign=True)],
    ]

    for case in candidate_cases:
        got = candidate_optimize(case)
        print(f"candidate semantic variants survive: {got}")
        assert len(got) == 2

    true_redundancy = candidate_optimize(
        [CandidateBind("/src", "/dst"), CandidateBind("/src/sub", "/dst/sub")]
    )
    print(f"candidate true redundancy: {true_redundancy}")
    assert len(true_redundancy) == 1
    assert true_redundancy[0].src == "/src"

    print("PASS: current semantic loss reproduced; candidate discriminator preserves semantics without disabling true redundancy")


if __name__ == "__main__":
    main()
