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

    def make_case(
        self,
        root: pathlib.Path,
        *,
        logind: str = "",
        dbus_result: str = "",
        dbus_connect: str = "",
    ) -> dict:
        label = "default-root"
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
        (root / f"{label}-needrestart.txt").write_text("", encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
