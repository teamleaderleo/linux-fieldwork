#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
fixture_src="$repo_root/programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/scouts/LF-SCOUT-ROOT-01/artifacts/fixture"
result_dir="$repo_root/investigations/lf-02-privileged-host-integrations/results"
summary_script="$repo_root/investigations/lf-02-privileged-host-integrations/summarize_results.py"
runtime="${RUNNER_TEMP:-/tmp}/lf-02-privileged-host-integrations"
fixture_work="$runtime/fixture"
package="$runtime/lf-fieldwork-probe_1.0_all.deb"
needrestart_cfg=/etc/dpkg/dpkg.cfg.d/needrestart
needrestart_marker=/run/needrestart/unpacked
cfg_backup="$runtime/needrestart.dpkg.cfg"
marker_backup="$runtime/needrestart.unpacked.original"
marker_meta="$runtime/needrestart.unpacked.meta"
config_was_disabled=0
marker_was_present=0

cleanup() {
    set +e
    if [[ $config_was_disabled -eq 1 && -e "$cfg_backup" ]]; then
        mv "$cfg_backup" "$needrestart_cfg"
    fi
    if [[ $marker_was_present -eq 1 ]]; then
        mkdir -p "$(dirname "$needrestart_marker")"
        cp -a "$marker_backup" "$needrestart_marker"
        if [[ -s "$marker_meta" ]]; then
            read -r marker_mode marker_uid marker_gid < "$marker_meta"
            chmod "$marker_mode" "$needrestart_marker"
            chown "$marker_uid:$marker_gid" "$needrestart_marker"
        fi
    else
        rm -f "$needrestart_marker"
    fi
    rm -rf "$runtime"
}
trap cleanup EXIT INT TERM

if [[ $(id -u) -ne 0 ]]; then
    echo "run this probe as root (the workflow uses sudo)" >&2
    exit 2
fi

for command in dpkg-deb strace python3 sha256sum find diff perl; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "missing required command: $command" >&2
        exit 2
    }
done

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime" "$result_dir"

if [[ -e "$needrestart_marker" ]]; then
    marker_was_present=1
    cp -a "$needrestart_marker" "$marker_backup"
    stat -c '%a %u %g' "$needrestart_marker" > "$marker_meta"
fi

restore_marker() {
    if [[ $marker_was_present -eq 1 ]]; then
        mkdir -p "$(dirname "$needrestart_marker")"
        cp -a "$marker_backup" "$needrestart_marker"
        read -r marker_mode marker_uid marker_gid < "$marker_meta"
        chmod "$marker_mode" "$needrestart_marker"
        chown "$marker_uid:$marker_gid" "$needrestart_marker"
    else
        rm -f "$needrestart_marker"
    fi
}

snapshot_marker() {
    local output=$1
    if [[ -e "$needrestart_marker" ]]; then
        {
            stat -c 'present=1 mode=%a uid=%u gid=%g size=%s mtime=%Y inode=%i' "$needrestart_marker"
            sha256sum "$needrestart_marker"
            printf '%s\n' '--- content ---'
            cat "$needrestart_marker"
        } > "$output"
    else
        printf 'present=0\n' > "$output"
    fi
}

capture_environment() {
    {
        printf 'date_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf 'repository_head=%s\n' "$(git rev-parse HEAD)"
        printf 'uid=%s gid=%s user=%s\n' "$(id -u)" "$(id -g)" "$(id -un)"
        printf 'kernel=%s\n' "$(uname -a)"
        cat /etc/os-release
        dpkg --version | head -n 1
        apt-get --version | head -n 1
        strace --version | head -n 1
        printf 'needrestart_cfg_present=%s\n' "$([[ -f "$needrestart_cfg" ]] && echo yes || echo no)"
        if [[ -f "$needrestart_cfg" ]]; then
            printf '%s\n' '--- needrestart dpkg config ---'
            cat "$needrestart_cfg"
        fi
        printf '%s\n' '--- apt inhibitor defaults ---'
        apt-config dump | grep -E '^DPkg::Inhibit-(Shutdown|Sleep)' || true
    } > "$result_dir/environment.txt"
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
    } > "$result_dir/fixture.txt"
}

