#!/usr/bin/env python3
"""Run Linux Fieldwork unittest discovery without exact inherited duplicates."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import unittest
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence


LOCAL_METHOD_ONLY_CLASSES = frozenset(
    {
        (
            "test_caching_proxy_parent_swap_race."
            "CachingProxyParentSwapRaceTest"
        ),
        (
            "test_lf23_cancellation_harness_symlink_safety."
            "LF23CancellationHarnessSymlinkSafetyTest"
        ),
        (
            "test_tarfilter_transform_regex_python_group_controls."
            "TarfilterTransformRegexPythonGroupControlsTest"
        ),
    }
)


@dataclass(frozen=True)
class DiscoverySummary:
    discovered: int
    retained: int
    removed: int
    removed_ids: tuple[str, ...]
    policy_classes: tuple[str, ...]


class DiscoveryPolicyError(RuntimeError):
    """Raised when the explicit discovery policy no longer matches the suite."""


def iter_tests(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def discover_suite(
    *,
    start_dir: pathlib.Path,
    pattern: str = "test*.py",
) -> unittest.TestSuite:
    start_dir = start_dir.resolve()
    repository_root = start_dir.parent
    for import_root in (repository_root, start_dir):
        import_path = str(import_root)
        if import_path not in sys.path:
            sys.path.insert(0, import_path)

    loader = unittest.TestLoader()
    return loader.discover(
        str(start_dir),
        pattern=pattern,
        top_level_dir=str(start_dir),
    )


def apply_discovery_policy(
    suite: unittest.TestSuite,
    *,
    policy_classes: frozenset[str] = LOCAL_METHOD_ONLY_CLASSES,
    require_all_policy_classes: bool = True,
) -> tuple[unittest.TestSuite, DiscoverySummary]:
    retained: list[unittest.TestCase] = []
    removed_ids: list[str] = []
    observed_policy_classes: set[str] = set()
    discovered = 0

    for test in iter_tests(suite):
        discovered += 1
        test_class = type(test)
        class_id = f"{test_class.__module__}.{test_class.__name__}"
        method_name = getattr(test, "_testMethodName", None)

        if class_id in policy_classes:
            observed_policy_classes.add(class_id)
            if method_name not in test_class.__dict__:
                removed_ids.append(test.id())
                continue

        retained.append(test)

    if require_all_policy_classes:
        missing = sorted(policy_classes - observed_policy_classes)
        if missing:
            raise DiscoveryPolicyError(
                "discovery policy class was not found: " + ", ".join(missing)
            )

    summary = DiscoverySummary(
        discovered=discovered,
        retained=len(retained),
        removed=len(removed_ids),
        removed_ids=tuple(sorted(removed_ids)),
        policy_classes=tuple(sorted(observed_policy_classes)),
    )
    return unittest.TestSuite(retained), summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Discover and run Linux Fieldwork unit tests while suppressing "
            "inherited test methods only for explicitly classified exact-duplicate "
            "extension classes."
        )
    )
    parser.add_argument(
        "--start-dir",
        default="tests",
        help="unittest discovery directory (default: tests)",
    )
    parser.add_argument(
        "--pattern",
        default="test*.py",
        help="unittest discovery filename pattern (default: test*.py)",
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        choices=(0, 1, 2),
        default=2,
        help="unittest runner verbosity (default: 2)",
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--list",
        action="store_true",
        help="list retained test IDs without executing them",
    )
    output.add_argument(
        "--json",
        action="store_true",
        help="emit the discovery summary as JSON without executing tests",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        suite = discover_suite(
            start_dir=pathlib.Path(args.start_dir),
            pattern=args.pattern,
        )
        filtered, summary = apply_discovery_policy(suite)
    except (ImportError, OSError, DiscoveryPolicyError) as error:
        print(f"fieldwork unittest discovery failed: {error}", file=sys.stderr)
        return 2

    if args.json:
        payload = {"schema_version": 1, **asdict(summary)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.list:
        for test in iter_tests(filtered):
            print(test.id())
        print(
            f"retained {summary.retained} of {summary.discovered} tests; "
            f"removed {summary.removed} exact inherited duplicate(s)",
            file=sys.stderr,
        )
        return 0

    print(
        f"fieldwork discovery retained {summary.retained} of "
        f"{summary.discovered} tests; removed {summary.removed} exact "
        "inherited duplicate(s)",
        file=sys.stderr,
    )
    result = unittest.TextTestRunner(verbosity=args.verbosity).run(filtered)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
