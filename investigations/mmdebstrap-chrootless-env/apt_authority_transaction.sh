#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/apt-authority-results"
argv_classifier="$repo_root/tools/classify_env_argv.py"
runtime_leaf=mmdebstrap-chrootless-apt-authority
source "$repo_root/investigations/mmdebstrap-unwritable-tmpdir/runtime_guard.sh"

if [[ ${1-} == --check-runtime-parent ]]; then
  [[ $# -eq 2 ]] || {
    echo 'usage: apt_authority_transaction.sh --check-runtime-parent PATH' >&2
    exit 2
  }
  validate_disposable_runtime \
    "$repo_root" "${HOME:-/nonexistent-home}" "$2" "$runtime_leaf" \
    >/dev/null
  exit
fi

runtime="$(validate_disposable_runtime \
  "$repo_root" \
  "${HOME:-/nonexistent-home}" \
  "${RUNNER_TEMP:-/tmp}" \
  "$runtime_leaf")"

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
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for command_name in \
  cp \
  dpkg-deb \
  dpkg-query \
  patch \
  perl \
  python3 \
  realpath \
  stat \
  timeout; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "missing required command: $command_name" >&2
    exit 2
  }
done
[[ -f "$argv_classifier" ]] || {
  echo "missing env argv classifier: $argv_classifier" >&2
  exit 2
}

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime/fixture/DEBIAN" "$runtime/fake-bin" "$runtime/home"
mkdir -p "$runtime/fixture/usr/share/lf-apt-authority-probe" "$result_dir"
source_mode_before="$(stat -c '%a' "$source_root/mmdebstrap")"

prepared="$runtime/prepared"
python3 \
  "$repo_root/investigations/mmdebstrap-chrootless-env/prepare_authority_candidates.py" \
  "$prepared" --json >"$result_dir/prepared.json"
candidate="$prepared/candidate-tree/upstream/mmdebstrap/mmdebstrap"
inner_mutation="$prepared/mmdebstrap-inner-path-mutation"
outer_mutation="$prepared/mmdebstrap-outer-env-mutation"

cat >"$runtime/fixture/DEBIAN/control" <<'EOF'
Package: lf-apt-authority-probe
Version: 1.0
Section: misc
Priority: optional
Architecture: all
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: apt-managed chrootless executable authority probe
 A local-only fixture for measuring wrapper and PATH authority.
EOF

cat >"$runtime/fixture/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu

result_dir="$DPKG_ROOT/var/lib/lf-apt-authority-probe"
mkdir -p "$result_dir"
printf '%s\n' "$PATH" >"$result_dir/path.txt"
if command -v lf-authority-helper >/dev/null 2>&1; then
  lf-authority-helper
  printf 'configured_or_caller_command_resolved=yes\n' >"$result_dir/result.txt"
else
  printf 'configured_or_caller_command_resolved=no\n' >"$result_dir/result.txt"
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
printf 'fixture payload\n' >"$runtime/fixture/usr/share/lf-apt-authority-probe/payload"
package="$runtime/lf-apt-authority-probe_1.0_all.deb"
dpkg-deb --build --root-owner-group "$runtime/fixture" "$package" \
  >"$result_dir/package-build.stdout" \
  2>"$result_dir/package-build.stderr"

cat >"$runtime/fake-bin/lf-authority-helper" <<'EOF'
#!/bin/sh
set -eu
printf 'source=fake-bin\n' \
  >"$DPKG_ROOT/var/lib/lf-apt-authority-probe/command.txt"
EOF
chmod 0755 "$runtime/fake-bin/lf-authority-helper"

cat >"$runtime/fake-bin/env" <<'EOF'
#!/bin/sh
set -eu
: "${OUTER_ENV_LOG_DIR:?}"
umask 077
record="$OUTER_ENV_LOG_DIR/argv.$$"
set -C
exec 9>"$record"
set +C
printf '%s\0' "$@" >&9
exec 9>&-
exec /usr/bin/env "$@"
EOF
chmod 0755 "$runtime/fake-bin/env"

