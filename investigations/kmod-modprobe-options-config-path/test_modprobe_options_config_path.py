#!/usr/bin/env python3
import json
import os
import pathlib
import shutil
import subprocess
import tempfile


def run(argv, *, env=None):
    cp = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    return {"argv": argv, "status": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}


def write_helper(path: pathlib.Path, modprobe: str, output_dir: pathlib.Path):
    path.write_text(
        "#!/bin/sh\n"
        "set -u\n"
        f"printf '%s\\n' \"$MODPROBE_OPTIONS\" > {output_dir / 'env.txt'}\n"
        f"{modprobe} -c > {output_dir / 'nested.stdout'} 2> {output_dir / 'nested.stderr'}\n"
        f"printf '%s\\n' \"$?\" > {output_dir / 'nested.status'}\n"
    )
    path.chmod(0o755)


def case(root: pathlib.Path, label: str, conf_name: str, modprobe: str):
    case_dir = root / label
    case_dir.mkdir()
    conf_dir = case_dir / conf_name
    conf_dir.mkdir()
    output_dir = case_dir / "receipt"
    output_dir.mkdir()
    helper = case_dir / "helper.sh"
    marker = f"lf_{label}_marker"
    write_helper(helper, modprobe, output_dir)
    (conf_dir / "lf.conf").write_text(
        f"blacklist {marker}\n"
        f"install lf_outer_{label} {helper}\n"
    )

    direct = run([modprobe, "-C", str(conf_dir), "-c"])
    outer = run([modprobe, "-C", str(conf_dir), f"lf_outer_{label}"])
    receipt = {
        "modprobe_options": (output_dir / "env.txt").read_text().rstrip("\n"),
        "nested_status": int((output_dir / "nested.status").read_text()),
        "nested_stdout": (output_dir / "nested.stdout").read_text(),
        "nested_stderr": (output_dir / "nested.stderr").read_text(),
    }
    return {
        "label": label,
        "config_dir": str(conf_dir),
        "marker": marker,
        "direct": {
            **direct,
            "marker_count": direct["stdout"].splitlines().count(f"blacklist {marker}"),
        },
        "outer": outer,
        "nested": {
            **receipt,
            "marker_count": receipt["nested_stdout"].splitlines().count(f"blacklist {marker}"),
        },
    }


def quoted_env_control(root: pathlib.Path, modprobe: str):
    conf_dir = root / "quoted env conf"
    conf_dir.mkdir()
    marker = "lf_quoted_env_marker"
    (conf_dir / "lf.conf").write_text(f"blacklist {marker}\n")
    env = os.environ.copy()
    env["MODPROBE_OPTIONS"] = f"-C '{conf_dir}'"
    result = run([modprobe, "-c"], env=env)
    return {
        "config_dir": str(conf_dir),
        "modprobe_options": env["MODPROBE_OPTIONS"],
        **result,
        "marker_count": result["stdout"].splitlines().count(f"blacklist {marker}"),
    }


def parser_controls(root: pathlib.Path, modprobe: str):
    conf_dir = root / "parser conf"
    conf_dir.mkdir()
    marker = "lf_parser_marker"
    (conf_dir / "lf.conf").write_text(f"blacklist {marker}\n")
    values = {
        "normal_single_quotes": f"-C '{conf_dir}'",
        "leading_and_repeated_spaces": f"  -C   '{conf_dir}'  ",
        "tab_separator": f"-C\t{conf_dir}",
        "unmatched_quote": f"-C '{conf_dir}",
    }
    out = {}
    for label, value in values.items():
        env = os.environ.copy()
        env["MODPROBE_OPTIONS"] = value
        result = run([modprobe, "-c"], env=env)
        out[label] = {
            "modprobe_options": value,
            **result,
            "marker_count": result["stdout"].splitlines().count(f"blacklist {marker}"),
        }
    return out


def main():
    modprobe = shutil.which("modprobe")
    if modprobe is None:
        raise SystemExit("modprobe not found")
    version = run([modprobe, "--version"])
    with tempfile.TemporaryDirectory(prefix="lf-kmod-modprobe-options-") as td:
        root = pathlib.Path(td)
        results = {
            "environment": {
                "modprobe": modprobe,
                "version": version,
                "uname": run(["uname", "-srmo"]),
                "euid": os.geteuid(),
            },
            "cases": [
                case(root, "no_space", "confdir", modprobe),
                case(root, "space", "conf dir", modprobe),
            ],
            "quoted_env_control": quoted_env_control(root, modprobe),
            "parser_controls": parser_controls(root, modprobe),
        }

        no_space, space = results["cases"]
        assert no_space["direct"]["status"] == 0
        assert no_space["direct"]["marker_count"] == 1
        assert no_space["outer"]["status"] == 0
        assert no_space["nested"]["nested_status"] == 0
        assert no_space["nested"]["marker_count"] == 1

        assert space["direct"]["status"] == 0
        assert space["direct"]["marker_count"] == 1
        assert space["outer"]["status"] == 0
        assert space["nested"]["nested_status"] == 0
        assert space["nested"]["marker_count"] == 0
        assert space["nested"]["modprobe_options"] == f"-C {space['config_dir']}"

        quoted = results["quoted_env_control"]
        assert quoted["status"] == 0
        assert quoted["marker_count"] == 1

        parsers = results["parser_controls"]
        assert parsers["normal_single_quotes"]["marker_count"] == 1
        assert parsers["leading_and_repeated_spaces"]["status"] == 0
        assert parsers["leading_and_repeated_spaces"]["marker_count"] == 0
        assert parsers["tab_separator"]["status"] == 0
        assert parsers["tab_separator"]["marker_count"] == 0
        assert parsers["unmatched_quote"]["status"] == 0
        assert parsers["unmatched_quote"]["marker_count"] == 0

        root_text = str(root)

        def normalize(value):
            if isinstance(value, str):
                return value.replace(root_text, "$TMP")
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            return value

        print(json.dumps(normalize(results), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
