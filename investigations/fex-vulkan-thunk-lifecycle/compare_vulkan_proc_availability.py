#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

COLUMNS = ("direct", "gipa_null", "gipa_instance", "gdpa_device")


def load(path: Path):
    rows = {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        expected = ["name", *COLUMNS]
        if reader.fieldnames != expected:
            raise SystemExit(f"{path}: unexpected header {reader.fieldnames!r}, expected {expected!r}")
        for row in reader:
            name = row.pop("name")
            rows[name] = {k: int(v) for k, v in row.items()}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("native", type=Path)
    ap.add_argument("fex", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--text", type=Path)
    args = ap.parse_args()

    native = load(args.native)
    fex = load(args.fex)
    native_names = set(native)
    fex_names = set(fex)
    if native_names != fex_names:
        missing_in_fex = sorted(native_names - fex_names)
        extra_in_fex = sorted(fex_names - native_names)
        raise SystemExit(f"name sets differ: missing_in_fex={missing_in_fex[:20]} extra_in_fex={extra_in_fex[:20]}")

    summary = {
        "command_count": len(native),
        "columns": {},
    }
    lines = [f"command_count={len(native)}"]

    for column in COLUMNS:
        fex_extra = sorted(name for name in native if native[name][column] == 0 and fex[name][column] == 1)
        fex_missing = sorted(name for name in native if native[name][column] == 1 and fex[name][column] == 0)
        matches = len(native) - len(fex_extra) - len(fex_missing)
        summary["columns"][column] = {
            "matches": matches,
            "fex_extra_nonnull": fex_extra,
            "fex_missing_nonnull": fex_missing,
        }
        lines.append(
            f"{column}: matches={matches} fex_extra_nonnull={len(fex_extra)} fex_missing_nonnull={len(fex_missing)}"
        )
        if fex_extra:
            lines.append(f"  extra: {', '.join(fex_extra)}")
        if fex_missing:
            lines.append(f"  missing: {', '.join(fex_missing)}")

    text = "\n".join(lines) + "\n"
    print(text, end="")
    if args.json:
        args.json.write_text(json.dumps(summary, indent=2) + "\n")
    if args.text:
        args.text.write_text(text)


if __name__ == "__main__":
    main()
