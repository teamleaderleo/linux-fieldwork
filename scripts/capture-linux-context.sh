#!/usr/bin/env bash
# Capture host facts that commonly decide rootless container and bootstrap behavior.
set -u

output=${1:-"linux-context-$(date -u +%Y%m%dT%H%M%SZ).md"}
mkdir -p "$(dirname "$output")"

exec 3>"$output"

section() {
  printf '\n## %s\n\n' "$1" >&3
}

run() {
  local title=$1
  shift
  printf '### %s\n\n```text\n' "$title" >&3
  printf '$' >&3
  printf ' %q' "$@" >&3
  printf '\n' >&3
  "$@" >&3 2>&1
  local status=$?
  printf '\n[exit %d]\n```\n\n' "$status" >&3
  return 0
}

printf '# Linux execution context\n\n' >&3
printf -- '- Captured at: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >&3
printf -- '- Host: `%s`\n' "$(hostname 2>/dev/null || printf unknown)" >&3

section "Identity and kernel"
run "uname" uname -a
run "identity" id
run "OS release" sh -c 'cat /etc/os-release 2>/dev/null || true'
run "process security fields" sh -c \
  "grep -E '^(NSpid|Cap(Inh|Prm|Eff|Bnd|Amb)|NoNewPrivs|Seccomp):' /proc/self/status 2>/dev/null || true"

section "Namespaces"
run "namespace handles" sh -c \
  'for item in /proc/self/ns/*; do printf "%s -> %s\n" "$item" "$(readlink "$item")"; done'
run "user namespace probe" sh -c \
  'command -v unshare >/dev/null && unshare --user --map-root-user sh -c "printf uid=; id -u; printf gid=; id -g"'
run "mount namespace probe" sh -c \
  'command -v unshare >/dev/null && d=$(mktemp -d) && trap "rmdir \"$d\"" EXIT && unshare --user --map-root-user --mount sh -c "mount -t tmpfs tmpfs \"$d\" && findmnt \"$d\" && umount \"$d\""'

section "UID and GID delegation"
run "subuid" sh -c 'cat /etc/subuid 2>/dev/null || true'
run "subgid" sh -c 'cat /etc/subgid 2>/dev/null || true'
run "namespace sysctls" sh -c \
  'for key in kernel.unprivileged_userns_clone user.max_user_namespaces; do printf "%s=" "$key"; sysctl -n "$key" 2>/dev/null || printf unavailable; done'

section "Mounts and cgroups"
run "cgroup membership" sh -c 'cat /proc/self/cgroup 2>/dev/null || true'
run "cgroup filesystems" sh -c 'findmnt -t cgroup,cgroup2 2>/dev/null || true'
run "selected mounts" sh -c \
  'findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS / /tmp /var/tmp 2>/dev/null || true'
run "full mountinfo" sh -c 'cat /proc/self/mountinfo 2>/dev/null || true'

section "Container and bootstrap tools"
for tool in \
  docker podman buildah runc crun containerd nerdctl \
  mmdebstrap debootstrap qemu-system-x86_64 qemu-aarch64; do
  if command -v "$tool" >/dev/null 2>&1; then
    run "$tool version" sh -c '"$1" --version 2>&1 | head -n 20' sh "$tool"
  fi
done

section "Resource limits"
run "ulimit" sh -c 'ulimit -a'

printf 'Wrote %s\n' "$output"
