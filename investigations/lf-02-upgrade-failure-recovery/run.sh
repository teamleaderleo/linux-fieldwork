#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
investigation_dir="$repo_root/investigations/lf-02-upgrade-failure-recovery"
result_dir="$investigation_dir/results"
runtime="${RUNNER_TEMP:-/tmp}/lf-02-upgrade-failure-recovery"
package_dir="$runtime/packages"
target="$runtime/target"
scout_artifacts="$repo_root/programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/scouts/LF-SCOUT-ROOT-01/artifacts"
classifier="$scout_artifacts/classify-strace.py"
provenance_tool="$scout_artifacts/write-provenance.py"
summary_tool="$investigation_dir/summarize.py"

cleanup() {
    if [[ "${KEEP_RUNTIME:-0}" != 1 ]]; then
        rm -rf "$runtime"
    fi
}
trap cleanup EXIT INT TERM

need() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "missing required command: $1" >&2
        exit 2
    }
}

for command in dpkg dpkg-deb dpkg-query strace python3 sha256sum find diff git date; do
    need "$command"
done

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime" "$result_dir"

python3 "$provenance_tool" capture \
    --repo-root "$repo_root" \
    --runtime "$runtime" \
    --result-dir "$result_dir" \
    --json-output "$result_dir/provenance.json" \
    --env-output "$result_dir/provenance.env"

capture_environment() {
    {
        printf 'date_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        cat "$result_dir/provenance.env"
        printf 'uid=%s\n' "$(id -u)"
        printf 'gid=%s\n' "$(id -g)"
        printf 'user=%s\n' "$(id -un)"
        printf 'kernel=%s\n' "$(uname -a)"
        if [[ -r /etc/os-release ]]; then
            cat /etc/os-release
        fi
        dpkg --version | head -n 1
        dpkg-deb --version | head -n 1
        strace --version | head -n 1
    } > "$result_dir/environment.txt"
}

