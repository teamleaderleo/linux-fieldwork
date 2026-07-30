#!/usr/bin/env bash
# Capture host facts that commonly decide rootless container and bootstrap behavior.
set -uo pipefail

include_sensitive=0
output=""

usage() {
  cat <<'EOF'
usage: capture-linux-context.sh [--include-sensitive] [OUTPUT]

The default report redacts host and account names. Use --include-sensitive only
for a private artifact that will be reviewed before publication.
EOF
}

while (($#)); do
  case $1 in
    --include-sensitive)
      include_sensitive=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      printf 'unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n $output ]]; then
        printf 'only one output path may be supplied\n' >&2
        exit 2
      fi
      output=$1
      ;;
  esac
  shift
done

if [[ -z $output ]]; then
  output="linux-context-$(date -u +%Y%m%dT%H%M%SZ).md"
fi
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
if ((include_sensitive)); then
  printf -- '- Host: `%s`\n' "$(hostname 2>/dev/null || printf unknown)" >&3
  printf -- '- Sensitive fields included: `yes`\n' >&3
else
  printf -- '- Host: `redacted`\n' >&3
  printf -- '- Sensitive fields included: `no`\n' >&3
fi

section "Identity and kernel"
run "kernel" uname -srvmo
run "numeric identity" sh -c \
  'printf "uid=%s\ngid=%s\ngroups=" "$(id -u)" "$(id -g)"; id -G | tr " " ","; printf "\n"'
run "OS release" sh -c 'cat /etc/os-release 2>/dev/null || true'
run "process security fields" sh -c \
  "grep -E '^(NSpid|Cap(Inh|Prm|Eff|Bnd|Amb)|NoNewPrivs|Seccomp):' /proc/self/status 2>/dev/null || true"

section "Namespaces"
run "namespace handles" sh -c \
  'for item in /proc/self/ns/*; do printf "%s -> %s\n" "$item" "$(readlink "$item")"; done'
run "user namespace probe" sh -c \
  'command -v unshare >/dev/null && unshare --user --map-root-user sh -c "printf uid=; id -u; printf gid=; id -g"'
run "mount namespace probe" sh -c \
  'command -v unshare >/dev/null || exit 127; d=$(mktemp -d); trap '\''rmdir "$d" 2>/dev/null || true'\'' EXIT; unshare --user --map-root-user --mount sh -c '\''mount -t tmpfs tmpfs "$1" && findmnt "$1" && umount "$1"'\'' sh "$d"'

section "UID and GID delegation"
run "current-user subuid ranges" sh -c \
  'u=$(getent passwd "$(id -u)" | cut -d: -f1); awk -F: -v u="$u" '\''$1 == u {print "current-user:" $2 ":" $3; found=1} END {if (!found) print "none"}'\'' /etc/subuid 2>/dev/null || printf "unavailable\n"'
run "current-user subgid ranges" sh -c \
  'u=$(getent passwd "$(id -u)" | cut -d: -f1); awk -F: -v u="$u" '\''$1 == u {print "current-user:" $2 ":" $3; found=1} END {if (!found) print "none"}'\'' /etc/subgid 2>/dev/null || printf "unavailable\n"'
run "namespace sysctls" sh -c \
  'for key in kernel.unprivileged_userns_clone user.max_user_namespaces; do printf "%s=" "$key"; sysctl -n "$key" 2>/dev/null || printf unavailable; printf "\n"; done'

section "Mounts and cgroups"
run "cgroup membership" sh -c 'cat /proc/self/cgroup 2>/dev/null || true'
run "cgroup filesystems" sh -c 'findmnt -t cgroup,cgroup2 2>/dev/null || true'
run "selected mounts" sh -c \
  'findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS / /tmp /var/tmp 2>/dev/null || true'

section "Container and bootstrap tools"
for tool in \
  docker podman buildah runc crun containerd nerdctl \
  mmdebstrap debootstrap autopkgtest qemu-system-x86_64 qemu-aarch64; do
  if command -v "$tool" >/dev/null 2>&1; then
    run "$tool version" sh -c '"$1" --version 2>&1 | head -n 20' sh "$tool"
  fi
done

section "Resource limits"
run "ulimit" sh -c 'ulimit -a'

if ((include_sensitive)); then
  section "Sensitive host details"
  run "hostname" hostname
  run "named identity" id
  run "subuid" sh -c 'cat /etc/subuid 2>/dev/null || true'
  run "subgid" sh -c 'cat /etc/subgid 2>/dev/null || true'
  run "full mountinfo" sh -c 'cat /proc/self/mountinfo 2>/dev/null || true'
fi

printf 'Wrote %s\n' "$output"
