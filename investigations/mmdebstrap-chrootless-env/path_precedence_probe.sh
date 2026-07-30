#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/path-results"

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
    echo 'usage: path_precedence_probe.sh --check-runtime-parent PATH' >&2
    exit 2
  fi
  validate_runtime_parent "$2" >/dev/null
  exit
fi

runtime_parent="$(validate_runtime_parent "${RUNNER_TEMP:-/tmp}")"
runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-path-precedence")"
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
  rm -rf "$runtime"
}
trap cleanup EXIT INT TERM

for command_name in cp dpkg-deb dpkg-query python3 realpath stat; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "missing required command: $command_name" >&2
    exit 2
  }
done

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime/fixture/DEBIAN" "$runtime/fake-bin" "$runtime/home"
mkdir -p "$runtime/fixture/usr/share/lf-path-precedence" "$result_dir"
source_mode_before="$(stat -c '%a' "$source_root/mmdebstrap")"
candidate="$runtime/mmdebstrap-candidate"
cp --preserve=mode "$source_root/mmdebstrap" "$candidate"
cmp "$source_root/mmdebstrap" "$candidate"
chmod 0755 "$candidate"

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
for tool in dpkg ldconfig start-stop-daemon update-rc.d; do
  if tool_path="$(command -v "$tool" 2>/dev/null)"; then
    printf '%s=%s\n' "$tool" "$tool_path"
  else
    printf '%s=<missing>\n' "$tool"
  fi
done >"$result_dir/tools.txt"
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

run_case() {
  local label=$1
  local path_value=$2
  local mmdebstrap_path=$3
  local target="$runtime/$label-root"
  local package_dir hook
  package_dir="$(dirname "$package")"
  printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' \
    "$package_dir" "$package" "$package"

  env -i \
    PATH="$path_value" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    "$mmdebstrap_path" \
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
tainted_path_value="$runtime/fake-bin:$system_path"
run_case candidate-tainted "$tainted_path_value" "$candidate"
run_case candidate-clean "$system_path" "$candidate"
run_case mutation-tainted "$tainted_path_value" "$mutation"

for label in candidate-tainted candidate-clean; do
  grep -Fx 'caller_command_resolved=no' \
    "$result_dir/$label-maintainer-script/result.txt"
  test ! -e "$result_dir/$label-maintainer-script/command.txt"
  for tool in dpkg ldconfig start-stop-daemon update-rc.d; do
    grep -E "^$tool=/" "$result_dir/$label-maintainer-script/tools.txt"
  done
done

candidate_tainted_path="$(cat "$result_dir/candidate-tainted-maintainer-script/path.txt")"
candidate_clean_path="$(cat "$result_dir/candidate-clean-maintainer-script/path.txt")"
[[ "$candidate_tainted_path" == "$candidate_clean_path" ]]
[[ "$candidate_tainted_path" != *"$runtime/fake-bin"* ]]

grep -Fx 'caller_command_resolved=yes' \
  "$result_dir/mutation-tainted-maintainer-script/result.txt"
grep -Fx 'source=caller-path' \
  "$result_dir/mutation-tainted-maintainer-script/command.txt"
mutation_path="$(cat "$result_dir/mutation-tainted-maintainer-script/path.txt")"
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
caller_path_directory=$runtime/fake-bin
candidate_tainted_maintainer_script_path=$candidate_tainted_path
candidate_tainted_caller_command_resolved=no
candidate_clean_maintainer_script_path=$candidate_clean_path
candidate_clean_caller_command_resolved=no
mutation_tainted_maintainer_script_path=$mutation_path
mutation_tainted_caller_command_resolved=yes
expected_tools_resolved=yes
interpretation=canonical DPkg::Path blocks caller-prefix command resolution
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap chrootless canonical PATH candidate passed'
