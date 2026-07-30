#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/results"
runtime="${RUNNER_TEMP:-/tmp}/mmdebstrap-chrootless-env"
fixture="$runtime/fixture"
package="$runtime/lf-chrootless-env-probe_1.0_all.deb"
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

for command in dpkg dpkg-deb dpkg-query perl python3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "missing required command: $command" >&2
    exit 2
  }
done

rm -rf "$runtime" "$result_dir"
mkdir -p "$fixture/DEBIAN" "$fixture/usr/lib/lf-chrootless-env-probe"
mkdir -p "$result_dir" "$runtime/home" "$runtime/xdg" "$runtime/bin"

cat >"$fixture/DEBIAN/control" <<'EOF'
Package: lf-chrootless-env-probe
Version: 1.0
Section: misc
Priority: optional
Architecture: all
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: chrootless environment security probe
 A local-only fixture for testing maintainer-script environment boundaries.
EOF

cat >"$fixture/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu

log="$DPKG_ROOT/var/lib/lf-chrootless-env-probe/environment.log"
mkdir -p "$(dirname "$log")"
{
  printf 'env_count=%s\n' "$(env | wc -l)"
  for name in \
    LF_SECRET_CANARY \
    AWS_SECRET_ACCESS_KEY \
    GITHUB_TOKEN \
    SSH_AUTH_SOCK \
    DBUS_SESSION_BUS_ADDRESS \
    XDG_RUNTIME_DIR \
    HOME \
    PATH \
    DEBIAN_FRONTEND \
    DEBCONF_NONINTERACTIVE_SEEN \
    LC_ALL \
    TZ \
    SOURCE_DATE_EPOCH \
    FAKEROOTKEY \
    LD_PRELOAD \
    DPKG_ROOT \
    DPKG_ADMINDIR; do
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
sock.sendall(b"lf-chrootless-package-script\n")
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
} >"$log"
EOF
chmod 0755 "$fixture/DEBIAN/postinst"
printf 'fixture payload\n' >"$fixture/usr/lib/lf-chrootless-env-probe/payload"
dpkg-deb --build --root-owner-group "$fixture" "$package" \
  >"$result_dir/fixture-build.stdout" \
  2>"$result_dir/fixture-build.stderr"

start_server() {
  local socket_path=$1 output=$2 stop_file=$3
  rm -f "$socket_path" "$output" "$stop_file"
  python3 - "$socket_path" "$output" "$stop_file" <<'PY' &
import pathlib
import socket
import sys

socket_path = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
stop = pathlib.Path(sys.argv[3])
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(str(socket_path))
server.listen(1)
server.settimeout(0.2)
try:
    while not stop.exists():
        try:
            conn, _ = server.accept()
        except TimeoutError:
            continue
        with conn:
            output.write_bytes(conn.recv(4096))
        break
    else:
        output.write_text("no-connection\n", encoding="utf-8")
finally:
    server.close()
PY
  server_pid=$!
  for _ in $(seq 1 100); do
    [[ -S "$socket_path" ]] && return
    sleep 0.05
  done
  echo "fake agent socket was not created" >&2
  exit 1
}

assert_installed() {
  local target=$1
  test -f "$target/usr/lib/lf-chrootless-env-probe/payload"
  dpkg-query --admindir="$target/var/lib/dpkg" \
    -W -f='${db:Status-Status}\n' lf-chrootless-env-probe \
    | grep -Fx installed >/dev/null
}

make_command() {
  local target=$1 skip_environment_check=$2
  local package_dir hook
  package_dir="$(dirname "$package")"
  printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' \
    "$package_dir" "$package" "$package"
  command=(
    "$source_root/mmdebstrap"
    --mode=chrootless
    --variant=custom
    --format=directory
    --skip=update
    --include="$package"
    --setup-hook="$hook"
  )
  if [[ $skip_environment_check == yes ]]; then
    command+=(--skip=check/chrootless/environment)
  fi
  command+=( '' "$target" )
}

chmod 0755 "$source_root/mmdebstrap"

