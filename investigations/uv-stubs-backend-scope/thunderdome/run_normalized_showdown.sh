#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$PWD"
BASE="$ROOT_DIR/uv-base"
SUPPORT="$ROOT_DIR/uv-support"
REJECT="$ROOT_DIR/uv-reject"
TARGET="${RUNNER_TEMP:-/tmp}/uv-thunderdome-target"

rm -rf "$SUPPORT" "$REJECT" "$TARGET"
cp -a "$BASE" "$SUPPORT"
cp -a "$BASE" "$REJECT"

python investigations/uv-stubs-backend-scope/thunderdome/normalized_transform.py \
  support "$SUPPORT/crates/uv/src/commands/project/init.rs"
python investigations/uv-stubs-backend-scope/thunderdome/normalized_transform.py \
  reject "$REJECT/crates/uv/src/commands/project/init.rs"

(cd "$SUPPORT" && cargo fmt --all)
(cd "$REJECT" && cargo fmt --all)

git -C "$SUPPORT" diff --check
git -C "$REJECT" diff --check

echo '=== SUPPORT DIFF STAT ==='
git -C "$SUPPORT" diff --stat
echo '=== REJECT DIFF STAT ==='
git -C "$REJECT" diff --stat

echo '=== POLICY-ONLY SOURCE DIFF (reject -> support) ==='
diff -u \
  "$REJECT/crates/uv/src/commands/project/init.rs" \
  "$SUPPORT/crates/uv/src/commands/project/init.rs" || true

export CARGO_TARGET_DIR="$TARGET"
cargo build --manifest-path "$SUPPORT/Cargo.toml" --package uv --bin uv
cp "$TARGET/debug/uv" "${RUNNER_TEMP:-/tmp}/uv-support"
cargo build --manifest-path "$REJECT/Cargo.toml" --package uv --bin uv
cp "$TARGET/debug/uv" "${RUNNER_TEMP:-/tmp}/uv-reject"

"${RUNNER_TEMP:-/tmp}/uv-support" --version
"${RUNNER_TEMP:-/tmp}/uv-reject" --version

