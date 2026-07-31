from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


OPTIMIZED_CHILD = "LF_PARENT_SWAP_OPTIMIZED_CHILD"
REPOSITORY = pathlib.Path(__file__).resolve().parents[1]
RACE_SUITE = REPOSITORY / "tests/test_caching_proxy_parent_swap_race.py"


def checkout_generated_inventory() -> list[str]:
    inventory: set[str] = set()
    for path in REPOSITORY.glob("complete-*"):
        inventory.add(path.relative_to(REPOSITORY).as_posix())
    for root in (
        REPOSITORY / "tests",
        REPOSITORY / "investigations/caching-proxy-complete-stack",
        REPOSITORY / "investigations/caching-proxy-parent-swap-race",
    ):
        if not root.exists():
            continue
        for path in root.rglob("__pycache__"):
            inventory.add(path.relative_to(REPOSITORY).as_posix())
    return sorted(inventory)


def runtime_inventory(root: pathlib.Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


class CachingProxyParentSwapCleanupTest(unittest.TestCase):
    def run_isolated_suite(self, *, optimized: bool) -> None:
        before_checkout = checkout_generated_inventory()
        label = "optimized" if optimized else "ordinary"

        with tempfile.TemporaryDirectory(prefix=f"parent-swap-{label}-") as tmp:
            runtime_root = pathlib.Path(tmp) / "runtime"
            runtime_root.mkdir()
            environment = os.environ.copy()
            environment.update(
                {
                    "TMPDIR": str(runtime_root),
                    "TEMP": str(runtime_root),
                    "TMP": str(runtime_root),
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            if optimized:
                environment[OPTIMIZED_CHILD] = "1"
            else:
                environment.pop(OPTIMIZED_CHILD, None)

            command = [sys.executable, "-B"]
            if optimized:
                command.append("-O")
            command.append(str(RACE_SUITE))

            completed = subprocess.run(
                command,
                cwd=REPOSITORY,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=300,
            )
            output = completed.stdout + completed.stderr
            self.assertEqual(completed.returncode, 0, output)
            self.assertEqual(
                runtime_inventory(runtime_root),
                [],
                f"{label} suite retained temporary state\n{output}",
            )

        self.assertEqual(
            checkout_generated_inventory(),
            before_checkout,
            f"{label} suite changed checkout-generated state",
        )

    def test_ordinary_suite_uses_empty_dedicated_temporary_root(self) -> None:
        self.run_isolated_suite(optimized=False)

    def test_optimized_suite_uses_empty_dedicated_temporary_root(self) -> None:
        self.run_isolated_suite(optimized=True)


if __name__ == "__main__":
    unittest.main()
