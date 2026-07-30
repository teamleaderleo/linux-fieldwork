#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/direct-path-results"

validate_runtime_parent() {
  local requested=$1 canonical
  canonical="$(realpath -m "$requested")"
  case "$canonical" in
    /tmp | /tmp/* | /var/tmp | /var/tmp/* | /home/runner/work/_temp | /home/runner/work/_temp/*) ;;
    *)
      echo "refusing unsafe runtime parent: $canonical" >&2
      return 2
      ;;
  esac
  printf '%s\n' "$canonical"
}

if [[ ${1-} == --check-runtime-parent ]]; then
  if [[ $# -ne 2 ]]; then
    echo 'usage: direct_path_probe.sh --check-runtime-parent PATH' >&2
    exit 2
  fi
  validate_runtime_parent "$2" >/dev/null
  exit
fi

runtime_parent="$(validate_runtime_parent "${RUNNER_TEMP:-/tmp}")"
runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-direct-path")"
if [[ "$runtime" == "$runtime_parent" ]]; then
  echo "refusing runtime equal to parent: $runtime" >&2
  exit 2
fi
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

for command_name in \
  apt-ftparchive \
  cp \
  dpkg \
  dpkg-deb \
  dpkg-query \
  gzip \
  python3 \
  realpath \
  stat \
  timeout; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "missing required command: $command_name" >&2
    exit 2
  }
done

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime/fake-bin" "$runtime/home" "$result_dir"
source_mode_before="$(stat -c '%a' "$source_root/mmdebstrap")"
candidate="$runtime/mmdebstrap-candidate"
cp --preserve=mode "$source_root/mmdebstrap" "$candidate"
cmp "$source_root/mmdebstrap" "$candidate"
chmod 0755 "$candidate"

mutation="$runtime/mmdebstrap-caller-path-mutation"
python3 - "$candidate" "$mutation" <<'PY'
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

arch="$(dpkg --print-architecture)"
fixture="$runtime/fixture"
repository="$runtime/repository"
pool="$repository/pool/main/l/lf-essential-path-probe"
binary_dir="$repository/dists/test/main/binary-$arch"
mkdir -p "$fixture/DEBIAN" "$fixture/usr/share/lf-essential-path-probe"
mkdir -p "$pool" "$binary_dir"

cat >"$fixture/DEBIAN/control" <<'EOF'
Package: lf-essential-path-probe
Version: 1.0
Section: misc
Priority: required
Architecture: all
Essential: yes
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: direct chrootless PATH probe
 A local Essential package for exercising mmdebstrap run_essential.
EOF

cat >"$fixture/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu

result_dir="$DPKG_ROOT/var/lib/lf-essential-path-probe"
mkdir -p "$result_dir"
printf '%s\n' "$PATH" >"$result_dir/path.txt"
printf 'postinst-ran=yes\n' >"$result_dir/result.txt"
EOF
chmod 0755 "$fixture/DEBIAN/postinst"
printf 'fixture payload\n' >"$fixture/usr/share/lf-essential-path-probe/payload"
package="$pool/lf-essential-path-probe_1.0_all.deb"
dpkg-deb --build --root-owner-group "$fixture" "$package" \
  >"$result_dir/package-build.stdout" \
  2>"$result_dir/package-build.stderr"

(
  cd "$repository"
  apt-ftparchive packages pool >"dists/test/main/binary-$arch/Packages"
  gzip -n -c "dists/test/main/binary-$arch/Packages" \
    >"dists/test/main/binary-$arch/Packages.gz"
  apt-ftparchive \
    -o APT::FTPArchive::Release::Origin='Linux Fieldwork' \
    -o APT::FTPArchive::Release::Label='Linux Fieldwork' \
    -o APT::FTPArchive::Release::Suite='test' \
    -o APT::FTPArchive::Release::Codename='test' \
    -o APT::FTPArchive::Release::Architectures="$arch" \
    -o APT::FTPArchive::Release::Components='main' \
    release dists/test >dists/test/Release
)
chmod -R a+rX "$repository"

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
  local source_spec="deb [trusted=yes] copy://$repository test main"
  local status

  : >"$wrapper_log"
  write_wrapper "$wrapper_log"
  set +e
  timeout 300 env -i \
    PATH="$runtime/fake-bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    "$mmdebstrap_path" \
      --mode=chrootless \
      --variant=essential \
      --format=directory \
      test "$target" "$source_spec" \
      >"$result_dir/$label.stdout" \
      2>"$result_dir/$label.stderr"
  status=$?
  set -e
  printf '%s\n' "$status" >"$result_dir/$label.status"

  if [[ "$status" -eq 124 ]]; then
    echo "$label transaction timed out" >&2
    exit 1
  fi
  [[ "$status" -eq 0 ]]
  grep -F 'I: installing essential packages...' "$result_dir/$label.stderr"
  test -f "$target/usr/share/lf-essential-path-probe/payload"
  grep -Fx 'postinst-ran=yes' \
    "$target/var/lib/lf-essential-path-probe/result.txt"
  cp -a "$target/var/lib/lf-essential-path-probe" \
    "$result_dir/$label-maintainer-script"
  dpkg-query --admindir="$target/var/lib/dpkg" \
    -W -f='${binary:Package}\n' \
    | sort >"$result_dir/$label-packages.txt"
  grep -Fx lf-essential-path-probe "$result_dir/$label-packages.txt"
  grep -Fx -- '--print-architecture' "$wrapper_log"
}

run_case candidate "$candidate"
if grep -F -- '--force-script-chrootless' \
  "$result_dir/candidate-dpkg-wrapper.log"; then
  echo "candidate direct chrootless dpkg used caller PATH" >&2
  exit 1
fi

run_case mutation "$mutation"
grep -F -- '--force-script-chrootless' \
  "$result_dir/mutation-dpkg-wrapper.log"

candidate_status="$(cat "$result_dir/candidate.status")"
mutation_status="$(cat "$result_dir/mutation.status")"
[[ "$candidate_status" -eq 0 ]]
[[ "$mutation_status" -eq 0 ]]
cmp "$result_dir/candidate-packages.txt" "$result_dir/mutation-packages.txt"

canonical_path=/usr/sbin:/usr/bin:/sbin:/bin
candidate_path="$(cat "$result_dir/candidate-maintainer-script/path.txt")"
mutation_path="$(cat "$result_dir/mutation-maintainer-script/path.txt")"
[[ "$candidate_path" == "$canonical_path" ]]
[[ "$mutation_path" == "$runtime/fake-bin:"* ]]

source_mode_after="$(stat -c '%a' "$source_root/mmdebstrap")"
[[ "$source_mode_after" == "$source_mode_before" ]]
git diff --exit-code -- upstream/mmdebstrap/mmdebstrap

cat >"$result_dir/summary.txt" <<EOF
product_source=upstream/mmdebstrap/mmdebstrap
executed_candidate_copy=$candidate
source_mode_before=$source_mode_before
source_mode_after=$source_mode_after
repository_source_unchanged=yes
repository_type=local_unsigned_trusted_copy_transport
variant=essential
candidate_transaction_status=$candidate_status
candidate_full_transaction_succeeded=yes
candidate_direct_run_essential_reached=yes
candidate_maintainer_script_path=$candidate_path
candidate_caller_dpkg_received_chrootless_args=no
mutation_transaction_status=$mutation_status
mutation_full_transaction_succeeded=yes
mutation_direct_run_essential_reached=yes
mutation_maintainer_script_path=$mutation_path
mutation_caller_dpkg_received_chrootless_args=yes
candidate_mutation_package_sets_equal=yes
interpretation=successful direct run_essential uses canonical DPkg::Path while the mutation restores caller-path dpkg resolution
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap direct chrootless canonical PATH probe passed'