exercise_policy() {
  local policy="$1"
  local UV="$2"
  local WORK="${RUNNER_TEMP:-/tmp}/normalized-$policy"
  rm -rf "$WORK"
  mkdir -p "$WORK"

  init_supported() {
    local label="$1"
    local backend="$2"
    mkdir -p "$WORK/$label"
    if [[ -n "$backend" ]]; then
      (cd "$WORK/$label" && "$UV" init --package --name foo-stubs --build-backend "$backend" --no-workspace --vcs none)
    else
      (cd "$WORK/$label" && "$UV" init --package --name foo-stubs --no-workspace --vcs none)
    fi
    (cd "$WORK/$label" && "$UV" build --wheel --out-dir dist)
  }

  init_supported uv ""
  init_supported hatch hatchling
  init_supported poetry poetry
  init_supported flit flit
  init_supported pdm pdm
  init_supported setuptools setuptools
  if [[ "$policy" == support ]]; then
    init_supported scikit scikit
  fi

  mkdir -p "$WORK/lib-hatch"
  (cd "$WORK/lib-hatch" && "$UV" init --lib --name foo-stubs --build-backend hatchling --no-workspace --vcs none)
  (cd "$WORK/lib-hatch" && "$UV" build --wheel --out-dir dist)

  if [[ "$policy" == support ]]; then
    mkdir -p "$WORK/lib-scikit"
    (cd "$WORK/lib-scikit" && "$UV" init --lib --name foo-stubs --build-backend scikit --no-workspace --vcs none)
    (cd "$WORK/lib-scikit" && "$UV" build --wheel --out-dir dist)
  fi

  mkdir -p "$WORK/app-hatch"
  (cd "$WORK/app-hatch" && "$UV" init --app --package --name foo-stubs --build-backend hatchling --no-workspace --vcs none)
  (cd "$WORK/app-hatch" && "$UV" build --wheel --out-dir dist)

  mkdir -p "$WORK/canonical-alias"
  (cd "$WORK/canonical-alias" && "$UV" init --package --name foo_stubs --no-workspace --vcs none)
  (cd "$WORK/canonical-alias" && "$UV" build --wheel --out-dir dist)

  reject_without_side_effects() {
    local label="$1"
    local mode="$2"
    local backend="$3"
    set +e
    (cd "$WORK" && "$UV" init "$label" "$mode" --name foo-stubs --build-backend "$backend" --no-workspace) >"$WORK/$label.log" 2>&1
    local code=$?
    set -e
    cat "$WORK/$label.log"
    [[ "$code" -ne 0 ]]
    [[ ! -e "$WORK/$label" ]]
  }

  reject_without_side_effects reject-maturin-package --package maturin
  reject_without_side_effects reject-maturin-lib --lib maturin
  if [[ "$policy" == reject ]]; then
    reject_without_side_effects reject-scikit-package --package scikit
    reject_without_side_effects reject-scikit-lib --lib scikit
  fi

  for backend in scikit maturin; do
    mkdir -p "$WORK/bare-$backend"
    (cd "$WORK/bare-$backend" && "$UV" init --bare --name foo-stubs --build-backend "$backend" --no-workspace --vcs none)
    [[ -f "$WORK/bare-$backend/pyproject.toml" ]]
    [[ ! -e "$WORK/bare-$backend/src" ]]
  done

  for backend in hatchling poetry flit pdm setuptools; do
    local label="ordinary-${backend//[^a-zA-Z0-9]/-}"
    mkdir -p "$WORK/$label"
    (cd "$WORK/$label" && "$UV" init --package --name foo --build-backend "$backend" --no-workspace --vcs none)
  done

  mkdir -p "$WORK/ordinary-scikit"
  (cd "$WORK/ordinary-scikit" && "$UV" init --package --name foo --build-backend scikit --no-workspace --vcs none)
  [[ -f "$WORK/ordinary-scikit/CMakeLists.txt" ]]
  [[ -f "$WORK/ordinary-scikit/src/main.cpp" ]]
  [[ -f "$WORK/ordinary-scikit/src/foo/_core.pyi" ]]

  python - "$WORK" "$policy" <<'PY'
import configparser
import io
import pathlib
import sys
import tomllib
import zipfile

root = pathlib.Path(sys.argv[1])
policy = sys.argv[2]
supported = [
    "uv", "hatch", "poetry", "flit", "pdm", "setuptools",
    "lib-hatch", "app-hatch", "canonical-alias",
]
if policy == "support":
    supported += ["scikit", "lib-scikit"]

for label in supported:
    project = root / label
    data = tomllib.loads((project / "pyproject.toml").read_text())
    if data["project"]["name"] != "foo-stubs":
        raise SystemExit(f"{policy}/{label}: non-canonical project name")
    if "scripts" in data.get("project", {}):
        raise SystemExit(f"{policy}/{label}: runtime scripts leaked")
    if not (project / "src/foo-stubs/__init__.pyi").is_file():
        raise SystemExit(f"{policy}/{label}: stub source missing")
    if (project / "src/foo_stubs/__init__.py").exists():
        raise SystemExit(f"{policy}/{label}: runtime compatibility package leaked")

    wheels = list((project / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"{policy}/{label}: expected one wheel, got {len(wheels)}")
    with zipfile.ZipFile(wheels[0]) as zf:
        names = sorted(zf.namelist())
        if "foo-stubs/__init__.pyi" not in names:
            raise SystemExit(f"{policy}/{label}: wheel omitted stub: {names}")
        console_scripts = []
        for name in names:
            if not name.endswith(".dist-info/entry_points.txt"):
                continue
            parser = configparser.ConfigParser()
            parser.optionxform = str
            parser.read_file(io.StringIO(zf.read(name).decode()))
            if parser.has_section("console_scripts"):
                console_scripts.extend(parser.options("console_scripts"))
        if console_scripts:
            raise SystemExit(f"{policy}/{label}: unexpected console scripts {console_scripts}")
    print(f"PASS {policy}/{label}: {wheels[0].name}")

expected = {
    "hatch": '[tool.hatch.build.targets.wheel]\npackages = ["src/foo-stubs"]',
    "poetry": '[tool.poetry]\npackages = [{ include = "foo-stubs", from = "src" }]',
    "flit": 'requires = ["flit_core>=4,<5"]',
    "pdm": '[tool.pdm.build]\nincludes = ["src/foo-stubs"]',
    "setuptools": '[tool.setuptools.package-data]\n"*" = ["*.pyi"]',
}
if policy == "support":
    expected["scikit"] = '[tool.scikit-build]\nminimum-version = "build-system.requires"\nwheel.cmake = false\nwheel.packages = ["src/foo-stubs"]'
for label, snippet in expected.items():
    if snippet not in (root / label / "pyproject.toml").read_text():
        raise SystemExit(f"{policy}/{label}: missing expected adapter")

for label, forbidden in {
    "ordinary-hatchling": "[tool.hatch.build.targets.wheel]",
    "ordinary-poetry": "[tool.poetry]",
    "ordinary-pdm": "[tool.pdm.build]",
    "ordinary-setuptools": "[tool.setuptools.package-data]",
}.items():
    if forbidden in (root / label / "pyproject.toml").read_text():
        raise SystemExit(f"{policy}/{label}: stub config leaked")

if 'requires = ["flit_core>=3.2,<4"]' not in (root / "ordinary-flit" / "pyproject.toml").read_text():
    raise SystemExit(f"{policy}: ordinary Flit requirement changed")

ordinary_scikit = (root / "ordinary-scikit" / "pyproject.toml").read_text()
for snippet in ['build-dir = "build/{wheel_tag}"', "pybind11>=3", "CMakeLists.txt"]:
    if snippet not in ordinary_scikit:
        raise SystemExit(f"{policy}: ordinary Scikit template changed: {snippet}")
PY
}

exercise_policy support "${RUNNER_TEMP:-/tmp}/uv-support"
exercise_policy reject "${RUNNER_TEMP:-/tmp}/uv-reject"
