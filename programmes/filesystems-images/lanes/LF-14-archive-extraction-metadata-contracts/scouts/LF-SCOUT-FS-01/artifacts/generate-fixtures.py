#!/usr/bin/env python3
from __future__ import annotations
import argparse
import io
import os
import pathlib
import subprocess
import tarfile

EPOCH = 946684800

def reg(name: str, data: bytes, *, mode: int = 0o644, uid: int = 0, gid: int = 0, pax=None):
    ti = tarfile.TarInfo(name)
    ti.size = len(data)
    ti.mode = mode
    ti.uid = uid
    ti.gid = gid
    ti.uname = ""
    ti.gname = ""
    ti.mtime = EPOCH
    if pax:
        ti.pax_headers = dict(pax)
    return ti, io.BytesIO(data)

def write_one(path: pathlib.Path, entries):
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as tf:
        for ti, fp in entries:
            tf.addfile(ti, fp)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("output", type=pathlib.Path)
    ns = ap.parse_args()
    out = ns.output
    out.mkdir(parents=True, exist_ok=True)

    write_one(out / "traversal.tar", [reg("../lf14-traversal-escape", b"TRAVERSAL\n")])
    write_one(out / "absolute.tar", [reg("/lf14-absolute-escape", b"ABSOLUTE\n")])

    sym = tarfile.TarInfo("pivot")
    sym.type = tarfile.SYMTYPE
    sym.linkname = "../lf14-symlink-outside"
    sym.mode = 0o777
    sym.mtime = EPOCH
    write_one(out / "symlink.tar", [(sym, None), reg("pivot/payload", b"SYMLINK\n")])

    base, basefp = reg("hard/base", b"HARDLINK\n")
    link = tarfile.TarInfo("hard/peer")
    link.type = tarfile.LNKTYPE
    link.linkname = "hard/base"
    link.mode = 0o640
    link.mtime = EPOCH
    write_one(out / "hardlink.tar", [(base, basefp), (link, None)])

    write_one(out / "numeric-owner.tar", [reg("owner/file", b"OWNER\n", uid=12345, gid=23456)])
    write_one(out / "mode-bits.tar", [reg("mode/file", b"MODE\n", mode=0o751)])
    write_one(out / "timestamps.tar", [reg("time/file", b"TIME\n")])
    write_one(out / "xattr.tar", [reg("xattr/file", b"XATTR\n", pax={"SCHILY.xattr.user.lf14": "corpus"})])

    sparse_src = out / ".sparse-source"
    with sparse_src.open("wb") as fp:
        fp.write(b"BEGIN")
        fp.seek(1024 * 1024)
        fp.write(b"MIDDLE")
        fp.seek(8 * 1024 * 1024)
        fp.write(b"END")
    os.utime(sparse_src, (EPOCH, EPOCH))
    subprocess.run([
        "tar", "--format=pax", "--sparse", "--numeric-owner",
        "--owner=0", "--group=0", "-cf", str(out / "sparse.tar"),
        "-C", str(out), sparse_src.name
    ], check=True)
    sparse_src.unlink()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
