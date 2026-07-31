#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/apt-authority-results"
env_classifier="$repo_root/investigations/mmdebstrap-chrootless-env/classify_env_invocations.py"

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
  [[ $# -eq 2 ]] || {
    echo 'usage: apt_authority_transaction.sh --check-runtime-parent PATH' >&2
    exit 2
  }
  validate_runtime_parent "$2" >/dev/null
  exit
fi

runtime_parent="$(validate_runtime_parent "${RUNNER_TEMP:-/tmp}")"
runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-apt-authority")"
[[ "$runtime" != "$runtime_parent" ]] || {
  echo "refusing runtime equal to parent: $runtime" >&2
  exit 2
}
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
[[ -f "$env_classifier" ]] || {
  echo "missing env invocation classifier: $env_classifier" >&2
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
: "${OUTER_ENV_LOG:?}"
/usr/bin/python3 -c '
import json
import os
import sys

payload = (
    json.dumps(sys.argv[2:], ensure_ascii=True, separators=(",", ":")) + "\n"
).encode("utf-8")
fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
try:
    os.write(fd, payload)
finally:
    os.close(fd)
' "$OUTER_ENV_LOG" "$@"
exec /usr/bin/env "$@"
EOF
chmod 0755 "$runtime/fake-bin/env"

classify_env_invocations() {
  local log_file=$1
  local expectation=$2
  local summary_file="${log_file%.log}.classification.json"
  python3 "$env_classifier" \
    "$log_file" \
    --governed-dpkg "$expectation" \
    --summary "$summary_file" \
    >"$summary_file.stdout"
}

assert_version_probe_only() {
  local log_file=$1
  grep -Fx -- '["--version"]' "$log_file" >/dev/null
  classify_env_invocations "$log_file" forbid
}

assert_version_probe_and_sanitizer() {
  local log_file=$1
  grep -Fx -- '["--version"]' "$log_file" >/dev/null
  classify_env_invocations "$log_file" require
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
  local outer_log="$result_dir/$label-outer-env.log"
  local hook
  local status
  local -a launch_env=(
    /usr/bin/env -i
    PATH="$path_value"
    HOME="$runtime/home"
    TMPDIR="$runtime"
    LC_ALL=C.UTF-8
    OUTER_ENV_LOG="$outer_log"
  )
  hook="$(make_hook)"
  : >"$outer_log"
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

assert_version_probe_only "$result_dir/candidate-tainted-outer-env.log"
# The clean case has no fake env in PATH, so the log is intentionally empty.
[[ ! -s "$result_dir/candidate-clean-outer-env.log" ]]
assert_version_probe_only "$result_dir/inner-mutation-tainted-outer-env.log"
assert_version_probe_and_sanitizer \
  "$result_dir/outer-mutation-tainted-outer-env.log"

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
[[ ! -s "$result_dir/configured-authority-outer-env.log" ]]

empty_config="$runtime/apt-empty-dpkg-path.conf"
printf 'DPkg::Path "";\n' >"$empty_config"
empty_target="$runtime/empty-dpkg-path-root"
empty_hook="$(make_hook)"
: >"$result_dir/empty-dpkg-path-outer-env.log"
set +e
timeout 300 /usr/bin/env -i \
  PATH="$system_path" \
  HOME="$runtime/home" \
  TMPDIR="$runtime" \
  LC_ALL=C.UTF-8 \
  OUTER_ENV_LOG="$result_dir/empty-dpkg-path-outer-env.log" \
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
[[ "$empty_status" -ne 0 ]]
[[ "$empty_status" -ne 124 ]]
grep -F 'cannot determine chrootless maintainer-script PATH' \
  "$result_dir/empty-dpkg-path.stderr"
test ! -f "$empty_target/var/lib/lf-apt-authority-probe/result.txt"
[[ ! -s "$result_dir/empty-dpkg-path-outer-env.log" ]]

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

cat >"$result_dir/summary.txt" <<EOF
product_source=upstream/mmdebstrap/mmdebstrap
executed_candidate_copy=$candidate
source_mode_before=$source_mode_before
source_mode_after=$source_mode_after
repository_source_unchanged=yes
candidate_tainted_status=$(cat "$result_dir/candidate-tainted.status")
candidate_tainted_path=$candidate_tainted_path
candidate_tainted_fake_inner_command=no
candidate_tainted_caller_env_receipt=lossless-jsonl
candidate_tainted_caller_env_host_probe=present
candidate_tainted_caller_env_sanitizer_launch=no
candidate_clean_status=$(cat "$result_dir/candidate-clean.status")
candidate_clean_path=$candidate_clean_path
inner_mutation_status=$(cat "$result_dir/inner-mutation-tainted.status")
inner_mutation_path=$inner_path
inner_mutation_fake_inner_command=yes
inner_mutation_caller_env_receipt=lossless-jsonl
inner_mutation_caller_env_host_probe=present
inner_mutation_caller_env_sanitizer_launch=no
outer_mutation_status=$(cat "$result_dir/outer-mutation-tainted.status")
outer_mutation_path=$outer_path
outer_mutation_fake_inner_command=no
outer_mutation_caller_env_receipt=lossless-jsonl
outer_mutation_caller_env_host_probe=present
outer_mutation_caller_env_sanitizer_launch=yes
configured_authority_path=$configured_authority_path
configured_authority_fake_inner_command=yes
configured_authority_caller_env_sanitizer_launch=no
empty_dpkg_path_status=$empty_status
empty_dpkg_path_failed_closed=yes
empty_dpkg_path_maintainer_script_ran=no
candidate_mutation_package_sets_equal=yes
interpretation=apt-managed run_install requires absolute sanitizer authority and configured inner DPkg::Path while honoring explicit non-empty apt configuration; non-governed caller-PATH env invocations remain explicit in per-case classification receipts and outside this patch boundary
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap apt-managed chrootless authority transaction passed'
