from __future__ import annotations

import os
import pathlib
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_TESTSUITE = ROOT / "upstream/mmdebstrap/debian/tests/testsuite"
CWD_CHANGING_TEST = (
    ROOT / "upstream/mmdebstrap/tests/cwd-directory-not-accessible-by-unshared-user"
)
PATCH = (
    ROOT
    / "investigations/mmdebstrap-autopkgtest-1141078"
    / "installed-command-wrapper.patch"
)


def extract_proxy(testsuite: str) -> str:
    marker = "cat << 'END' > ./mmdebstrap\n"
    start = testsuite.index(marker) + len(marker)
    end = testsuite.index("\nEND\nchmod 0755 ./mmdebstrap", start)
    return testsuite[start:end] + "\n"


class MmdebstrapAutopkgtestProxyInstallationTest(unittest.TestCase):
    def test_patch_creates_the_proxy_at_the_exported_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mmdebstrap-autopkgtest-proxy-install-"
        ) as td:
            root = pathlib.Path(td)
            tree = root / "tree"
            tests_dir = tree / "debian/tests"
            tests_dir.mkdir(parents=True)
            shutil.copy2(SOURCE_TESTSUITE, tests_dir / "testsuite")

            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "-p1",
                    "-d",
                    str(tree),
                    "-i",
                    str(PATCH),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            patched_path = tests_dir / "testsuite"
            patched = patched_path.read_text(encoding="utf-8")
            syntax = subprocess.run(
                ["/bin/sh", "-n", str(patched_path)],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)

            install_line = 'install -m 0755 ./mmdebstrap "$AUTOPKGTEST_TMP/mmdebstrap"'
            self.assertIn(install_line, patched)
            command_match = re.search(r'env CMD="([^"]+)" DEFAULT_DIST=', patched)
            self.assertIsNotNone(command_match)

            source_proxy = tree / "mmdebstrap"
            source_proxy.write_text(extract_proxy(patched), encoding="utf-8")
            source_proxy.chmod(0o755)
            autopkgtest_tmp = root / "autopkgtest-tmp"
            autopkgtest_tmp.mkdir()
            env = dict(os.environ, AUTOPKGTEST_TMP=str(autopkgtest_tmp))
            installed = subprocess.run(
                ["/bin/sh", "-eu", "-c", install_line],
                cwd=tree,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)

            installed_proxy = autopkgtest_tmp / "mmdebstrap"
            self.assertEqual(installed_proxy.read_bytes(), source_proxy.read_bytes())
            self.assertTrue(installed_proxy.stat().st_mode & stat.S_IXUSR)

            # Replace the copied Perl proxy with an observable stand-in after
            # proving that the patch installs the real bytes at this path.
            result_path = root / "proxy-result"
            installed_proxy.write_text(
                "#!/bin/sh\n"
                'printf "%s\\n" "$PWD" >"$PROXY_RESULT"\n'
                'printf "%s\\n" "$@" >>"$PROXY_RESULT"\n',
                encoding="utf-8",
            )
            installed_proxy.chmod(0o755)
            source_proxy.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
            source_proxy.chmod(0o755)

            command = command_match.group(1)
            expanded_command = command.replace(
                "$AUTOPKGTEST_TMP", str(autopkgtest_tmp)
            ).replace("$SRC", str(tree))
            rendered = CWD_CHANGING_TEST.read_text(encoding="utf-8").replace(
                "{{ CMD }}", expanded_command
            )
            self.assertIn(
                f'set -- "$@" {autopkgtest_tmp}/mmdebstrap --setup-hook=', rendered
            )

            changed_directory = root / "changed-directory"
            changed_directory.mkdir()
            invocation = (
                f"CMD={shlex.quote(expanded_command)}\n"
                f"set -- env --chdir={shlex.quote(str(changed_directory))}\n"
                'set -- "$@" $CMD\n'
                '"$@"\n'
            )
            invoked = subprocess.run(
                ["/bin/sh", "-eu", "-c", invocation],
                env=dict(os.environ, PROXY_RESULT=str(result_path)),
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(invoked.returncode, 0, invoked.stderr)
            result = result_path.read_text(encoding="utf-8").splitlines()

            self.assertEqual(result[0], str(changed_directory))
            self.assertEqual(
                result[1:],
                [
                    f"--setup-hook={tree}/debian/tests/sourcesfilter",
                    f"--hook-dir={tree}/hooks/file-mirror-automount",
                ],
            )


if __name__ == "__main__":
    unittest.main()
