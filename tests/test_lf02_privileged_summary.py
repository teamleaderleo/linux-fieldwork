from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest


class LF02PrivilegedSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        module_path = repo / (
            "investigations/lf-02-privileged-host-integrations/"
            "summarize_results.py"
        )
        spec = importlib.util.spec_from_file_location("lf02_summary", module_path)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def write_case_files(
        self,
        root: pathlib.Path,
        label: str,
        *,
        logind: str = "",
        dbus_result: str = "",
        dbus_connect: str = "",
        needrestart: str = "",
    ) -> None:
        (root / f"{label}.status").write_text("0\n", encoding="utf-8")
        (root / f"{label}-marker-before.txt").write_text(
            "present=0\n", encoding="utf-8"
        )
        (root / f"{label}-marker-after.txt").write_text(
            "present=0\n", encoding="utf-8"
        )
        (root / f"{label}-dbus-connect.txt").write_text(
            dbus_connect, encoding="utf-8"
        )
        (root / f"{label}-logind-messages.txt").write_text(
            logind, encoding="utf-8"
        )
        (root / f"{label}-dbus-result.txt").write_text(
            dbus_result, encoding="utf-8"
        )
        (root / f"{label}-needrestart.txt").write_text(
            needrestart, encoding="utf-8"
        )

    def make_case(
        self,
        root: pathlib.Path,
        *,
        logind: str = "",
        dbus_result: str = "",
        dbus_connect: str = "",
    ) -> dict:
        label = "default-root"
        self.write_case_files(
            root,
            label,
            logind=logind,
            dbus_result=dbus_result,
            dbus_connect=dbus_connect,
        )
        return self.module.classify_case(root, label)

    def test_unrelated_filesystem_eacces_is_not_logind_access_denied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = self.make_case(
                pathlib.Path(td),
                dbus_result=(
                    'newfstatat(AT_FDCWD, "/target/var/lib/apt/lists/partial", '
                    '0x7fff, 0) = -1 EACCES (Permission denied)\n'
                ),
            )
        self.assertFalse(case["logind_inhibit_message"])
        self.assertFalse(case["logind_access_denied"])
        self.assertEqual(case["logind_result"], "not-observed")

    def test_explicit_dbus_access_denied_is_classified(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = self.make_case(
                pathlib.Path(td),
                logind=(
                    'sendmsg(... "org.freedesktop.login1" ... "Inhibit" ...)\n'
                ),
                dbus_result=(
                    'recvmsg(... "org.freedesktop.DBus.Error.AccessDenied" ...)\n'
                ),
            )
        self.assertTrue(case["logind_inhibit_message"])
        self.assertTrue(case["logind_access_denied"])
        self.assertFalse(case["inhibitor_fd_received"])
        self.assertEqual(case["logind_result"], "access-denied")

    def test_received_inhibitor_fd_is_success_not_access_denied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = self.make_case(
                pathlib.Path(td),
                logind=(
                    'sendmsg(... "org.freedesktop.login1" ... "Inhibit" ...)\n'
                ),
                dbus_result=(
                    'recvmsg(... cmsg_data=[3<anon_inode:[eventfd]>], '
                    'cmsg_type=SCM_RIGHTS ...)\n'
                ),
            )
        self.assertTrue(case["logind_inhibit_message"])
        self.assertTrue(case["inhibitor_fd_received"])
        self.assertFalse(case["logind_access_denied"])
        self.assertEqual(case["logind_result"], "inhibitor-fd-received")

    def test_access_denied_text_without_logind_call_is_not_attributed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = self.make_case(
                pathlib.Path(td),
                dbus_result="recvmsg(... AccessDenied ...)\n",
            )
        self.assertFalse(case["logind_access_denied"])
        self.assertEqual(case["logind_result"], "not-observed")

    def test_component_equality_does_not_imply_full_tree_equality(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for label in self.module.LABELS:
                self.write_case_files(root, label)
                (root / f"{label}-script.normalized").write_text(
                    "postinst\n", encoding="utf-8"
                )
                (root / f"{label}-alternative.normalized").write_text(
                    "auto\n", encoding="utf-8"
                )

            (root / "default-root-tree.tsv").write_text(
                "etc\td\t755\t0\t\n", encoding="utf-8"
            )
            control_tree = (
                "etc\td\t755\t0\t\n"
                "etc/apt/apt.conf.d/99mmdebstrap\tf\t644\t12\t\n"
            )
            (root / "no-inhibit-root-tree.tsv").write_text(
                control_tree, encoding="utf-8"
            )
            (root / "isolated-root-tree.tsv").write_text(
                control_tree, encoding="utf-8"
            )

            summary = self.module.build_summary(root)

        self.assertTrue(summary["target_script_state_equal"])
        self.assertTrue(summary["target_alternatives_state_equal"])
        self.assertFalse(summary["target_tree_state_equal"])
        comparison = summary["target_state_comparison"]
        self.assertTrue(comparison["maintainer_script_log_equal"])
        self.assertTrue(comparison["alternatives_database_equal"])
        self.assertFalse(comparison["full_tree_manifest_equal"])
        self.assertFalse(
            comparison["tree_pairwise"]["default_vs_no_inhibit"]["equal"]
        )
        self.assertGreater(
            comparison["tree_pairwise"]["default_vs_no_inhibit"][
                "difference_lines"
            ],
            0,
        )
        self.assertTrue(
            comparison["tree_pairwise"]["no_inhibit_vs_isolated"]["equal"]
        )


if __name__ == "__main__":
    unittest.main()
