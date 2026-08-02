#!/usr/bin/env python3
"""Apply one exact jq #3128 compiler-layout variant.

The patcher intentionally operates on the pinned src/compile.c text and fails
closed if the source shape drifts. It does not edit jq's tests or generated
files.
"""

from __future__ import annotations

import argparse
from pathlib import Path


BASE_SIMPLE = "    return bind_matcher(final_matcher, body);"
BASE_COMPLEX = "  return bind_matcher(preamble, BLOCK(mb, final_matcher, body));"
BASE_DESTRUCTURE = (
    "  return BLOCK(top, gen_subexp(var), gen_op_simple(POP), "
    "bind_alternation_matchers(matchers, body));"
)

VARIANTS: dict[str, tuple[str, str, str]] = {
    "baseline": (BASE_SIMPLE, BASE_COMPLEX, BASE_DESTRUCTURE),
    # Closed jqlang/jq#3384 source logic, excluding its unrelated Makefile edit.
    "closed-pr-3384": (
        "    return bind_matcher(final_matcher, BLOCK(gen_op_simple(POP), body));",
        "  return bind_matcher(preamble, BLOCK(mb, final_matcher, gen_op_simple(POP), body));",
        (
            "  return BLOCK(top, gen_op_simple(SUBEXP_BEGIN), gen_subexp(var), "
            "gen_op_simple(SUBEXP_END), gen_op_simple(POP), "
            "bind_alternation_matchers(matchers, body));"
        ),
    ),
    # The ordering written in issue #3128: end the path subexpression before
    # discarding the destructured value.
    "issue-end-pop": (
        (
            "    return bind_matcher(final_matcher, "
            "BLOCK(gen_op_simple(SUBEXP_END), gen_op_simple(POP), body));"
        ),
        (
            "  return bind_matcher(preamble, BLOCK(mb, final_matcher, "
            "gen_op_simple(SUBEXP_END), gen_op_simple(POP), body));"
        ),
        (
            "  return BLOCK(top, gen_op_simple(SUBEXP_BEGIN), gen_subexp(var), "
            "gen_op_simple(POP), bind_alternation_matchers(matchers, body));"
        ),
    ),
    # The unresolved sibling ordering explicitly called out in issue #3128.
    "issue-pop-end": (
        (
            "    return bind_matcher(final_matcher, "
            "BLOCK(gen_op_simple(POP), gen_op_simple(SUBEXP_END), body));"
        ),
        (
            "  return bind_matcher(preamble, BLOCK(mb, final_matcher, "
            "gen_op_simple(POP), gen_op_simple(SUBEXP_END), body));"
        ),
        (
            "  return BLOCK(top, gen_op_simple(SUBEXP_BEGIN), gen_subexp(var), "
            "gen_op_simple(POP), bind_alternation_matchers(matchers, body));"
        ),
    ),
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one {label} source shape, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=VARIANTS)
    parser.add_argument("compile_c", type=Path)
    args = parser.parse_args()

    path = args.compile_c
    text = path.read_text(encoding="utf-8")

    # Verify all baseline anchors even for the no-op row. This makes baseline
    # an exact-source identity check rather than an unverified control.
    for label, anchor in (
        ("simple matcher", BASE_SIMPLE),
        ("alternation matcher", BASE_COMPLEX),
        ("destructure", BASE_DESTRUCTURE),
    ):
        if text.count(anchor) != 1:
            raise SystemExit(
                f"expected one {label} baseline anchor, found {text.count(anchor)}"
            )

    if args.variant == "baseline":
        return

    simple, complex_matcher, destructure = VARIANTS[args.variant]
    text = replace_once(text, BASE_SIMPLE, simple, "simple matcher")
    text = replace_once(text, BASE_COMPLEX, complex_matcher, "alternation matcher")
    text = replace_once(text, BASE_DESTRUCTURE, destructure, "destructure")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
