from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/curl-asio-multi-socket-rearm.yml"


class CurlAsioRearmWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_runner_and_checkout_boundary_are_fixed(self) -> None:
        self.assertIn("runs-on: ubuntu-24.04", self.workflow)
        self.assertNotIn("runs-on: ubuntu-latest", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)
        permissions = self.workflow.split("jobs:", 1)[0]
        self.assertIn("  contents: read", permissions)
        self.assertNotIn("write", permissions)

    def test_fixture_builds_outside_the_checkout(self) -> None:
        self.assertIn('runtime="${RUNNER_TEMP}/curl-asio-rearm"', self.workflow)
        self.assertIn('"$runtime/fixture"', self.workflow)
        self.assertNotIn("fixture.cpp -o fixture", self.workflow)

    def test_two_runs_must_match_and_preserve_expected_semantics(self) -> None:
        self.assertIn('for attempt in 1 2; do', self.workflow)
        self.assertIn('cmp "$evidence/run-1.txt" "$evidence/run-2.txt"', self.workflow)
        self.assertIn("one-shot: completed=0 timed_out=1 reads=1 body='hello '", self.workflow)
        self.assertIn("rearm: completed=1 timed_out=0 reads=2", self.workflow)
        self.assertIn("curl multi-socket Asio re-arm discriminator: PASS", self.workflow)

    def test_artifact_contains_identity_and_is_required(self) -> None:
        for item in (
            "g++ --version",
            "pkg-config --modversion libcurl",
            "BOOST_LIB_VERSION",
            "sha256sum experiments/curl-asio-multi-socket-rearm/fixture.cpp",
        ):
            self.assertIn(item, self.workflow)
        self.assertIn("actions/upload-artifact@v4", self.workflow)
        self.assertIn("if-no-files-found: error", self.workflow)
        self.assertIn("retention-days: 30", self.workflow)

    def test_cleanup_restores_checkout_and_runtime(self) -> None:
        self.assertIn("if: always()", self.workflow)
        self.assertIn('rm -rf "$runtime" "$evidence"', self.workflow)
        self.assertIn('test -z "$(git status --short)"', self.workflow)
        self.assertIn('test ! -e "$runtime"', self.workflow)


if __name__ == "__main__":
    unittest.main()