classify_outer_env() {
  local label=$1
  local record_dir="$result_dir/$label-outer-env"
  local summary="$result_dir/$label-outer-env.json"
  python3 "$argv_classifier" "$record_dir" --output "$summary" \
    >"$result_dir/$label-outer-env.stdout" \
    2>"$result_dir/$label-outer-env.stderr"
}

require_outer_env_contract() {
  local label=$1 expected_sanitizer=$2 expected_host_calls=$3
  python3 - \
    "$result_dir/$label-outer-env.json" \
    "$expected_sanitizer" \
    "$expected_host_calls" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
expected_sanitizer = sys.argv[2]
expected_host_calls = sys.argv[3]
payload = json.loads(path.read_text(encoding="utf-8"))
if type(payload) is not dict or payload.get("schema_version") != 1:
    raise SystemExit(f"invalid env argv summary schema: {path}")
counts = payload.get("counts")
if type(counts) is not dict:
    raise SystemExit(f"env argv summary counts are missing: {path}")
required = (
    "host-version-probe",
    "host-shell-hook",
    "sanitizer-dpkg",
    "other-host",
)
for name in required:
    value = counts.get(name)
    if type(value) is not int or value < 0:
        raise SystemExit(f"invalid {name} count in {path}: {value!r}")
files_checked = payload.get("files_checked")
if type(files_checked) is not int or files_checked < 0:
    raise SystemExit(f"invalid files_checked in {path}: {files_checked!r}")
if sum(counts[name] for name in required) != files_checked:
    raise SystemExit(f"env argv count total mismatch: {path}")
records = payload.get("records")
if type(records) is not list or len(records) != files_checked:
    raise SystemExit(f"env argv record inventory mismatch: {path}")

sanitizer_count = counts["sanitizer-dpkg"]
if expected_sanitizer == "absent":
    if sanitizer_count != 0:
        raise SystemExit(
            f"caller-path dpkg sanitizer unexpectedly executed {sanitizer_count} time(s): {path}"
        )
elif expected_sanitizer == "present":
    if sanitizer_count < 1:
        raise SystemExit(f"caller-path dpkg sanitizer was not observed: {path}")
else:
    raise SystemExit(f"invalid sanitizer expectation: {expected_sanitizer}")

if expected_host_calls == "present":
    if counts["host-version-probe"] < 1:
        raise SystemExit(f"caller-path env version probe was not observed: {path}")
    if counts["host-shell-hook"] < 1:
        raise SystemExit(f"caller-path setup hook was not observed: {path}")
elif expected_host_calls == "absent":
    if files_checked != 0:
        raise SystemExit(f"caller-path env unexpectedly executed: {path}")
else:
    raise SystemExit(f"invalid host-call expectation: {expected_host_calls}")

# "other-host" remains retained evidence. It is outside the two product-patch
# boundaries and must not be silently discarded or promoted to sanitizer use.
print(
    json.dumps(
        {
            "summary": str(path),
            "host-version-probe": counts["host-version-probe"],
            "host-shell-hook": counts["host-shell-hook"],
            "sanitizer-dpkg": counts["sanitizer-dpkg"],
            "other-host": counts["other-host"],
        },
        sort_keys=True,
    )
)
PY
}

json_count() {
  local summary=$1 classification=$2
  python3 - "$summary" "$classification" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
value = payload["counts"][sys.argv[2]]
if type(value) is not int or value < 0:
    raise SystemExit("invalid classification count")
print(value)
PY
}

make_hook() {
  local package_dir
  package_dir="$(dirname "$package")"
  printf 'mkdir -p "$1%s"; cp "%s" "$1%s"' \
    "$package_dir" "$package" "$package"
}

