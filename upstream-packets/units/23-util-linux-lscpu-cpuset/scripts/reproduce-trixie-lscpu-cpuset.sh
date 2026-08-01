#!/usr/bin/env bash
set -euo pipefail

baseline=/usr/bin/lscpu
candidate=
outdir=
while (($#)); do
  case "$1" in
    --baseline) baseline=$2; shift 2 ;;
    --candidate) candidate=$2; shift 2 ;;
    --output-dir) outdir=$2; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -x "$baseline" ]] || { echo "baseline is not executable: $baseline" >&2; exit 2; }
[[ -z "$candidate" || -x "$candidate" ]] || {
  echo "candidate is not executable: $candidate" >&2
  exit 2
}

if [[ -z "$outdir" ]]; then
  outdir=$(mktemp -d /tmp/unit23-evidence.XXXXXX)
  cleanup_out=1
else
  mkdir -p "$outdir"
  cleanup_out=0
fi
work=$(mktemp -d /tmp/unit23-lscpu.XXXXXX)
trap 'rm -rf "$work"; if [[ ${cleanup_out:-0} == 1 ]]; then echo "evidence retained at $outdir"; fi' EXIT

make_root() {
  local root=$1

  # Keep this fixture independent of the runner's live sysfs. Copying the
  # whole CPU tree can encounter transient or unreadable power attributes in
  # containers. lscpu needs only the bounded identities below to exercise the
  # affected cpuset allocation and cleanup path.
  mkdir -p \
    "$root/proc" \
    "$root/sys/devices/system/cpu" \
    "$root/sys/devices/system/node/node0"
  cp /proc/cpuinfo "$root/proc/cpuinfo"

  # Match the public report's bounded 16-CPU topology. kernel_max controls
  # util-linux's cpuset allocation size and is a required discriminator.
  printf '15\n' >"$root/sys/devices/system/cpu/kernel_max"
  printf '0-15\n' >"$root/sys/devices/system/cpu/possible"
  printf '0-15\n' >"$root/sys/devices/system/cpu/present"
  printf '0-15\n' >"$root/sys/devices/system/cpu/online"
  printf '0000ffff\n' >"$root/sys/devices/system/node/node0/cpumap"
}

run_case() {
  local bin=$1 impl=$2 case_name=$3 mode=$4 malformed=$5 expected=$6
  local root="$work/${impl}-${case_name}-${mode}"
  make_root "$root"
  [[ "$malformed" == 0 ]] || printf '5,12-%%\n' >"$root/sys/devices/system/cpu/online"

  local stdout="$outdir/${impl}-${case_name}-${mode}.stdout"
  local stderr="$outdir/${impl}-${case_name}-${mode}.stderr"
  local -a args=("$bin" --sysroot "$root")
  [[ "$mode" == text ]] || args+=(--json)

  set +e
  (ulimit -c 0; LC_ALL=C TERM=dumb timeout 15s "${args[@]}") >"$stdout" 2>"$stderr"
  local rc=$?
  set -e

  printf '%s %s %s rc=%d stdout_sha256=%s stderr_sha256=%s\n' \
    "$impl" "$case_name" "$mode" "$rc" \
    "$(sha256sum "$stdout" | cut -d' ' -f1)" \
    "$(sha256sum "$stderr" | cut -d' ' -f1)" >>"$outdir/results.txt"

  case "$expected" in
    success)
      [[ $rc -eq 0 ]] || {
        echo "$impl $case_name $mode expected success, got $rc" >&2
        return 1
      }
      if [[ "$mode" == json ]]; then
        python3 -m json.tool "$stdout" >/dev/null
      fi
      ;;
    signal)
      [[ $rc -ge 128 && $rc -ne 124 ]] || {
        echo "$impl $case_name $mode expected signal failure, got $rc" >&2
        return 1
      }
      ;;
    *)
      echo "bad expected state: $expected" >&2
      return 2
      ;;
  esac
}

: >"$outdir/results.txt"
{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "os=$(tr '\n' ' ' </etc/os-release)"
  echo "kernel=$(uname -srvmo)"
  echo "baseline=$baseline"
  echo "baseline_sha256=$(sha256sum "$baseline" | cut -d' ' -f1)"
  "$baseline" --version | head -1 | sed 's/^/baseline_version=/'
  if command -v dpkg-query >/dev/null 2>&1; then
    dpkg-query -W -f='baseline_package=${Package} ${Version} ${Architecture}\n' util-linux 2>/dev/null || true
  fi
  if [[ -n "$candidate" ]]; then
    echo "candidate=$candidate"
    echo "candidate_sha256=$(sha256sum "$candidate" | cut -d' ' -f1)"
    "$candidate" --version | head -1 | sed 's/^/candidate_version=/'
  fi
} >"$outdir/identity.txt"

run_case "$baseline" baseline valid text 0 success
run_case "$baseline" baseline valid json 0 success
run_case "$baseline" baseline malformed-online text 1 signal
run_case "$baseline" baseline malformed-online json 1 signal

if [[ -n "$candidate" ]]; then
  run_case "$candidate" candidate valid text 0 success
  run_case "$candidate" candidate valid json 0 success
  run_case "$candidate" candidate malformed-online text 1 success
  run_case "$candidate" candidate malformed-online json 1 success
fi

cat "$outdir/identity.txt"
cat "$outdir/results.txt"
