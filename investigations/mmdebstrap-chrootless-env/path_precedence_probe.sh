#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/path-results"
runtime_parent="$(realpath -m "${RUNNER_TEMP:-/tmp}")"

if [[ "$runtime_parent" == / ]]; then
  echo "refusing unsafe runtime parent: $runtime_parent" >&2
  exit 2
fi
runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-path-precedence")"
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
  rm -rf "$runtime"
}
trap cleanup EXIT INT TERM

for command_name in dpkg-deb dpkg-query realpath; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "missing required command: $command_name" >&2
    exit 2
  }
done

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime/fixture/DEBIAN" "$runtime/fake-bin" "$runtime/home"
mkdir -p "$runtime/fixture/usr/share/lf-path-precedence" "$result_dir"

cat >"$runtime/fixture/DEBIAN/control" <<'EOF'
Package: lf-path-precedence-probe
Version: 1.0
Section: misc
Priority: optional
Architecture: all
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: chrootless maintainer-script PATH precedence probe
 A local-only fixture for measuring executable lookup in maintainer scripts.
EOF

cat >"$runtime/fixture/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu

result_dir="$DPKG_ROOT/var/lib/lf-path-precedence-probe"
mkdir -p "$result_dir"
printf '%s\n' "$PATH" >"$result_dir/path.txt"
if command -v lf-path-probe >/dev/null 2>&1; then
  lf-path-probe
  printf 'caller_command_resolved=yes\n' >"$result_dir/result.txt"
else
  printf 'caller_command_resolved=no\n' >"$result_dir/result.txt"
fi
EOF
chmod 0755 "$runtime/fixture/DEBIAN/postinst"
printf 'fixture payload\n' >"$runtime/fixture/usr/share/lf-path-precedence/payload"

dpkg-deb --build --root-owner-group \
  "$runtime/fixture" "$runtime/lf-path-precedence-probe_1.0_all.deb" \
  >"$result_dir/package-build.stdout" \
  2>"$result_dir/package-build.stderr"
package="$runtime/lf-path-precedence-probe_1.0_all.deb"

cat >"$runtime/fake-bin/lf-path-probe" <<'EOF'
#!/bin/sh
set -eu
printf 'source=caller-path\n' \
  >"$DPKG_ROOT/var/lib/lf-path-precedence-probe/command.txt"
EOF
chmod 0755 "$runtime/fake-bin/lf-path-probe"
chmod 0755 "$source_root/mmdebstrap"

run_case() {
  local label=$1 path_value=$2 target="$runtime/$label-root"
  local package_dir hook
  package_dir="$(dirname "$package")"
  printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' \
    "$package_dir" "$package" "$package"

  env -i \
    PATH="$path_value" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    "$source_root/mmdebstrap" \
      --mode=chrootless \
      --variant=custom \
      --format=directory \
      --skip=update \
      --include="$package" \
      --setup-hook="$hook" \
      '' "$target" \
      >"$result_dir/$label.stdout" \
      2>"$result_dir/$label.stderr"

  test -f "$target/usr/share/lf-path-precedence/payload"
  dpkg-query --admindir="$target/var/lib/dpkg" \
    -W -f='${db:Status-Status}\n' lf-path-precedence-probe \
    | grep -Fx installed >/dev/null
  cp -a "$target/var/lib/lf-path-precedence-probe" \
    "$result_dir/$label-maintainer-script"
}

system_path=/usr/sbin:/usr/bin:/sbin:/bin
run_case tainted "$runtime/fake-bin:$system_path"
run_case clean "$system_path"

grep -Fx 'caller_command_resolved=yes' \
  "$result_dir/tainted-maintainer-script/result.txt"
grep -Fx 'source=caller-path' \
  "$result_dir/tainted-maintainer-script/command.txt"
tainted_path="$(cat "$result_dir/tainted-maintainer-script/path.txt")"
[[ "$tainted_path" == "$runtime/fake-bin:"* ]]

grep -Fx 'caller_command_resolved=no' \
  "$result_dir/clean-maintainer-script/result.txt"
test ! -e "$result_dir/clean-maintainer-script/command.txt"
clean_path="$(cat "$result_dir/clean-maintainer-script/path.txt")"
[[ "$clean_path" != *"$runtime/fake-bin"* ]]

cat >"$result_dir/summary.txt" <<EOF
product_source=upstream/mmdebstrap/mmdebstrap
caller_path_directory=$runtime/fake-bin
tainted_maintainer_script_path=$tainted_path
tainted_caller_command_resolved=yes
clean_maintainer_script_path=$clean_path
clean_caller_command_resolved=no
interpretation=caller PATH prefix reaches apt-managed chrootless maintainer scripts
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap chrootless PATH precedence probe passed'