run_case() {
  local label=$1
  local path_value=$2
  local mmdebstrap_path=$3
  local apt_config=${4-}
  local target="$runtime/$label-root"
  local outer_dir="$result_dir/$label-outer-env"
  local hook
  local status
  local -a launch_env=(
    /usr/bin/env -i
    PATH="$path_value"
    HOME="$runtime/home"
    TMPDIR="$runtime"
    LC_ALL=C.UTF-8
    OUTER_ENV_LOG_DIR="$outer_dir"
  )
  hook="$(make_hook)"
  rm -rf "$outer_dir"
  mkdir -p "$outer_dir"
  if [[ -n "$apt_config" ]]; then
    launch_env+=(APT_CONFIG="$apt_config")
  fi

  set +e
  timeout 300 "${launch_env[@]}" \
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
  status=$?
  set -e
  printf '%s\n' "$status" >"$result_dir/$label.status"
  classify_outer_env "$label"

  [[ "$status" -ne 124 ]] || {
    echo "$label transaction timed out" >&2
    exit 1
  }
  [[ "$status" -eq 0 ]]
  test -f "$target/usr/share/lf-apt-authority-probe/payload"
  dpkg-query --admindir="$target/var/lib/dpkg" \
    -W -f='${db:Status-Status}\n' lf-apt-authority-probe \
    | grep -Fx installed >/dev/null
  cp -a "$target/var/lib/lf-apt-authority-probe" \
    "$result_dir/$label-maintainer-script"
  dpkg-query --admindir="$target/var/lib/dpkg" \
    -W -f='${binary:Package}\n' \
    | sort >"$result_dir/$label-packages.txt"
}

system_path=/usr/sbin:/usr/bin:/sbin:/bin
tainted_path="$runtime/fake-bin:$system_path"
run_case candidate-tainted "$tainted_path" "$candidate"
run_case candidate-clean "$system_path" "$candidate"
run_case inner-mutation-tainted "$tainted_path" "$inner_mutation"
run_case outer-mutation-tainted "$tainted_path" "$outer_mutation"

for label in candidate-tainted candidate-clean outer-mutation-tainted; do
  grep -Fx 'configured_or_caller_command_resolved=no' \
    "$result_dir/$label-maintainer-script/result.txt"
  test ! -e "$result_dir/$label-maintainer-script/command.txt"
done

grep -Fx 'configured_or_caller_command_resolved=yes' \
  "$result_dir/inner-mutation-tainted-maintainer-script/result.txt"
grep -Fx 'source=fake-bin' \
  "$result_dir/inner-mutation-tainted-maintainer-script/command.txt"

require_outer_env_contract candidate-tainted absent present
require_outer_env_contract candidate-clean absent absent
require_outer_env_contract inner-mutation-tainted absent present
require_outer_env_contract outer-mutation-tainted present present

candidate_tainted_path="$(cat "$result_dir/candidate-tainted-maintainer-script/path.txt")"
candidate_clean_path="$(cat "$result_dir/candidate-clean-maintainer-script/path.txt")"
inner_path="$(cat "$result_dir/inner-mutation-tainted-maintainer-script/path.txt")"
outer_path="$(cat "$result_dir/outer-mutation-tainted-maintainer-script/path.txt")"
[[ "$candidate_tainted_path" == "$candidate_clean_path" ]]
[[ "$candidate_tainted_path" == "$system_path" ]]
[[ "$outer_path" == "$system_path" ]]
[[ "$inner_path" == "$runtime/fake-bin:"* ]]

configured_path="$runtime/fake-bin:$system_path"
configured_config="$runtime/apt-configured-dpkg-path.conf"
printf 'DPkg::Path "%s";\n' "$configured_path" >"$configured_config"
run_case configured-authority "$system_path" "$candidate" "$configured_config"
grep -Fx 'configured_or_caller_command_resolved=yes' \
  "$result_dir/configured-authority-maintainer-script/result.txt"
grep -Fx 'source=fake-bin' \
  "$result_dir/configured-authority-maintainer-script/command.txt"
configured_authority_path="$(cat "$result_dir/configured-authority-maintainer-script/path.txt")"
[[ "$configured_authority_path" == "$configured_path" ]]
require_outer_env_contract configured-authority absent absent

empty_config="$runtime/apt-empty-dpkg-path.conf"
printf 'DPkg::Path "";\n' >"$empty_config"
empty_target="$runtime/empty-dpkg-path-root"
empty_hook="$(make_hook)"
empty_outer_dir="$result_dir/empty-dpkg-path-outer-env"
rm -rf "$empty_outer_dir"
mkdir -p "$empty_outer_dir"
set +e
timeout 300 /usr/bin/env -i \
  PATH="$system_path" \
  HOME="$runtime/home" \
  TMPDIR="$runtime" \
  LC_ALL=C.UTF-8 \
  OUTER_ENV_LOG_DIR="$empty_outer_dir" \
  APT_CONFIG="$empty_config" \
  "$candidate" \
    --mode=chrootless \
    --variant=custom \
    --format=directory \
    --skip=update \
    --include="$package" \
    --setup-hook="$empty_hook" \
    '' "$empty_target" \
    >"$result_dir/empty-dpkg-path.stdout" \
    2>"$result_dir/empty-dpkg-path.stderr"
