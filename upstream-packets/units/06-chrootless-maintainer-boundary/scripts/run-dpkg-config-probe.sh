#!/bin/bash
set -euo pipefail

probe_name=lf-dpkg-config-probe
work=$(mktemp -d "/tmp/${probe_name}.XXXXXX")
system_cfg=/etc/dpkg/dpkg.cfg.d/zz-lf-fieldwork-dpkg-config-probe
system_cfg_created=0

cleanup() {
  rc=$?
  if [ "$system_cfg_created" -eq 1 ]; then
    rm -f -- "$system_cfg"
  fi
  rm -rf -- "$work"
  exit "$rc"
}
trap cleanup EXIT HUP INT TERM

if [ "$(id -u)" -ne 0 ]; then
  echo "error=requires-root-for-disposable-system-config-phase" >&2
  exit 1
fi
if [ -e "$system_cfg" ]; then
  echo "error=refusing-preexisting-system-config path=$system_cfg" >&2
  exit 1
fi

printf 'probe=%s\n' "$probe_name"
printf 'dpkg_version=%s\n' "$(dpkg-query -W -f='${Version}' dpkg 2>/dev/null || dpkg --version | sed -n '1s/.*version //p')"
printf 'uid=%s\n' "$(id -u)"
printf 'system_config_files='
find /etc/dpkg/dpkg.cfg /etc/dpkg/dpkg.cfg.d -maxdepth 1 -type f -printf '%p,' 2>/dev/null | sort
printf '\n'

pkgroot="$work/pkg"
mkdir -p "$pkgroot/DEBIAN" "$pkgroot/opt/lfprobe" "$pkgroot/usr/share/doc/lfprobe"
cat >"$pkgroot/DEBIAN/control" <<'EOF'
Package: lf-dpkg-config-probe
Version: 1.0
Architecture: all
Maintainer: Linux Fieldwork <nobody@example.invalid>
Description: disposable dpkg configuration isolation probe
EOF
printf 'keep\n' >"$pkgroot/opt/lfprobe/keep"
printf 'doc\n' >"$pkgroot/usr/share/doc/lfprobe/README"
dpkg-deb --build "$pkgroot" "$work/probe.deb" >/dev/null

cat >"$work/logger.sh" <<EOF
#!/bin/sh
printf logger >'$work/logger.marker'
cat >/dev/null
EOF
cat >"$work/pre.sh" <<EOF
#!/bin/sh
printf pre >'$work/pre.marker'
EOF
cat >"$work/post.sh" <<EOF
#!/bin/sh
printf post >'$work/post.marker'
EOF
chmod 0755 "$work/logger.sh" "$work/pre.sh" "$work/post.sh"

reset_case_state() {
  rm -f -- "$work/logger.marker" "$work/pre.marker" "$work/post.marker" \
    "$work/user-dpkg.log" "$work/system-dpkg.log"
}

make_root() {
  root=$1
  mkdir -p "$root/var/lib/dpkg" "$root/var/log" "$root/tmp"
  : >"$root/var/lib/dpkg/status"
  chmod 01777 "$root/tmp"
}

print_case() {
  phase=$1
  name=$2
  rc=$3
  root=$4
  printf 'phase=%s case=%s rc=%s markers=' "$phase" "$name" "$rc"
  for marker in logger pre post; do
    if [ -e "$work/$marker.marker" ]; then
      printf '%s,' "$marker"
    fi
  done
  printf ' files='
  [ -e "$root/opt/lfprobe/keep" ] && printf 'opt,'
  [ -e "$root/usr/share/doc/lfprobe/README" ] && printf 'doc,'
  printf ' user_log=%s system_log=%s target_log=%s\n' \
    "$([ -e "$work/user-dpkg.log" ] && echo yes || echo no)" \
    "$([ -e "$work/system-dpkg.log" ] && echo yes || echo no)" \
    "$([ -e "$root/var/log/dpkg.log" ] && echo yes || echo no)"
}

run_case() {
  phase=$1
  name=$2
  env_mode=$3
  shift 3
  root="$work/root-$phase-$name"
  make_root "$root"
  reset_case_state
  set +e
  if [ "$env_mode" = inherited ]; then
    HOME="$work/home" TMPDIR="$root/tmp" PATH=/usr/sbin:/usr/bin:/sbin:/bin \
      /usr/bin/dpkg --force-not-root --force-script-chrootless \
      --root="$root" "$@" --install "$work/probe.deb" \
      >"$work/$phase-$name.out" 2>"$work/$phase-$name.err"
  else
    /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin TMPDIR="$root/tmp" \
      /usr/bin/dpkg --force-not-root --force-script-chrootless \
      --root="$root" "$@" --install "$work/probe.deb" \
      >"$work/$phase-$name.out" 2>"$work/$phase-$name.err"
  fi
  rc=$?
  set -e
  print_case "$phase" "$name" "$rc" "$root"
  if [ "$rc" -ne 0 ]; then
    printf 'stderr_begin phase=%s case=%s\n' "$phase" "$name"
    sed -n '1,12p' "$work/$phase-$name.err"
    printf 'stderr_end phase=%s case=%s\n' "$phase" "$name"
  fi
}

mkdir -p "$work/home"
cat >"$work/home/.dpkg.cfg" <<EOF
status-logger $work/logger.sh
pre-invoke $work/pre.sh
post-invoke $work/post.sh
path-exclude /opt/lfprobe/*
log $work/user-dpkg.log
EOF

run_case user inherited inherited
run_case user appended-controls inherited \
  --status-logger=true --pre-invoke=true --post-invoke=true \
  --path-include='*' --log="$work/root-user-appended-controls/var/log/dpkg.log"
run_case user scrubbed scrubbed \
  --log="$work/root-user-scrubbed/var/log/dpkg.log"
run_case user scrubbed-plus-include scrubbed \
  --path-include='*' --log="$work/root-user-scrubbed-plus-include/var/log/dpkg.log"

cat >"$system_cfg" <<EOF
status-logger $work/logger.sh
pre-invoke $work/pre.sh
post-invoke $work/post.sh
path-exclude /opt/lfprobe/*
log $work/system-dpkg.log
EOF
system_cfg_created=1

run_case system scrubbed-baseline scrubbed
run_case system appended-command-controls scrubbed \
  --status-logger=true --pre-invoke=true --post-invoke=true \
  --path-include='*' \
  --log="$work/root-system-appended-command-controls/var/log/dpkg.log"
run_case system neutralize-data-only scrubbed \
  --path-include='*' \
  --log="$work/root-system-neutralize-data-only/var/log/dpkg.log"

rm -f -- "$system_cfg"
system_cfg_created=0
if [ -e "$system_cfg" ]; then
  echo "cleanup=failed-system-config-present" >&2
  exit 1
fi
printf 'cleanup=system-config-absent\n'
