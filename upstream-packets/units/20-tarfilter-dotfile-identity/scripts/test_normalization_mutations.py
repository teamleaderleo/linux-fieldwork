#!/usr/bin/env python3
from __future__ import annotations

import json
import posixpath


def baseline(name: str) -> str:
    return "/" + name.lstrip("./")


def first_prefix_only(name: str) -> str:
    if name.startswith("./"):
        name = name[2:]
    return "/" + name.lstrip("/")


def over_normalized(name: str) -> str:
    return posixpath.normpath("/" + name)


def candidate_before_root_repair(name: str) -> str:
    while name.startswith(("./", "/")):
        name = name[2:] if name.startswith("./") else name[1:]
    return "/" + name


def selected(name: str) -> str:
    while name.startswith(("./", "/")):
        name = name[2:] if name.startswith("./") else name[1:]
    if name == ".":
        name = ""
    return "/" + name


expected = {
    ".config": "/.config",
    "config": "/config",
    "..name": "/..name",
    "...name": "/...name",
    "./.config": "/.config",
    "././.config": "/.config",
    "/./.config": "/.config",
    "//./.config": "/.config",
    ".//.config": "/.config",
    "/.//.config": "/.config",
    ".": "/",
    "./": "/",
    "./.": "/",
    "/.": "/",
    "/./": "/",
    "//./.": "/",
    "../config": "/../config",
    "./../config": "/../config",
    "foo/./.config": "/foo/./.config",
}

rows = []
for name, wanted in expected.items():
    rows.append(
        {
            "name": name,
            "expected": wanted,
            "baseline": baseline(name),
            "first_prefix_only": first_prefix_only(name),
            "over_normalized": over_normalized(name),
            "candidate_before_root_repair": candidate_before_root_repair(name),
            "selected": selected(name),
        }
    )

assert baseline(".config") == "/config"
assert baseline("../config") == "/config"
assert first_prefix_only("././.config") == "/./.config"
assert over_normalized("../config") == "/config"
assert over_normalized("foo/./.config") == "/foo/.config"
assert candidate_before_root_repair(".") == "/."
assert candidate_before_root_repair("./.") == "/."
for row in rows:
    assert row["selected"] == row["expected"], row

print(
    json.dumps(
        {
            "claim": "complete leading archive prefixes are removed while filename dots, parent components, and root markers retain identity",
            "losing_mutations": {
                "baseline_character_set_strip": [".config", "../config"],
                "first_prefix_only": ["././.config"],
                "posixpath_normpath": ["../config", "foo/./.config"],
                "candidate_before_root_repair": [".", "./."],
            },
            "rows": rows,
        },
        indent=2,
        sort_keys=True,
    )
)
