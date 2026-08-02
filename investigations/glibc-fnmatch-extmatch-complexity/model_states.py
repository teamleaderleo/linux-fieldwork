#!/usr/bin/env python3
from __future__ import annotations

import argparse
from functools import lru_cache


def naive_count(length: int) -> tuple[bool, int]:
    """Model `*(a|aa)b` against `a^length c` with naive recursion."""

    string = "a" * length + "c"
    calls = 0

    def star(position: int) -> bool:
        nonlocal calls
        calls += 1

        if (
            position < len(string)
            and string[position] == "b"
            and position + 1 == len(string)
        ):
            return True
        if position < length and string[position] == "a" and star(position + 1):
            return True
        if (
            position + 1 < length
            and string[position : position + 2] == "aa"
            and star(position + 2)
        ):
            return True
        return False

    return star(0), calls


def memoized_count(length: int) -> tuple[bool, int]:
    """Run the same reduced grammar while evaluating each suffix state once."""

    string = "a" * length + "c"
    evaluated_states = 0

    @lru_cache(maxsize=None)
    def star(position: int) -> bool:
        nonlocal evaluated_states
        evaluated_states += 1

        if (
            position < len(string)
            and string[position] == "b"
            and position + 1 == len(string)
        ):
            return True
        if position < length and string[position] == "a" and star(position + 1):
            return True
        if (
            position + 1 < length
            and string[position : position + 2] == "aa"
            and star(position + 2)
        ):
            return True
        return False

    return star(0), evaluated_states


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=4)
    parser.add_argument("--stop", type=int, default=34)
    parser.add_argument("--step", type=int, default=2)
    args = parser.parse_args()

    print("n,naive_calls,memoized_unique_states,ratio")
    for length in range(args.start, args.stop + 1, args.step):
        naive_result, naive_calls = naive_count(length)
        memo_result, unique_states = memoized_count(length)
        if naive_result or memo_result:
            raise AssertionError("rejecting model unexpectedly matched")
        print(
            f"{length},{naive_calls},{unique_states},"
            f"{naive_calls / unique_states:.6f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
