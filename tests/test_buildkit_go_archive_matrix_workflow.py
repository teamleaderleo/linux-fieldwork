from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/buildkit-go-archive-release-readiness.yml"


class BuildkitGoArchiveMatrixWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_runner_and_toolchains_are_exact(self) -> None:
        self.assertIn("runs-on: ubuntu-24.04", self.workflow)
        self.assertNotIn("runs-on: ubuntu-latest", self.workflow)
        self.assertIn('go-version: "1.23.12"', self.workflow)
        self.assertIn('go-version: "1.25.12"', self.workflow)
        self.assertIn('go-directive: "1.23.0"', self.workflow)
        self.assertEqual(self.workflow.count('go-directive: "1.25"'), 3)
        self.assertIn("GOTOOLCHAIN: local", self.workflow)

    def test_proposed_code_has_no_persisted_checkout_credentials(self) -> None:
        self.assertEqual(self.workflow.count("persist-credentials: false"), 2)

    def test_effective_go_and_module_directive_are_verified(self) -> None:
        self.assertIn('test "$(go env GOVERSION)" = "go${EXPECTED_GO_VERSION}"', self.workflow)
        self.assertIn("module_go=$(awk '$1 == \"go\" { print $2; exit }' go-archive/go.mod)", self.workflow)
        self.assertIn('test "$module_go" = "$EXPECTED_GO_DIRECTIVE"', self.workflow)
        self.assertIn('test "$(go env GOTOOLCHAIN)" = local', self.workflow)

    def test_four_version_behavior_contract_is_unchanged(self) -> None:
        for identity in (
            "v0.2.0",
            "v0.2.1",
            "v0.3.0",
            "9e6d2c7c969f4871fe6ded98ae0e28963fde311f",
        ):
            self.assertIn(identity, self.workflow)
        self.assertEqual(self.workflow.count("expect: pass"), 2)
        self.assertEqual(self.workflow.count("expect: fail"), 2)
        self.assertIn("EXPECT_IMPLIED_PARENT", self.workflow)

    def test_disposable_state_checks_remain(self) -> None:
        self.assertIn("Verify disposable state", self.workflow)
        self.assertIn("goarchive-probe.*", self.workflow)
        self.assertIn("git -C go-archive status --short", self.workflow)


if __name__ == "__main__":
    unittest.main()
