#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/direct-path-results"
runtime_parent="$(realpath -m "${RUNNER_TEMP:-/tmp}")"

if [[ "$runtime_parent" == / ]]; then
  echo "refusing unsafe runtime parent: $runtime_parent" >&2
  exit 2
fi
runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-direct-path")"
case "$runtime" in
  "$runtime_parent"/*) ;;
  *)
    echo "refusing runtime outside parent: $runtime" >&2
    exit 2
    ;;
esac

result_parent="$(realpath -m "$repo_root/investigations/mmdebstrap-chrootless-env")"
result_dir="$(realpath -m "$result_dir")"
case "$result_dir" in
  "$result_parent"/*) ;;
  *)
    echo "refusing result directory outside investigation: $result_dir" >&2
    exit 2
    ;;
esac

cleanup() {
  chmod -R u+w "$runtime" 2>/dev/null || true
  rm -rf "$runtime"
}
trap cleanup EXIT INT TERM

for command_name in dpkg dpkg-query python3 realpath timeout; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "missing required command: $command_name" >&2
    exit 2
  }
done

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime/fake-bin" "$runtime/home" "$result_dir"
chmod 0755 "$source_root/mmdebstrap"

mutation="$runtime/mmdebstrap-caller-path-mutation"
python3 - "$source_root/mmdebstrap" "$mutation" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
old = '    my @result = (\'-i\', "PATH=$dpkgpath", "TMPDIR=$tmpdir");\n'
new = '    my @result = (\'-i\', "PATH=$ENV{PATH}", "TMPDIR=$tmpdir");\n'
if source.count(old) != 1:
    raise SystemExit("canonical PATH source marker not found exactly once")
Path(sys.argv[2]).write_text(source.replace(old, new), encoding="utf-8")
PY
chmod 0755 "$mutation"

write_wrapper() {
  local log_file=$1
  cat >"$runtime/fake-bin/dpkg" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$log_file"
exec /usr/bin/dpkg "\$@"
EOF
  chmod 0755 "$runtime/fake-bin/dpkg"
}

run_case() {
  local label=$1
  local mmdebstrap_path=$2
  local target="$runtime/$label-root"
  local wrapper_log="$result_dir/$label-dpkg-wrapper.log"
  local source_spec='deb [trusted=yes] https://deb.debian.org/debian sid main'

  : >"$wrapper_log"
  write_wrapper "$wrapper_log"
  timeout 900 env -i \
    PATH="$runtime/fake-bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    "$mmdebstrap_path" \
      --mode=chrootless \
      --variant=essential \
      --format=directory \
      sid "$target" "$source_spec" \
      >"$result_dir/$label.stdout" \
      2>"$result_dir/$label.stderr"

  test -s "$target/var/lib/dpkg/status"
  dpkg-query --admindir="$target/var/lib/dpkg" \
    -W -f='${binary:Package}\n' \
    | sort >"$result_dir/$label-packages.txt"
  test -s "$result_dir/$label-packages.txt"
}

run_case candidate "$source_root/mmdebstrap"
if grep -F -- '--force-script-chrootless' \
  "$result_dir/candidate-dpkg-wrapper.log"; then
  echo "candidate direct chrootless dpkg used caller PATH" >&2
  exit 1
fi

run_case mutation "$mutation"
grep -F -- '--force-script-chrootless' \
  "$result_dir/mutation-dpkg-wrapper.log"

cmp "$result_dir/candidate-packages.txt" "$result_dir/mutation-packages.txt"

cat >"$result_dir/summary.txt" <<EOF
product_source=upstream/mmdebstrap/mmdebstrap
variant=essential
candidate_transaction_succeeded=yes
candidate_caller_dpkg_received_chrootless_args=no
mutation_transaction_succeeded=yes
mutation_caller_dpkg_received_chrootless_args=yes
candidate_mutation_package_sets_equal=yes
interpretation=direct run_essential uses canonical DPkg::Path
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap direct chrootless canonical PATH probe passed'
