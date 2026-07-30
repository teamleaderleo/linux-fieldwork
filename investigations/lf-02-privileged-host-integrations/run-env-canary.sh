#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
fixture_src="$repo_root/programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/scouts/LF-SCOUT-ROOT-01/artifacts/fixture"
result_dir="$repo_root/investigations/lf-02-privileged-host-integrations/env-results"
runtime="${RUNNER_TEMP:-/tmp}/lf-02-environment-inheritance"
fixture_work="$runtime/fixture"
package="$runtime/lf-fieldwork-env-probe_1.0_all.deb"
agent_sock="$runtime/fake-agent.sock"
agent_received="$result_dir/fake-agent-received.txt"
server_pid=

cleanup() {
    set +e
    if [[ -n "${server_pid:-}" ]]; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
    fi
    rm -rf "$runtime"
}
trap cleanup EXIT INT TERM

for command in dpkg-deb python3 perl; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "missing required command: $command" >&2
        exit 2
    }
done

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime" "$result_dir" "$runtime/home" "$runtime/xdg" "$runtime/sanitized-home"
cp -a "$fixture_src" "$fixture_work"

cat >> "$fixture_work/DEBIAN/postinst" <<'SCRIPT'
{
    printf 'env_count=%s\n' "$(env | wc -l)"
    for name in \
        LF_SECRET_CANARY \
        AWS_SECRET_ACCESS_KEY \
        GITHUB_TOKEN \
        SSH_AUTH_SOCK \
        DBUS_SESSION_BUS_ADDRESS \
        HOME \
        XDG_RUNTIME_DIR; do
        value="$(printenv "$name" 2>/dev/null || printf '<unset>')"
        printf '%s=%s\n' "$name" "$value"
    done
    if [ -n "${SSH_AUTH_SOCK-}" ] && [ -S "$SSH_AUTH_SOCK" ]; then
        if python3 - "$SSH_AUTH_SOCK" <<'PY'
import socket
import sys
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(5)
sock.connect(sys.argv[1])
sock.sendall(b"lf-fieldwork-package-script\n")
sock.close()
PY
        then
            printf 'agent_socket_connect=success\n'
        else
            printf 'agent_socket_connect=failure\n'
        fi
    else
        printf 'agent_socket_connect=unavailable\n'
    fi
} >> "$DPKG_ROOT/var/lib/lf-fieldwork-probe/env-canary.log"
SCRIPT

chmod 0755 \
    "$fixture_work/DEBIAN/preinst" \
    "$fixture_work/DEBIAN/postinst" \
    "$fixture_work/DEBIAN/prerm" \
    "$fixture_work/DEBIAN/postrm" \
    "$fixture_work/usr/lib/lf-fieldwork-probe/tool"

dpkg-deb --build --root-owner-group "$fixture_work" "$package" \
    > "$result_dir/fixture-build.stdout" \
    2> "$result_dir/fixture-build.stderr"

python3 - "$agent_sock" "$agent_received" <<'PY' &
import pathlib
import socket
import sys
sock_path = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(str(sock_path))
server.listen(1)
server.settimeout(120)
try:
    conn, _ = server.accept()
    with conn:
        data = conn.recv(4096)
    out_path.write_bytes(data)
finally:
    server.close()
PY
server_pid=$!

for _ in $(seq 1 100); do
    [[ -S "$agent_sock" ]] && break
    sleep 0.05
done
[[ -S "$agent_sock" ]]