capture_host_dpkg_config() {
    : > "$result_dir/host-dpkg-config.txt"
    for path in /etc/dpkg/dpkg.cfg /etc/dpkg/dpkg.cfg.d/*; do
        [[ -f "$path" ]] || continue
        printf '===== %s =====\n' "$path" >> "$result_dir/host-dpkg-config.txt"
        cat "$path" >> "$result_dir/host-dpkg-config.txt"
        printf '\n' >> "$result_dir/host-dpkg-config.txt"
    done
}

host_fingerprint() {
    local output=$1
    shift
    : > "$output"
    for path in "$@"; do
        if [[ -L "$path" ]]; then
            printf 'symlink\t%s\t%s\n' "$path" "$(readlink "$path")" >> "$output"
        elif [[ -f "$path" ]]; then
            printf 'file\t%s\t%s\n' "$path" "$(sha256sum "$path" | awk '{print $1}')" >> "$output"
        elif [[ -d "$path" ]]; then
            printf 'directory\t%s\n' "$path" >> "$output"
        else
            printf 'absent\t%s\n' "$path" >> "$output"
        fi
    done
}

trace_phase() {
    local name=$1
    local expected=$2
    shift 2
    local raw_command="$result_dir/$name.command.raw"
    local normalized_command="$result_dir/$name.command"
    local stdout="$result_dir/$name.stdout"
    local stderr="$result_dir/$name.stderr"
    local prefix="$result_dir/$name.trace"
    local started_utc started_ms finished_utc finished_ms status

    printf '%q ' "$@" > "$raw_command"
    printf '\n' >> "$raw_command"
    python3 "$provenance_tool" normalize \
        --repo-root "$repo_root" \
        --runtime "$runtime" \
        --result-dir "$result_dir" \
        --input "$raw_command" \
        --output "$normalized_command"

    started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    started_ms="$(date +%s%3N)"
    set +e
    strace -ff -qq -yy -s 4096 \
        -e trace=%file,%process,%network \
        -o "$prefix" \
        -- "$@" > "$stdout" 2> "$stderr"
    status=$?
    set -e
    finished_ms="$(date +%s%3N)"
    finished_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '%s\n' "$status" > "$result_dir/$name.status"

    python3 - "$result_dir/$name.phase.json" "$name" "$expected" \
        "$status" "$started_utc" "$finished_utc" "$started_ms" "$finished_ms" <<'PY'
import json
import pathlib
import sys

path, name, expected, status, started, finished, started_ms, finished_ms = sys.argv[1:]
status_i = int(status)
start_i = int(started_ms)
finish_i = int(finished_ms)
record = {
    "schema_version": 1,
    "name": name,
    "expected_exit": expected,
    "exit_status": status_i,
    "started_utc": started,
    "finished_utc": finished,
    "duration_ms": finish_i - start_i,
    "artifacts": {
        "command": f"{name}.command",
        "raw_command": f"{name}.command.raw",
        "stdout": f"{name}.stdout",
        "stderr": f"{name}.stderr",
        "status": f"{name}.status",
        "trace_glob": f"{name}.trace*",
    },
}
pathlib.Path(path).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
PY

    case "$expected" in
        nonzero)
            if [[ $status -eq 0 ]]; then
                echo "$name unexpectedly succeeded" >&2
                cat "$stderr" >&2
                exit 1
            fi
            ;;
        *)
            if [[ $status -ne $expected ]]; then
                echo "$name exited $status, expected $expected" >&2
                cat "$stderr" >&2
                exit 1
            fi
            ;;
    esac
}

dpkg_phase() {
    local name=$1
    local expected=$2
    shift 2
    trace_phase "$name" "$expected" \
        env -i \
        PATH=/usr/sbin:/usr/bin:/sbin:/bin \
        HOME="$target/nonexistent-home" \
        TMPDIR="$target/tmp" \
        XDG_RUNTIME_DIR="$target/run" \
        LC_ALL=C \
        dpkg \
        --force-not-root \
        --force-script-chrootless \
        --force-confold \
        --root="$target" \
        --log="$target/var/log/dpkg.log" \
        "$@"
}

snapshot_state() {
    local label=$1
    python3 - "$target" "$result_dir" "$label" <<'PY'
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import sys

target = pathlib.Path(sys.argv[1])
result_dir = pathlib.Path(sys.argv[2])
label = sys.argv[3]
admindir = target / "var/lib/dpkg"
query = subprocess.run(
    [
        "dpkg-query",
        f"--admindir={admindir}",
        "-W",
        "-f=${db:Status-Status}\t${Status}\t${Version}\n",
        "lf-lifecycle",
    ],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
if query.returncode == 0:
    status_word, full_status, version = query.stdout.rstrip("\n").split("\t", 2)
else:
    status_word, full_status, version = "absent", None, None

payload_path = target / "usr/lib/lf-lifecycle/version"
payload = payload_path.read_text(encoding="utf-8").rstrip("\n") if payload_path.is_file() else None

conffiles = {}
for path in sorted((target / "etc").glob("lf-lifecycle.conf*")):
    if not path.is_file():
        continue
    data = path.read_bytes()
    conffiles[str(path.relative_to(target))] = {
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "content": data.decode("utf-8", errors="replace"),
    }

script_path = target / "var/lib/lf-lifecycle/script.log"
script_lines = script_path.read_text(encoding="utf-8").splitlines() if script_path.is_file() else []

tree_path = result_dir / f"{label}-tree.tsv"
rows = []
for path in sorted(target.rglob("*"), key=lambda item: str(item.relative_to(target))):
    relative = str(path.relative_to(target))
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        kind = "l"
        link = os.readlink(path)
    elif stat.S_ISDIR(info.st_mode):
        kind = "d"
        link = ""
    elif stat.S_ISREG(info.st_mode):
        kind = "f"
        link = ""
    else:
        kind = "o"
        link = ""
    rows.append(
        f"{relative}\t{kind}\t{stat.S_IMODE(info.st_mode):o}\t{info.st_size}\t{link}"
    )
tree_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")

record = {
    "schema_version": 1,
    "label": label,
    "package": {
        "status_word": status_word,
        "full_status": full_status,
        "version": version,
        "query_stderr": query.stderr.strip() or None,
    },
    "payload_version": payload,
    "conffiles": conffiles,
    "script_log": script_lines,
    "artifacts": {"tree": tree_path.name},
}
(result_dir / f"{label}.snapshot.json").write_text(
    json.dumps(record, indent=2) + "\n", encoding="utf-8"
)
PY
}

assert_snapshot() {
    local label=$1
    local expected_status=$2
    local expected_payload=$3
    local expected_conf=$4
    python3 - "$result_dir/$label.snapshot.json" "$expected_status" "$expected_payload" "$expected_conf" <<'PY'
import json
import pathlib
import sys

path, expected_status, expected_payload, expected_conf = sys.argv[1:]
record = json.loads(pathlib.Path(path).read_text())
actual_status = record["package"]["status_word"]
allowed_statuses = set(expected_status.split(","))
assert actual_status in allowed_statuses, (actual_status, allowed_statuses)
if expected_payload == "<absent>":
    assert record["payload_version"] is None, record["payload_version"]
else:
    assert record["payload_version"] == expected_payload, record["payload_version"]
main_conf = record["conffiles"].get("etc/lf-lifecycle.conf")
if expected_conf == "<absent>":
    assert main_conf is None, main_conf
else:
    assert main_conf is not None, record["conffiles"]
    assert main_conf["content"] == expected_conf + "\n", main_conf
PY
}

init_target() {
    rm -rf "$target"
    mkdir -p \
        "$target/etc" \
        "$target/tmp" \
        "$target/run" \
        "$target/var/lib/dpkg/info" \
        "$target/var/lib/dpkg/parts" \
        "$target/var/lib/dpkg/triggers" \
        "$target/var/lib/dpkg/updates" \
        "$target/var/log"
    chmod 01777 "$target/tmp"
    : > "$target/var/lib/dpkg/status"
    : > "$target/var/lib/dpkg/available"
}

capture_environment
capture_host_dpkg_config
python3 "$investigation_dir/build-fixtures.py" --output "$package_dir" \
    > "$result_dir/fixture-build.stdout"
cp -a "$package_dir" "$result_dir/fixtures"
init_target

host_paths=(
    /etc/lf-lifecycle.conf
    /usr/lib/lf-lifecycle/version
    /var/lib/dpkg/status
    /var/log/dpkg.log
    /var/log/alternatives.log
    /run/needrestart/unpacked
)
host_fingerprint "$result_dir/host-before.tsv" "${host_paths[@]}"

v1="$package_dir/lf-lifecycle_1.0_all.deb"
v2="$package_dir/lf-lifecycle_2.0_all.deb"
v3_fail="$package_dir/lf-lifecycle_3.0_all.deb"
v3_recover="$package_dir/lf-lifecycle_3.1_all.deb"

# Initial install and deliberate local conffile edit.
dpkg_phase install-v1 0 --install "$v1"
snapshot_state install-v1
assert_snapshot install-v1 installed 1.0 default=one
printf 'user=preserved\n' > "$target/etc/lf-lifecycle.conf"
snapshot_state local-edit
assert_snapshot local-edit installed 1.0 user=preserved

# Successful version 2 upgrade with unpack and configure separated.
dpkg_phase unpack-v2 0 --unpack "$v2"
snapshot_state unpack-v2
assert_snapshot unpack-v2 unpacked 2.0 user=preserved
dpkg_phase configure-v2 0 --configure lf-lifecycle
snapshot_state configure-v2
assert_snapshot configure-v2 installed 2.0 user=preserved

# Deliberately failing version 3 configuration.
dpkg_phase unpack-v3-fail 0 --unpack "$v3_fail"
snapshot_state unpack-v3-fail
assert_snapshot unpack-v3-fail unpacked 3.0 user=preserved
dpkg_phase configure-v3-fail nonzero --configure lf-lifecycle
snapshot_state configure-v3-fail
assert_snapshot configure-v3-fail half-configured 3.0 user=preserved

# Later fixed version must recover to installed state.
dpkg_phase unpack-v3-recover 0 --unpack "$v3_recover"
snapshot_state unpack-v3-recover
assert_snapshot unpack-v3-recover unpacked 3.1 user=preserved
dpkg_phase configure-v3-recover 0 --configure lf-lifecycle
snapshot_state configure-v3-recover
assert_snapshot configure-v3-recover installed 3.1 user=preserved

# Purge tracked package data. Maintainer-script-created target logs are captured separately.
dpkg_phase purge 0 --purge lf-lifecycle
snapshot_state purge
assert_snapshot purge absent,not-installed '<absent>' '<absent>'

python3 - "$result_dir/purge.snapshot.json" "$target" <<'PY'
import json
import pathlib
import sys

snapshot = json.loads(pathlib.Path(sys.argv[1]).read_text())
target = sys.argv[2]
lines = snapshot["script_log"]
assert lines, "maintainer-script log was unexpectedly empty"
for line in lines:
    assert f"dpkg_root={target}" in line, line
    assert f"cwd={target}" in line, line
assert any("phase=postinst script_version=3.0" in line for line in lines)
assert any("phase=postinst script_version=3.1" in line for line in lines)
PY

for phase_record in "$result_dir"/*.phase.json; do
    phase="$(basename "$phase_record" .phase.json)"
    set +e
    python3 "$classifier" \
        --target "$target" \
        --runtime "$runtime" \
        --cwd "$repo_root" \
        --output "$result_dir/$phase-access.tsv" \
        "$result_dir/$phase.trace"* \
        > "$result_dir/$phase-classifier.stdout"
    classifier_status=$?
    set -e
    if [[ $classifier_status -ne 0 ]]; then
        echo "outside-target classifier rejected $phase with status $classifier_status" >&2
        cat "$result_dir/$phase-classifier.stdout" >&2
        exit "$classifier_status"
    fi
done

host_fingerprint "$result_dir/host-after.tsv" "${host_paths[@]}"
diff -u "$result_dir/host-before.tsv" "$result_dir/host-after.tsv" \
    > "$result_dir/host-fingerprint.diff" || :

python3 "$summary_tool" --results "$result_dir" --target "$target" \
    | tee "$result_dir/summary.stdout"

echo "LF-02 upgrade failure and recovery probe completed"
