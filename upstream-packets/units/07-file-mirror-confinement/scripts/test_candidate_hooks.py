#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path

def executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8"); path.chmod(0o755)

def fields(path: Path) -> list[str]:
    return [] if not path.exists() else [x.decode() for x in path.read_bytes().split(b"\0") if x]

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--setup", required=True, type=Path)
    p.add_argument("--cleanup", required=True, type=Path)
    a = p.parse_args()
    setup, cleanup = a.setup.resolve(), a.cleanup.resolve()
    checks: list[str] = []

    for hook in (setup, cleanup):
        r = subprocess.run(["/bin/sh", "-n", str(hook)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    checks.append("shell-syntax")

    with tempfile.TemporaryDirectory(prefix="unit07-fork-matrix-") as tmp:
        w = Path(tmp); fake = w/"fakebin"; fake.mkdir()
        mounts, actions, uris = w/"mounts", w/"actions", w/"uris"
        executable(fake/"apt-get", '#!/bin/sh\ncat "$URI_FILE"\n')
        executable(fake/"mount", '#!/bin/sh\nprintf "%s\\0" "$@" >>"$MOUNT_LOG"\n')
        executable(fake/"umount", '#!/bin/sh\nprintf "umount\\0%s\\0" "$@" >>"$ACTION_LOG"\n')
        executable(fake/"rm", '''#!/bin/sh
if [ "${1:-}" = -r ]; then
  printf "rm\\0" >>"$ACTION_LOG"; printf "%s\\0" "$@" >>"$ACTION_LOG"; exit 0
fi
exec /bin/rm "$@"
''')
        def env(mode="root", uri="", include=""):
            uris.write_text(uri + ("\n" if uri else ""), encoding="utf-8")
            e = os.environ.copy()
            e.update(PATH=f"{fake}:/usr/bin:/bin", URI_FILE=str(uris),
                     MOUNT_LOG=str(mounts), ACTION_LOG=str(actions),
                     MMDEBSTRAP_APT_CONFIG="/dev/null", MMDEBSTRAP_MODE=mode,
                     MMDEBSTRAP_INCLUDE=include, MMDEBSTRAP_ARGV0="/bin/false",
                     MMDEBSTRAP_HOOK="file-mirror-automount",
                     MMDEBSTRAP_HOOKSOCK="9", MMDEBSTRAP_VERBOSITY="1")
            return e
        def run(hook, root, mode="root", uri="", include=""):
            return subprocess.run(["/bin/sh", str(hook), str(root)],
                env=env(mode, uri, include), capture_output=True, text=True, timeout=15)

        mounts.unlink(missing_ok=True)
        root=w/"traversal/a/b/root"; root.mkdir(parents=True)
        r=run(setup, root, uri="file:///../../etc")
        assert r.returncode==0 and "refusing unsafe" in r.stderr and not mounts.exists()
        assert not (root/"run/mmdebstrap/file-mirror-automount").exists()
        checks.append("traversal-rejected")

        mounts.unlink(missing_ok=True); actions.unlink(missing_ok=True)
        r=run(setup, Path("/"), uri="file:///tmp")
        assert r.returncode!=0 and "refusing filesystem root" in r.stderr
        assert not mounts.exists() and not actions.exists()
        checks.append("root-refused")

        mounts.unlink(missing_ok=True)
        src=w/"repository"; src.mkdir(); root=w/"ordinary"; root.mkdir()
        r=run(setup, root, uri=f"file://{src}"); target=root.resolve()/src.relative_to("/")
        assert r.returncode==0 and fields(mounts)==["-o","ro,bind",str(src.resolve()),str(target)]
        assert fields(root/"run/mmdebstrap/file-mirror-automount")==[str(src.relative_to("/"))]
        checks.append("ordinary-repository")

        mounts.unlink(missing_ok=True)
        real=w/"canonical"; real.mkdir(); link=w/"repository-link"; link.symlink_to(real, target_is_directory=True)
        root=w/"symlink"; root.mkdir(); r=run(setup, root, uri=f"file://{link}")
        target=root.resolve()/link.relative_to("/")
        assert r.returncode==0 and fields(mounts)==["-o","ro,bind",str(real.resolve()),str(target)]
        assert fields(root/"run/mmdebstrap/file-mirror-automount")==[str(link.relative_to("/"))]
        checks.append("symlink-uri-reachable")

        mounts.unlink(missing_ok=True)
        spelling=w/"sources/spelling"; repo=w/"sources/repository"; spelling.mkdir(parents=True); repo.mkdir()
        root=w/"parent"; root.mkdir(); r=run(setup, root, uri=f"file://{spelling}/../repository")
        assert r.returncode==0 and "refusing unsafe" in r.stderr and not mounts.exists()
        checks.append("parent-component-rejected")

        mounts.unlink(missing_ok=True)
        pkg=w/"package.deb"; pkg.write_bytes(b"package"); root=w/"package"; root.mkdir()
        r=run(setup, root, include=str(pkg)); target=root.resolve()/pkg.relative_to("/")
        assert r.returncode==0 and fields(mounts)==["-o","bind",str(pkg.resolve()),str(target)]
        checks.append("package-contained")

        for mode in ("root","fakechroot"):
            actions.unlink(missing_ok=True)
            root=w/f"cleanup-{mode}"; valid=root/"var/cache/local"; valid.mkdir(parents=True)
            marker=root/"run/mmdebstrap/file-mirror-automount"; marker.parent.mkdir(parents=True)
            marker.write_bytes(b"var/cache/local\0../../outside\0")
            r=run(cleanup, root, mode); assert r.returncode!=0 and not actions.exists() and marker.exists()
            marker.write_bytes(b"var/cache/local\0"); r=run(cleanup, root, mode); assert r.returncode==0
            expected=["umount",str(valid.resolve())] if mode=="root" else ["rm","-r",str(valid.resolve())]
            assert fields(actions)==expected and not marker.exists()
            before=actions.read_bytes(); assert run(cleanup, root, mode).returncode==0 and actions.read_bytes()==before
            checks.append(f"cleanup-preflight-rerun-{mode}")

        actions.unlink(missing_ok=True)
        root=w/"cleanup-symlink"; root.mkdir(); outside=w/"outside"; outside.mkdir()
        (root/"escape").symlink_to(outside, target_is_directory=True)
        marker=root/"run/mmdebstrap/file-mirror-automount"; marker.parent.mkdir(parents=True); marker.write_bytes(b"escape/target\0")
        r=run(cleanup, root); assert r.returncode!=0 and not actions.exists() and marker.exists()
        checks.append("cleanup-symlink-rejected")

    print(json.dumps({"count":len(checks),"results":checks,
        "setup_sha256":hashlib.sha256(setup.read_bytes()).hexdigest(),
        "cleanup_sha256":hashlib.sha256(cleanup.read_bytes()).hexdigest()}, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