# Negative control: dpkg itself passes the ambient environment to a
# chrootless maintainer script unless its caller wraps the process.
direct_target="$runtime/direct-root"
direct_socket="$runtime/direct-agent.sock"
direct_received="$result_dir/direct-agent-received.txt"
direct_stop="$runtime/direct-agent.stop"
mkdir -p "$direct_target/var/lib/dpkg" "$direct_target/var/log"
: >"$direct_target/var/lib/dpkg/status"
start_server "$direct_socket" "$direct_received" "$direct_stop"
env \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  LF_SECRET_CANARY=direct-secret-canary \
  GITHUB_TOKEN=direct-github-token \
  SSH_AUTH_SOCK="$direct_socket" \
  dpkg \
    --force-not-root \
    --force-script-chrootless \
    --root="$direct_target" \
    --log="$direct_target/var/log/dpkg.log" \
    --install "$package" \
    >"$result_dir/direct.stdout" \
    2>"$result_dir/direct.stderr"
touch "$direct_stop"
wait "$server_pid"
server_pid=
direct_log="$direct_target/var/lib/lf-chrootless-env-probe/environment.log"
grep -Fx 'LF_SECRET_CANARY=direct-secret-canary' "$direct_log"
grep -Fx 'GITHUB_TOKEN=direct-github-token' "$direct_log"
grep -Fx 'agent_socket_connect=success' "$direct_log"
grep -Fx 'lf-chrootless-package-script' "$direct_received"
cp "$direct_log" "$result_dir/direct-environment.log"

# The default launch check must reject a credential-rich shell and report
# variable names only, never values.
unsafe_target="$runtime/unsafe-root"
make_command "$unsafe_target" no
set +e
env \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  HOME="$runtime/home" \
  TMPDIR="$runtime" \
  LC_ALL=C.UTF-8 \
  LF_SECRET_CANARY=unsafe-secret-value \
  GITHUB_TOKEN=unsafe-token-value \
  SSH_AUTH_SOCK="$runtime/not-an-agent.sock" \
  "${command[@]}" \
  >"$result_dir/unsafe.stdout" \
  2>"$result_dir/unsafe.stderr"
unsafe_status=$?
set -e
[[ $unsafe_status -ne 0 ]]
grep -F 'LF_SECRET_CANARY' "$result_dir/unsafe.stderr"
grep -F 'GITHUB_TOKEN' "$result_dir/unsafe.stderr"
grep -F 'SSH_AUTH_SOCK' "$result_dir/unsafe.stderr"
if grep -F -e 'unsafe-secret-value' -e 'unsafe-token-value' \
  "$result_dir/unsafe.stderr"; then
  echo "unsafe environment error disclosed a secret value" >&2
  exit 1
fi
test ! -e "$unsafe_target"

# Apt keeps its proxy/authentication environment, while the dpkg child gets a
# small explicit environment before executing package scripts.
cat >"$runtime/bin/apt-get" <<'EOF'
#!/bin/sh
{
  printf 'http_proxy=%s\n' "${http_proxy-<unset>}"
  printf 'GITHUB_TOKEN=%s\n' "${GITHUB_TOKEN-<unset>}"
} >>"$LF_APT_ENV_LOG"
exec /usr/bin/apt-get "$@"
EOF
chmod 0755 "$runtime/bin/apt-get"

sanitized_target="$runtime/sanitized-root"
san_socket="$runtime/sanitized-agent.sock"
san_received="$result_dir/sanitized-agent-received.txt"
san_stop="$runtime/sanitized-agent.stop"
apt_env_log="$result_dir/apt-environment.log"
start_server "$san_socket" "$san_received" "$san_stop"
make_command "$sanitized_target" yes
env \
  PATH="$runtime/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  HOME="$runtime/home" \
  TMPDIR="$runtime" \
  LC_ALL=C.UTF-8 \
  TZ=UTC \
  SOURCE_DATE_EPOCH=1700000000 \
  http_proxy=http://proxy.invalid:3128 \
  LF_APT_ENV_LOG="$apt_env_log" \
  LF_SECRET_CANARY=sanitized-secret-canary \
  AWS_SECRET_ACCESS_KEY=fake-aws-secret \
  GITHUB_TOKEN=fake-github-token \
  SSH_AUTH_SOCK="$san_socket" \
  DBUS_SESSION_BUS_ADDRESS="unix:path=$runtime/fake-session-bus" \
  XDG_RUNTIME_DIR="$runtime/xdg" \
  "${command[@]}" \
  >"$result_dir/sanitized.stdout" \
  2>"$result_dir/sanitized.stderr"
