#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
scout_dir="$repo_root/programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/scouts/LF-SCOUT-ROOT-01"
artifact_dir="$scout_dir/artifacts"
fixture_src="$artifact_dir/fixture"
result_dir="$artifact_dir/results"
runtime="${RUNNER_TEMP:-/tmp}/lf-02-dpkg-root-containment"
fixture_work="$runtime/fixture"
package="$runtime/lf-fieldwork-probe_1.0_all.deb"
direct_root="$runtime/direct-root"
mm_root_one="$runtime/mmdebstrap-root-one"
mm_root_two="$runtime/mmdebstrap-root-two"
source_root="$repo_root/upstream/mmdebstrap"
classifier="$artifact_dir/classify-strace.py"

cleanup() {
    if [[ "${KEEP_RUNTIME:-0}" != 1 ]]; then
        rm -rf "$runtime"
    fi
}
trap cleanup EXIT INT TERM

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime" "$result_dir"

need() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "missing required command: $1" >&2
        exit 2
    }
}

for command in dpkg dpkg-deb strace python3 sha256sum find diff perl; do
    need "$command"
done

capture_environment() {
    {
        printf 'date_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf 'repository_head=%s\n' "$(git rev-parse HEAD)"
        printf 'repository_branch=%s\n' "$(git branch --show-current)"
        printf 'upstream_requested_revision=%s\n' "$(python3 -c 'import json; print(json.load(open("upstream/mmdebstrap/.linux-fieldwork-source.json"))["requested_revision"])')"
        printf 'upstream_resolved_commit=%s\n' "$(python3 -c 'import json; print(json.load(open("upstream/mmdebstrap/.linux-fieldwork-source.json"))["resolved_commit"])')"
        printf 'uid=%s\n' "$(id -u)"
        printf 'gid=%s\n' "$(id -g)"
        printf 'user=%s\n' "$(id -un)"
        printf 'kernel=%s\n' "$(uname -a)"
        if [[ -r /etc/os-release ]]; then
            cat /etc/os-release
        fi
        dpkg --version | head -n 1
        apt-get --version | head -n 1
        update-alternatives --version | head -n 1
        strace --version | head -n 1
        perl -v | sed -n '2p'
    } > "$result_dir/environment.txt"
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

trace_command() {
    local name=$1
    shift
    local stdout="$result_dir/$name.stdout"
    local stderr="$result_dir/$name.stderr"
    local prefix="$result_dir/$name.trace"
    printf '%q ' "$@" > "$result_dir/$name.command"
    printf '\n' >> "$result_dir/$name.command"
    set +e
    strace -ff -qq -s 4096 \
        -e trace=%file,%process,%network \
        -o "$prefix" \
        -- "$@" > "$stdout" 2> "$stderr"
    local status=$?
    set -e
    printf '%s\n' "$status" > "$result_dir/$name.status"
    if [[ $status -ne 0 ]]; then
        echo "$name failed with status $status" >&2
        cat "$stderr" >&2
        exit "$status"
    fi
}

prepare_fixture() {
    cp -a "$fixture_src" "$fixture_work"
    chmod 0755 \
        "$fixture_work/DEBIAN/preinst" \
        "$fixture_work/DEBIAN/postinst" \
        "$fixture_work/DEBIAN/prerm" \
        "$fixture_work/DEBIAN/postrm" \
        "$fixture_work/usr/lib/lf-fieldwork-probe/tool"
    dpkg-deb --build --root-owner-group "$fixture_work" "$package" \
        > "$result_dir/fixture-build.stdout" \
        2> "$result_dir/fixture-build.stderr"
    {
        dpkg-deb --info "$package"
        dpkg-deb --contents "$package"
        sha256sum "$package"
        stat -c 'size=%s mode=%a uid=%u gid=%g path=%n' "$package"
    } > "$result_dir/fixture.txt"
}

init_direct_root() {
    rm -rf "$direct_root"
    mkdir -p \
        "$direct_root/etc/alternatives" \
        "$direct_root/tmp" \
        "$direct_root/run" \
        "$direct_root/usr/bin" \
        "$direct_root/var/lib/dpkg/alternatives" \
        "$direct_root/var/lib/dpkg/info" \
        "$direct_root/var/lib/dpkg/parts" \
        "$direct_root/var/lib/dpkg/triggers" \
        "$direct_root/var/lib/dpkg/updates" \
        "$direct_root/var/log"
    chmod 01777 "$direct_root/tmp"
    : > "$direct_root/var/lib/dpkg/status"
    : > "$direct_root/var/lib/dpkg/available"
}

dpkg_target() {
    local phase=$1
    shift
    trace_command "$phase" \
        env -i \
        PATH=/usr/sbin:/usr/bin:/sbin:/bin \
        HOME="$direct_root/nonexistent-home" \
        TMPDIR="$direct_root/tmp" \
        XDG_RUNTIME_DIR="$direct_root/run" \
        LC_ALL=C \
        dpkg \
        --force-not-root \
        --force-script-chrootless \
        --root="$direct_root" \
        --log="$direct_root/var/log/dpkg.log" \
        "$@"
}

assert_target_state() {
    local root=$1
    local label=$2
    test -f "$root/usr/lib/lf-fieldwork-probe/tool"
    test "$(readlink "$root/usr/bin/lf-fieldwork-probe")" = /etc/alternatives/lf-fieldwork-probe
    test "$(readlink "$root/etc/alternatives/lf-fieldwork-probe")" = /usr/lib/lf-fieldwork-probe/tool
    grep -F "dpkg_root=$root" "$root/var/lib/lf-fieldwork-probe/script.log" >/dev/null
    grep -F "cwd=$root" "$root/var/lib/lf-fieldwork-probe/script.log" >/dev/null
    grep -F 'phase=postinst' "$root/var/lib/lf-fieldwork-probe/script.log" >/dev/null
    dpkg-query --admindir="$root/var/lib/dpkg" -W -f='${db:Status-Status}\n' lf-fieldwork-probe \
        | grep -Fx installed >/dev/null
    find "$root" -xdev -printf '%P\t%y\t%m\t%s\t%l\n' | LC_ALL=C sort \
        > "$result_dir/$label-tree.tsv"
    cp "$root/var/lib/lf-fieldwork-probe/script.log" "$result_dir/$label-script.log"
    cp "$root/var/log/dpkg.log" "$result_dir/$label-dpkg.log"
    cp "$root/var/lib/dpkg/alternatives/lf-fieldwork-probe" "$result_dir/$label-alternative-state"
}

classify_group() {
    local name=$1
    local root=$2
    shift 2
    python3 "$classifier" \
        --target "$root" \
        --runtime "$runtime" \
        --cwd "$repo_root" \
        --output "$result_dir/$name-access.tsv" \
        "$@" > "$result_dir/$name-classifier.stdout"
}

run_direct_probe() {
    init_direct_root
    dpkg_target direct-install --install "$package"
    assert_target_state "$direct_root" direct-install

    dpkg_target direct-reinstall --install "$package"
    assert_target_state "$direct_root" direct-reinstall

    dpkg_target direct-purge --purge lf-fieldwork-probe
    test ! -e "$direct_root/usr/lib/lf-fieldwork-probe/tool"
    test ! -e "$direct_root/usr/bin/lf-fieldwork-probe"
    test ! -e "$direct_root/etc/alternatives/lf-fieldwork-probe"
    test ! -e "$direct_root/var/lib/dpkg/alternatives/lf-fieldwork-probe"
    dpkg-query --admindir="$direct_root/var/lib/dpkg" -W -f='${db:Status-Status}\n' lf-fieldwork-probe 2>/dev/null \
        | grep -Fx installed >/dev/null && {
            echo 'package remained installed after purge' >&2
            exit 1
        }
    find "$direct_root" -xdev -printf '%P\t%y\t%m\t%s\t%l\n' | LC_ALL=C sort \
        > "$result_dir/direct-purge-tree.tsv"
    cp "$direct_root/var/lib/lf-fieldwork-probe/script.log" "$result_dir/direct-purge-script.log"

    dpkg_target direct-install-after-purge --install "$package"
    assert_target_state "$direct_root" direct-install-after-purge

    classify_group direct "$direct_root" "$result_dir"/direct-*.trace*
}

mmdebstrap_once() {
    local label=$1
    local root=$2
    local package_dir
    package_dir="$(dirname "$package")"
    rm -rf "$root"
    local hook
    printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' "$package_dir" "$package" "$package"
    trace_command "$label" \
        env \
        LC_ALL=C \
        TMPDIR="$runtime" \
        "$source_root/mmdebstrap" \
        --mode=chrootless \
        --variant=custom \
        --format=directory \
        --skip=update \
        --include="$package" \
        --setup-hook="$hook" \
        '' \
        "$root"
    assert_target_state "$root" "$label"
    classify_group "$label" "$root" "$result_dir/$label.trace"*
}

run_mmdebstrap_probe() {
    chmod 0755 "$source_root/mmdebstrap"
    mmdebstrap_once mmdebstrap-one "$mm_root_one"
    mmdebstrap_once mmdebstrap-two "$mm_root_two"

    sed "s#${mm_root_one}#ROOT#g" "$result_dir/mmdebstrap-one-script.log" \
        > "$result_dir/mmdebstrap-one-script.normalized"
    sed "s#${mm_root_two}#ROOT#g" "$result_dir/mmdebstrap-two-script.log" \
        > "$result_dir/mmdebstrap-two-script.normalized"
    diff -u \
        "$result_dir/mmdebstrap-one-script.normalized" \
        "$result_dir/mmdebstrap-two-script.normalized" \
        > "$result_dir/mmdebstrap-rerun-script.diff"

    sed "s#${mm_root_one}#ROOT#g" "$result_dir/mmdebstrap-one-alternative-state" \
        > "$result_dir/mmdebstrap-one-alternative.normalized"
    sed "s#${mm_root_two}#ROOT#g" "$result_dir/mmdebstrap-two-alternative-state" \
        > "$result_dir/mmdebstrap-two-alternative.normalized"
    diff -u \
        "$result_dir/mmdebstrap-one-alternative.normalized" \
        "$result_dir/mmdebstrap-two-alternative.normalized" \
        > "$result_dir/mmdebstrap-rerun-alternative.diff"
}

write_summary() {
    python3 - "$result_dir" <<'PY'
import glob
import json
import pathlib
import sys

result_dir = pathlib.Path(sys.argv[1])
summary = {
    "fixture": result_dir.joinpath("fixture.txt").read_text(encoding="utf-8").splitlines()[-2:],
    "phases": {},
    "classifications": {},
    "host_fingerprint_unchanged": result_dir.joinpath("host-fingerprint.diff").stat().st_size == 0,
    "mmdebstrap_rerun_script_diff_empty": result_dir.joinpath("mmdebstrap-rerun-script.diff").stat().st_size == 0,
    "mmdebstrap_rerun_alternative_diff_empty": result_dir.joinpath("mmdebstrap-rerun-alternative.diff").stat().st_size == 0,
}
for status_path in sorted(result_dir.glob("*.status")):
    summary["phases"][status_path.stem] = int(status_path.read_text(encoding="utf-8").strip())
for summary_path in sorted(result_dir.glob("*-access.summary.txt")):
    values = {}
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        values[key] = int(value) if value.isdigit() else value
    summary["classifications"][summary_path.name.removesuffix("-access.summary.txt")] = values
result_dir.joinpath("summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
PY
}

capture_environment
prepare_fixture

host_paths=(
    /usr/bin/lf-fieldwork-probe
    /etc/alternatives/lf-fieldwork-probe
    /var/lib/dpkg/alternatives/lf-fieldwork-probe
    /var/lib/dpkg/status
    /var/log/dpkg.log
    /var/log/alternatives.log
)
host_fingerprint "$result_dir/host-before.tsv" "${host_paths[@]}"

run_direct_probe
run_mmdebstrap_probe

host_fingerprint "$result_dir/host-after.tsv" "${host_paths[@]}"
diff -u "$result_dir/host-before.tsv" "$result_dir/host-after.tsv" \
    > "$result_dir/host-fingerprint.diff"

if grep -R -E 'execve(at)?\(.*(systemctl|invoke-rc\.d|service|deb-systemd-invoke|start-stop-daemon)' \
    "$result_dir"/*.trace* > "$result_dir/service-action-exec.txt"; then
    echo 'service-control execution observed' >&2
    exit 1
else
    : > "$result_dir/service-action-exec.txt"
fi

write_summary | tee "$result_dir/summary.stdout"

echo "LF-02 containment probe passed"
