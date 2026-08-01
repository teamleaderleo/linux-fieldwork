#!/usr/bin/env python3
from __future__ import annotations

import json

WILDCARDS = "*?[\\"


def literal_prefix(pattern: str) -> str:
    positions = [pattern.find(ch) for ch in WILDCARDS if pattern.find(ch) >= 0]
    end = min(positions) if positions else len(pattern)
    prefix = pattern[:end]
    return prefix.rstrip("/")


def dpkg_reincludes(path: str, pattern: str) -> bool:
    """Model dpkg src/main/filters.c parent re-inclusion comparison."""
    prefix = literal_prefix(pattern)
    return path[: len(prefix)] == pattern[: len(prefix)]


def candidate_reincludes(path: str, pattern: str) -> bool:
    """Model the unit-21 component-bounded two-direction predicate."""
    path = path.rstrip("/")
    prefix = literal_prefix(pattern)
    return (
        not prefix
        or path == prefix
        or path.startswith(prefix + "/")
        or prefix.startswith(path + "/")
    )


def main() -> None:
    cases = [
        {
            "case": "exact include retains top ancestor",
            "path": "/usr",
            "include": "/usr/bin/tool",
            "dpkg": False,
            "candidate": True,
            "reason": "the candidate adds the missing ancestor direction",
        },
        {
            "case": "exact include retains immediate ancestor",
            "path": "/usr/bin",
            "include": "/usr/bin/tool",
            "dpkg": False,
            "candidate": True,
            "reason": "the candidate adds the missing ancestor direction",
        },
        {
            "case": "wildcard prefix retains descendant directory",
            "path": "/usr/bin",
            "include": "/usr/*/tool",
            "dpkg": True,
            "candidate": True,
            "reason": "both keep dpkg's conservative fixed-prefix behavior",
        },
        {
            "case": "leading wildcard retains all candidate parents",
            "path": "/opt",
            "include": "*/tool",
            "dpkg": True,
            "candidate": True,
            "reason": "zero-length prefix remains deliberately conservative",
        },
        {
            "case": "exact include does not alias a sibling name",
            "path": "/usr2",
            "include": "/usr",
            "dpkg": True,
            "candidate": False,
            "reason": "component boundaries remove dpkg's plain-prefix over-inclusion",
        },
        {
            "case": "wildcard prefix does not alias a sibling name",
            "path": "/usr2",
            "include": "/usr/*",
            "dpkg": True,
            "candidate": False,
            "reason": "component boundaries remove dpkg's plain-prefix over-inclusion",
        },
        {
            "case": "exact include keeps descendants below the included path",
            "path": "/usr/bin/tool/cache",
            "include": "/usr/bin/tool",
            "dpkg": True,
            "candidate": True,
            "reason": "both retain descendants conservatively",
        },
        {
            "case": "unrelated path remains excluded",
            "path": "/opt",
            "include": "/usr/bin/tool",
            "dpkg": False,
            "candidate": False,
            "reason": "neither predicate retains unrelated paths",
        },
    ]

    output = []
    for case in cases:
        dpkg = dpkg_reincludes(case["path"], case["include"])
        candidate = candidate_reincludes(case["path"], case["include"])
        assert dpkg is case["dpkg"], (case, dpkg)
        assert candidate is case["candidate"], (case, candidate)
        output.append(
            {
                "case": case["case"],
                "path": case["path"],
                "include": case["include"],
                "literal_prefix": literal_prefix(case["include"]),
                "dpkg_reincludes": dpkg,
                "candidate_reincludes": candidate,
                "interpretation": case["reason"],
            }
        )

    print(
        json.dumps(
            {
                "reference": "guillemj/dpkg main src/main/filters.c blob 4fc1600a5717726faddc2fb556730f217e7f22a2",
                "candidate": "unit-21 component-bounded two-direction predicate",
                "cases": output,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