run_case() {
    local label=$1
    local environment=$2
    local target="$runtime/$label-root"
    local package_dir hook
    package_dir="$(dirname "$package")"
    printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' "$package_dir" "$package" "$package"
    rm -rf "$target"

    local -a command=(
        "$source_root/mmdebstrap"
        --mode=chrootless
        --variant=custom
        --format=directory
        --skip=update
        --include="$package"
        --setup-hook="$hook"
        ''
        "$target"
    )
    printf '%q ' "${command[@]}" > "$result_dir/$label.command"
    printf '\n' >> "$result_dir/$label.command"

    if [[ $environment == inherited ]]; then
        env \
            LF_SECRET_CANARY='lf-secret-canary-7f46' \
            AWS_SECRET_ACCESS_KEY='fake-aws-secret-3a91' \
            GITHUB_TOKEN='fake-github-token-91c2' \
            SSH_AUTH_SOCK="$agent_sock" \
            DBUS_SESSION_BUS_ADDRESS="unix:path=$runtime/fake-session-bus" \
            HOME="$runtime/home" \
            XDG_RUNTIME_DIR="$runtime/xdg" \
            TMPDIR="$runtime" \
            LC_ALL=C \
            "${command[@]}" \
            > "$result_dir/$label.stdout" \
            2> "$result_dir/$label.stderr"
    else
        env -i \
            PATH=/usr/sbin:/usr/bin:/sbin:/bin \
            HOME="$runtime/sanitized-home" \
            TMPDIR="$runtime" \
            LC_ALL=C \
            "${command[@]}" \
            > "$result_dir/$label.stdout" \
            2> "$result_dir/$label.stderr"
    fi

    cp "$target/var/lib/lf-fieldwork-probe/env-canary.log" "$result_dir/$label-env-canary.log"
    sed "s#${runtime}#RUNTIME#g" "$result_dir/$label-env-canary.log" \
        > "$result_dir/$label-env-canary.normalized"
    test -f "$target/usr/lib/lf-fieldwork-probe/tool"
    dpkg-query --admindir="$target/var/lib/dpkg" -W -f='${db:Status-Status}\n' lf-fieldwork-probe \
        | grep -Fx installed >/dev/null
}

chmod 0755 "$source_root/mmdebstrap"
run_case inherited inherited
wait "$server_pid"
server_pid=
run_case sanitized sanitized

inherited="$result_dir/inherited-env-canary.log"
sanitized="$result_dir/sanitized-env-canary.log"

grep -Fx 'LF_SECRET_CANARY=lf-secret-canary-7f46' "$inherited"
grep -Fx 'AWS_SECRET_ACCESS_KEY=fake-aws-secret-3a91' "$inherited"
grep -Fx 'GITHUB_TOKEN=fake-github-token-91c2' "$inherited"
grep -Fx "SSH_AUTH_SOCK=$agent_sock" "$inherited"
grep -Fx "DBUS_SESSION_BUS_ADDRESS=unix:path=$runtime/fake-session-bus" "$inherited"
grep -Fx 'agent_socket_connect=success' "$inherited"
grep -Fx 'lf-fieldwork-package-script' "$agent_received"

for name in LF_SECRET_CANARY AWS_SECRET_ACCESS_KEY GITHUB_TOKEN SSH_AUTH_SOCK DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR; do
    grep -Fx "$name=<unset>" "$sanitized"
done
grep -Fx 'agent_socket_connect=unavailable' "$sanitized"

python3 - "$result_dir" <<'PY'
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])

def parse(path):
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        data[key] = value
    return data

inherited = parse(root / "inherited-env-canary.log")
sanitized = parse(root / "sanitized-env-canary.log")
agent = (root / "fake-agent-received.txt").read_text(encoding="utf-8").strip()
summary = {
    "inherited_env_count": int(inherited["env_count"]),
    "sanitized_env_count": int(sanitized["env_count"]),
    "fake_credentials_inherited": all(
        inherited[key] != "<unset>"
        for key in ("LF_SECRET_CANARY", "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN")
    ),
    "host_socket_path_inherited": inherited["SSH_AUTH_SOCK"].endswith("/fake-agent.sock"),
    "package_script_connected_to_host_socket": inherited["agent_socket_connect"] == "success" and agent == "lf-fieldwork-package-script",
    "sanitized_control_removed_canaries": all(
        sanitized[key] == "<unset>"
        for key in (
            "LF_SECRET_CANARY",
            "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN",
            "SSH_AUTH_SOCK",
            "DBUS_SESSION_BUS_ADDRESS",
            "XDG_RUNTIME_DIR",
        )
    ),
    "sanitized_control_skipped_host_socket": sanitized["agent_socket_connect"] == "unavailable",
}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
raise SystemExit(0 if all(value for key, value in summary.items() if not key.endswith("_env_count")) else 1)
PY

echo "LF-02 environment and agent-socket canary passed"