touch "$san_stop"
wait "$server_pid"
server_pid=
assert_installed "$sanitized_target"
san_log="$sanitized_target/var/lib/lf-chrootless-env-probe/environment.log"
cp "$san_log" "$result_dir/sanitized-environment.log"
for name in \
  LF_SECRET_CANARY \
  AWS_SECRET_ACCESS_KEY \
  GITHUB_TOKEN \
  SSH_AUTH_SOCK \
  DBUS_SESSION_BUS_ADDRESS \
  XDG_RUNTIME_DIR \
  HOME; do
  grep -Fx "$name=<unset>" "$san_log"
done
grep -Fx 'agent_socket_connect=unavailable' "$san_log"
grep -Fx 'no-connection' "$san_received"
grep -Fx 'DEBIAN_FRONTEND=noninteractive' "$san_log"
grep -Fx 'DEBCONF_NONINTERACTIVE_SEEN=true' "$san_log"
grep -Fx 'LC_ALL=C.UTF-8' "$san_log"
grep -Fx 'TZ=UTC' "$san_log"
grep -Fx 'SOURCE_DATE_EPOCH=1700000000' "$san_log"
grep -F 'DPKG_ROOT=' "$san_log" | grep -F "$sanitized_target"
grep -F 'DPKG_ADMINDIR=' "$san_log" | grep -F "$sanitized_target"
grep -Fx 'http_proxy=http://proxy.invalid:3128' "$apt_env_log"
grep -Fx 'GITHUB_TOKEN=fake-github-token' "$apt_env_log"

# A scrubbed launch succeeds without an override, and a second fresh run
# reaches the same installed payload state.
for label in safe safe-rerun; do
  target="$runtime/$label-root"
  make_command "$target" no
  env -i \
    PATH=/usr/sbin:/usr/bin:/sbin:/bin \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    SOURCE_DATE_EPOCH=1700000000 \
    "${command[@]}" \
    >"$result_dir/$label.stdout" \
    2>"$result_dir/$label.stderr"
  assert_installed "$target"
  cp "$target/var/lib/lf-chrootless-env-probe/environment.log" \
    "$result_dir/$label-environment.log"
done
cmp \
  "$runtime/safe-root/usr/lib/lf-chrootless-env-probe/payload" \
  "$runtime/safe-rerun-root/usr/lib/lf-chrootless-env-probe/payload"

# Chrootless mode explicitly supports fakeroot. Its IPC key and preload
# state must survive the dpkg boundary while unrelated variables remain
# absent.
fakeroot_target="$runtime/fakeroot-root"
make_command "$fakeroot_target" no
env -i \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  HOME="$runtime/home" \
  TMPDIR="$runtime" \
  LC_ALL=C.UTF-8 \
  TZ=UTC \
  SOURCE_DATE_EPOCH=1700000000 \
  fakeroot -- "${command[@]}" \
  >"$result_dir/fakeroot.stdout" \
  2>"$result_dir/fakeroot.stderr"
assert_installed "$fakeroot_target"
fakeroot_log="$fakeroot_target/var/lib/lf-chrootless-env-probe/environment.log"
cp "$fakeroot_log" "$result_dir/fakeroot-environment.log"
grep -E '^FAKEROOTKEY=.+$' "$fakeroot_log"
grep -E '^LD_PRELOAD=.*libfakeroot' "$fakeroot_log"
grep -Fx 'LF_SECRET_CANARY=<unset>' "$fakeroot_log"
grep -Fx 'TZ=UTC' "$fakeroot_log"

cat >"$result_dir/summary.txt" <<EOF
negative_control=ambient credentials and agent socket reached direct chrootless dpkg script
unsafe_launch_status=$unsafe_status
unsafe_launch_rejected=yes
unsafe_error_values_redacted=yes
apt_proxy_preserved=yes
apt_token_preserved_to_apt_only=yes
dpkg_environment_sanitized=yes
agent_socket_blocked=yes
required_dpkg_environment_preserved=yes
fakeroot_environment_preserved=yes
safe_launch_succeeded=yes
clean_rerun_succeeded=yes
EOF

cat "$result_dir/summary.txt"
echo "mmdebstrap chrootless environment security regression passed"