empty_status=$?
set -e
classify_outer_env empty-dpkg-path
[[ "$empty_status" -ne 0 ]]
[[ "$empty_status" -ne 124 ]]
grep -F 'cannot determine chrootless maintainer-script PATH' \
  "$result_dir/empty-dpkg-path.stderr"
test ! -f "$empty_target/var/lib/lf-apt-authority-probe/result.txt"
require_outer_env_contract empty-dpkg-path absent absent

for label in \
  candidate-clean \
  inner-mutation-tainted \
  outer-mutation-tainted \
  configured-authority; do
  cmp "$result_dir/candidate-tainted-packages.txt" \
    "$result_dir/$label-packages.txt"
done

source_mode_after="$(stat -c '%a' "$source_root/mmdebstrap")"
[[ "$source_mode_after" == "$source_mode_before" ]]
git diff --exit-code -- upstream/mmdebstrap/mmdebstrap

candidate_version_calls="$(json_count "$result_dir/candidate-tainted-outer-env.json" "host-version-probe")"
candidate_hook_calls="$(json_count "$result_dir/candidate-tainted-outer-env.json" "host-shell-hook")"
candidate_sanitizer_calls="$(json_count "$result_dir/candidate-tainted-outer-env.json" "sanitizer-dpkg")"
candidate_other_host_calls="$(json_count "$result_dir/candidate-tainted-outer-env.json" "other-host")"
inner_sanitizer_calls="$(json_count "$result_dir/inner-mutation-tainted-outer-env.json" "sanitizer-dpkg")"
outer_sanitizer_calls="$(json_count "$result_dir/outer-mutation-tainted-outer-env.json" "sanitizer-dpkg")"

cat >"$result_dir/summary.txt" <<EOF
product_source=upstream/mmdebstrap/mmdebstrap
executed_candidate_copy=$candidate
source_mode_before=$source_mode_before
source_mode_after=$source_mode_after
repository_source_unchanged=yes
candidate_tainted_status=$(cat "$result_dir/candidate-tainted.status")
candidate_tainted_path=$candidate_tainted_path
candidate_tainted_fake_inner_command=no
candidate_tainted_caller_env_version_calls=$candidate_version_calls
candidate_tainted_caller_env_hook_calls=$candidate_hook_calls
candidate_tainted_caller_env_sanitizer_calls=$candidate_sanitizer_calls
candidate_tainted_other_host_calls=$candidate_other_host_calls
candidate_clean_status=$(cat "$result_dir/candidate-clean.status")
candidate_clean_path=$candidate_clean_path
inner_mutation_status=$(cat "$result_dir/inner-mutation-tainted.status")
inner_mutation_path=$inner_path
inner_mutation_fake_inner_command=yes
inner_mutation_caller_env_sanitizer_calls=$inner_sanitizer_calls
outer_mutation_status=$(cat "$result_dir/outer-mutation-tainted.status")
outer_mutation_path=$outer_path
outer_mutation_fake_inner_command=no
outer_mutation_caller_env_sanitizer_calls=$outer_sanitizer_calls
configured_authority_path=$configured_authority_path
configured_authority_fake_inner_command=yes
configured_authority_caller_env_sanitizer_calls=0
empty_dpkg_path_status=$empty_status
empty_dpkg_path_failed_closed=yes
empty_dpkg_path_maintainer_script_ran=no
candidate_mutation_package_sets_equal=yes
interpretation=apt-managed run_install requires absolute sanitizer authority and configured inner DPkg::Path while honoring explicit non-empty apt configuration; lossless argv receipts retain caller-path version, setup-hook, sanitizer, and other host calls without confusing host hooks with the governed dpkg sanitizer
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap apt-managed chrootless authority transaction passed'
