#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
timestamp=1700000000
old_timestamp=$((timestamp - 125000))
result_label="${RESULT_LABEL:-run}"
case "$result_label" in
  *[!A-Za-z0-9_.-]*|'')
    echo "invalid result label: $result_label" >&2
    exit 2
    ;;
esac

runtime_parent="$(realpath -m "${RUNNER_TEMP:-/tmp}")"
case "$runtime_parent" in
  /tmp|/tmp/*|/var/tmp|/var/tmp/*|/home/runner/work/_temp|/home/runner/work/_temp/*)
    ;;
  *)
    echo "refusing unsafe runtime parent: $runtime_parent" >&2
    exit 2
    ;;
esac

runtime="$runtime_parent/mmdebstrap-chrootless-directory-mtime-real"
if [[ -L "$runtime" ]]; then
  echo "refusing symlink runtime leaf: $runtime" >&2
  exit 2
fi
runtime_canonical="$(realpath -m "$runtime")"
case "$runtime_canonical" in
  "$runtime_parent"/*) ;;
  *)
    echo "refusing runtime outside parent: $runtime_canonical" >&2
    exit 2
    ;;
esac
[[ "$runtime_canonical" != / && "$runtime_canonical" != "$runtime_parent" ]] || {
  echo "refusing unsafe runtime: $runtime_canonical" >&2
  exit 2
}

repo_canonical="$(realpath -m "$repo_root")"
home_canonical="$(realpath -m "${HOME:-/nonexistent-home}")"
for protected in "$repo_canonical" "$home_canonical"; do
  [[ "$protected" != / ]] || {
    echo "refusing unbounded protected root: $protected" >&2
    exit 2
  }
done

case "$runtime_canonical" in
  "$repo_canonical"|"$repo_canonical"/*)
    echo "refusing runtime inside repository: $runtime_canonical" >&2
    exit 2
    ;;
esac
case "$repo_canonical" in
  "$runtime_canonical"|"$runtime_canonical"/*)
    echo "refusing runtime containing repository: $runtime_canonical" >&2
    exit 2
    ;;
esac

case "$runtime_parent" in
  /home/runner/work/_temp|/home/runner/work/_temp/*)
    case "$home_canonical" in
      "$runtime_canonical"|"$runtime_canonical"/*)
        echo "refusing runtime containing home: $runtime_canonical" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    case "$runtime_canonical" in
      "$home_canonical"|"$home_canonical"/*)
        echo "refusing runtime inside home: $runtime_canonical" >&2
        exit 2
        ;;
    esac
    case "$home_canonical" in
      "$runtime_canonical"|"$runtime_canonical"/*)
        echo "refusing runtime containing home: $runtime_canonical" >&2
        exit 2
        ;;
    esac
    ;;
esac

if [[ ${1-} == --check-runtime-parent ]]; then
  [[ $# -eq 1 ]] || {
    echo 'usage: real_metadata_probe.sh --check-runtime-parent' >&2
    exit 2
  }
  printf '%s\n' "$runtime"
  exit
fi
[[ $# -eq 0 ]] || {
  echo 'usage: real_metadata_probe.sh [--check-runtime-parent]' >&2
  exit 2
}

result_dir="$repo_root/investigations/mmdebstrap-chrootless-directory-mtime/real-boundary-results"
tree="$runtime/tree"
mount_dir="$tree/foreign-device"
mounted=no

cleanup() {
  local cleanup_status=0
  set +e
  if [[ $mounted == yes ]] || mountpoint -q "$mount_dir" 2>/dev/null; then
    sudo umount "$mount_dir" || cleanup_status=$?
    if mountpoint -q "$mount_dir" 2>/dev/null; then
      [[ $cleanup_status -ne 0 ]] || cleanup_status=1
      echo "refusing recursive cleanup while mount is still active: $mount_dir" >&2
      return "$cleanup_status"
    fi
    mounted=no
  fi
  rm -rf "$runtime" || cleanup_status=$?
  return "$cleanup_status"
}

on_signal() {
  local status=$1
  trap - EXIT INT TERM
  cleanup || true
  exit "$status"
}

trap cleanup EXIT
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

for command_name in \
  findmnt \
  getcap \
  getfacl \
  mountpoint \
  python3 \
  realpath \
  setcap \
  setfacl \
  stat \
  sudo; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "missing required command: $command_name" >&2
    exit 2
  }
done

if mountpoint -q "$mount_dir" 2>/dev/null; then
  echo "refusing stale mount before runtime reset: $mount_dir" >&2
  exit 2
fi
rm -rf "$runtime"
mkdir -p "$tree/ordinary" "$tree/acl-directory" "$mount_dir" "$result_dir"

acl_file="$tree/acl-directory/payload"
cap_file="$tree/capability-helper"
printf 'acl bytes\n' >"$acl_file"
printf '#!/bin/sh\nexit 0\n' >"$cap_file"
chmod 0755 "$cap_file"

touch -h --date="@$old_timestamp" \
  "$tree/ordinary" \
  "$tree/acl-directory" \
  "$acl_file" \
  "$cap_file"
setfacl -m u:nobody:rx "$tree/acl-directory"
setfacl -m u:nobody:r "$acl_file"
sudo setcap cap_net_bind_service=ep "$cap_file"

sudo mount -t tmpfs -o size=1m,mode=0755 tmpfs "$mount_dir"
mounted=yes
sudo chown "$(id -u):$(id -g)" "$mount_dir"
mkdir -p "$mount_dir/nested"
printf 'mounted sentinel\n' >"$mount_dir/nested/sentinel"
touch -h --date="@$old_timestamp" \
  "$mount_dir" \
  "$mount_dir/nested" \
  "$mount_dir/nested/sentinel"

root_device="$(stat -c '%d' "$tree")"
mount_device="$(stat -c '%d' "$mount_dir")"
[[ "$root_device" != "$mount_device" ]] || {
  echo "tmpfs did not create a distinct device" >&2
  exit 1
}

ordinary_before="$(stat -c '%Y' "$tree/ordinary")"
mount_before="$(stat -c '%Y' "$mount_dir")"
nested_before="$(stat -c '%Y' "$mount_dir/nested")"
sentinel_before="$(stat -c '%Y' "$mount_dir/nested/sentinel")"
acl_before="$(getfacl -cp "$tree/acl-directory" "$acl_file")"
cap_before="$(getcap -n "$cap_file")"
[[ -n "$cap_before" ]] || {
  echo "file capability was not recorded" >&2
  exit 1
}

candidate_patch="$repo_root/investigations/mmdebstrap-chrootless-directory-mtime/0001-normalize-root-chrootless-directory-mtimes.patch"
normalizer=python-evidence-model
if [[ -f "$candidate_patch" ]]; then
  for command_name in patch perl; do
    command -v "$command_name" >/dev/null 2>&1 || {
      echo "missing product normalizer command: $command_name" >&2
      exit 2
    }
  done
  product_normalizer="$runtime/product-normalizer.pl"
  python3 \
    "$repo_root/investigations/mmdebstrap-chrootless-directory-mtime/prepare_product_normalizer.py" \
    "$product_normalizer" \
    >"$result_dir/$result_label-product-normalizer.stdout" \
    2>"$result_dir/$result_label-product-normalizer.stderr"
  perl "$product_normalizer" "$tree" "$timestamp"
  normalizer=extracted-product-perl-helper
else
  python3 - "$repo_root" "$tree" "$timestamp" <<'PY'
import pathlib
import sys

repo = pathlib.Path(sys.argv[1])
tree = pathlib.Path(sys.argv[2])
timestamp = int(sys.argv[3])
sys.path.insert(0, str(repo / "tests"))
from test_mmdebstrap_chrootless_directory_mtime import normalize_directory_mtimes

normalize_directory_mtimes(tree, timestamp)
PY
fi

ordinary_after="$(stat -c '%Y' "$tree/ordinary")"
mount_after="$(stat -c '%Y' "$mount_dir")"
nested_after="$(stat -c '%Y' "$mount_dir/nested")"
sentinel_after="$(stat -c '%Y' "$mount_dir/nested/sentinel")"
acl_after="$(getfacl -cp "$tree/acl-directory" "$acl_file")"
cap_after="$(getcap -n "$cap_file")"

[[ "$ordinary_before" == "$old_timestamp" ]]
[[ "$ordinary_after" == "$timestamp" ]]
[[ "$mount_after" == "$mount_before" ]]
[[ "$nested_after" == "$nested_before" ]]
[[ "$sentinel_after" == "$sentinel_before" ]]
[[ "$acl_after" == "$acl_before" ]]
[[ "$cap_after" == "$cap_before" ]]
grep -Fx 'mounted sentinel' "$mount_dir/nested/sentinel" >/dev/null
mountpoint -q "$mount_dir"
[[ "$(findmnt -rn -T "$mount_dir" -o FSTYPE)" == tmpfs ]]

summary="$result_dir/$result_label.txt"
cat >"$summary" <<EOF
schema_version=1
result_label=$result_label
normalizer=$normalizer
normalization_timestamp=$timestamp
root_device=$root_device
foreign_device=$mount_device
ordinary_directory_before=$ordinary_before
ordinary_directory_after=$ordinary_after
foreign_mount_before=$mount_before
foreign_mount_after=$mount_after
foreign_nested_before=$nested_before
foreign_nested_after=$nested_after
foreign_sentinel_before=$sentinel_before
foreign_sentinel_after=$sentinel_after
acl_preserved=yes
capability_preserved=yes
mount_remained_active=yes
foreign_sentinel_preserved=yes
EOF

cat "$summary"

trap - EXIT INT TERM
cleanup
[[ ! -e "$runtime" ]] || {
  echo "runtime survived cleanup: $runtime" >&2
  exit 1
}

echo "real directory-mtime metadata boundary probe passed"