trace_case() {
    local label=$1
    local disable_inhibit=$2
    local disable_needrestart=$3
    local target="$runtime/$label-root"
    local package_dir hook
    package_dir="$(dirname "$package")"
    printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' "$package_dir" "$package" "$package"

    restore_marker
    snapshot_marker "$result_dir/$label-marker-before.txt"

    if [[ $disable_needrestart -eq 1 ]]; then
        if [[ ! -f "$needrestart_cfg" ]]; then
            echo "needrestart dpkg config missing; cannot run control" >&2
            exit 3
        fi
        mv "$needrestart_cfg" "$cfg_backup"
        config_was_disabled=1
    fi

    rm -rf "$target"
    local -a command=(
        "$source_root/mmdebstrap"
        --mode=chrootless
        --variant=custom
        --format=directory
        --skip=update,check/chrootless
        --include="$package"
        --setup-hook="$hook"
    )
    if [[ $disable_inhibit -eq 1 ]]; then
        command+=(--aptopt='DPkg::Inhibit-Shutdown "false";' --aptopt='DPkg::Inhibit-Sleep "false";')
    fi
    command+=('' "$target")

    printf '%q ' "${command[@]}" > "$result_dir/$label.command"
    printf '\n' >> "$result_dir/$label.command"

    set +e
    strace -ff -qq -s 4096 -yy \
        -e trace=%file,%process,%network \
        -o "$result_dir/$label.trace" \
        -- "${command[@]}" \
        > "$result_dir/$label.stdout" \
        2> "$result_dir/$label.stderr"
    local status=$?
    set -e
    printf '%s\n' "$status" > "$result_dir/$label.status"

    if [[ $disable_needrestart -eq 1 ]]; then
        mv "$cfg_backup" "$needrestart_cfg"
        config_was_disabled=0
    fi

    snapshot_marker "$result_dir/$label-marker-after.txt"

    if [[ $status -ne 0 ]]; then
        echo "$label failed with status $status" >&2
        cat "$result_dir/$label.stderr" >&2
        exit "$status"
    fi

    test -f "$target/usr/lib/lf-fieldwork-probe/tool"
    test "$(readlink "$target/usr/bin/lf-fieldwork-probe")" = /etc/alternatives/lf-fieldwork-probe
    test "$(readlink "$target/etc/alternatives/lf-fieldwork-probe")" = /usr/lib/lf-fieldwork-probe/tool
    grep -F "dpkg_root=$target" "$target/var/lib/lf-fieldwork-probe/script.log" >/dev/null
    dpkg-query --admindir="$target/var/lib/dpkg" -W -f='${db:Status-Status}\n' lf-fieldwork-probe \
        | grep -Fx installed >/dev/null

    sed "s#${target}#ROOT#g" "$target/var/lib/lf-fieldwork-probe/script.log" \
        > "$result_dir/$label-script.normalized"
    sed "s#${target}#ROOT#g" "$target/var/lib/dpkg/alternatives/lf-fieldwork-probe" \
        > "$result_dir/$label-alternative.normalized"
    find "$target" -xdev -printf '%P\t%y\t%m\t%s\t%l\n' | LC_ALL=C sort \
        > "$result_dir/$label-tree.tsv"

    grep -hE 'connect\(.*(/run|/var/run)/dbus/system_bus_socket' "$result_dir/$label.trace"* \
        > "$result_dir/$label-dbus-connect.txt" || true
    grep -hF 'org.freedesktop.login1' "$result_dir/$label.trace"* \
        > "$result_dir/$label-logind-messages.txt" || true
    grep -hE 'SCM_RIGHTS|org\.freedesktop\.DBus\.Error\.AccessDenied|AccessDenied' \
        "$result_dir/$label.trace"* \
        > "$result_dir/$label-dbus-result.txt" || true
    grep -hE 'execve\("/usr/lib/needrestart/dpkg-status"|/run/needrestart/unpacked' "$result_dir/$label.trace"* \
        > "$result_dir/$label-needrestart.txt" || true
}

write_summary() {
    python3 "$summary_script" "$result_dir"
}

capture_environment
prepare_fixture
chmod 0755 "$source_root/mmdebstrap"

trace_case default-root 0 0
trace_case no-inhibit-root 1 0
trace_case isolated-root 1 1

for suffix in script.normalized alternative.normalized; do
    diff -u "$result_dir/default-root-$suffix" "$result_dir/no-inhibit-root-$suffix" \
        > "$result_dir/default-vs-no-inhibit-$suffix.diff"
    diff -u "$result_dir/default-root-$suffix" "$result_dir/isolated-root-$suffix" \
        > "$result_dir/default-vs-isolated-$suffix.diff"
done

write_summary | tee "$result_dir/summary.stdout"
echo "LF-02 privileged host integration matrix passed"
