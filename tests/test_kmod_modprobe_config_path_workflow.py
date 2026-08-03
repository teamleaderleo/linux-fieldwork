from pathlib import Path
import unittest


WORKFLOW = Path(".github/workflows/kmod-modprobe-config-path.yml")


class KmodModprobeConfigPathWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_pins_exact_public_and_characterization_sources(self) -> None:
        self.assertIn("5086df53090b2fe9fa1c31351c05a78a12a4ba71", self.text)
        self.assertIn("2e52d25e54a94fb531fd442079c7cf686f3e910b", self.text)

    def test_disables_only_unavailable_optional_mbedtls_backend(self) -> None:
        self.assertNotIn("libmbedtls-dev", self.text)
        self.assertGreaterEqual(self.text.count("-Dmbedtls=disabled"), 2)
        for retained_dependency in (
            "libssl-dev",
            "liblzma-dev",
            "libzstd-dev",
            "zlib1g-dev",
        ):
            self.assertIn(retained_dependency, self.text)

    def test_clang_sanitizer_runtime_is_explicit(self) -> None:
        self.assertGreaterEqual(self.text.count("libclang-rt-18-dev"), 2)
        self.assertGreaterEqual(self.text.count("-Db_lundef=false"), 2)
        self.assertIn("clang -print-resource-dir", self.text)

    def test_native_gate_uses_compiler_identity_and_expected_loss(self) -> None:
        self.assertGreaterEqual(self.text.count("CC: ${{ matrix.compiler }}"), 3)
        self.assertIn("PASSED: modprobe_options_config_path_control", self.text)
        self.assertIn("FAILED: modprobe_options_config_path_space", self.text)
        self.assertIn("unexpected native failures", self.text)


if __name__ == "__main__":
    unittest.main()
