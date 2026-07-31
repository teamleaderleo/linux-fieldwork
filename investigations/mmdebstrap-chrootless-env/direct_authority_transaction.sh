#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/direct-authority-results"

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
    echo 'usage: direct_authority_transaction.sh --check-runtime-parent PATH' >&2
    exit 2
  }
  validate_runtime_parent "$2" >/dev/null
  exit
fi

runtime_parent="$(validate_runtime_parent "${RUNNER_TEMP:-/tmp}")"
runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-direct-authority")"
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
  apt-ftparchive \
  cp \
  dpkg \
  dpkg-deb \
  dpkg-query \
  gzip \
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

rm -rf "$runtime" "$result_dir"
mkdir -p "$runtime/fake-bin" "$runtime/home" "$result_dir"
source_mode_before="$(stat -c '%a' "$source_root/mmdebstrap")"

prepared="$runtime/prepared"
python3 \
  "$repo_root/investigations/mmdebstrap-chrootless-env/prepare_authority_candidates.py" \
  "$prepared" --json >"$result_dir/prepared.json"
candidate="$prepared/candidate-tree/upstream/mmdebstrap/mmdebstrap"
inner_mutation="$prepared/mmdebstrap-inner-path-mutation"
outer_mutation="$prepared/mmdebstrap-outer-env-mutation"

arch="$(dpkg --print-architecture)"
fixture="$runtime/fixture"
repository="$runtime/repository"
pool="$repository/pool/main/l/lf-essential-authority-probe"
binary_dir="$repository/dists/test/main/binary-$arch"
mkdir -p "$fixture/DEBIAN" "$fixture/usr/share/lf-essential-authority-probe"
mkdir -p "$pool" "$binary_dir"

cat >"$fixture/DEBIAN/control" <<'EOF'
Package: lf-essential-authority-probe
Version: 1.0
Section: misc
Priority: required
Architecture: all
Essential: yes
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: direct chrootless executable authority probe
 A local Essential package for exercising mmdebstrap run_essential.
EOF

cat >"$fixture/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu

result_dir="$DPKG_ROOT/var/lib/lf-essential-authority-probe"
mkdir -p "$result_dir"
printf '%s\n' "$PATH" >"$result_dir/path.txt"
printf 'postinst-ran=yes\n' >"$result_dir/result.txt"
EOF
chmod 0755 "$fixture/DEBIAN/postinst"
printf 'fixture payload\n' >"$fixture/usr/share/lf-essential-authority-probe/payload"
package="$pool/lf-essential-authority-probe_1.0_all.deb"
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

cat >"$runtime/fake-bin/env" <<'EOF'
#!/bin/sh
set -eu
: "${OUTER_ENV_LOG:?}"
printf '%s\n' "$*" >>"$OUTER_ENV_LOG"
exec /usr/bin/env "$@"
EOF
chmod 0755 "$runtime/fake-bin/env"

write_dpkg_wrapper() {
  local log_file=$1
  cat >"$runtime/fake-bin/dpkg" <<EOF
#!/bin/sh
set -eu
printf '%s\n' "\$*" >>"$log_file"
exec /usr/bin/dpkg "\$@"
EOF
  chmod 0755 "$runtime/fake-bin/dpkg"
}

assert_version_probe_only() {
  local log_file=$1
  grep -Fx -- '--version' "$log_file" >/dev/null
  if grep -F -- '-i PATH=' "$log_file" >/dev/null; then
    echo "unexpected chrootless sanitizer launch through caller PATH: $log_file" >&2
    return 1
  fi
  if grep -vFx -- '--version' "$log_file" | grep -q .; then
    echo "unexpected caller-path env invocation: $log_file" >&2
    return 1
  fi
}

assert_version_probe_and_sanitizer() {
  local log_file=$1
  grep -Fx -- '--version' "$log_file" >/dev/null
  grep -F -- '-i PATH=' "$log_file" >/dev/null
  if grep -vFx -- '--version' "$log_file" \
    | grep -vF -- '-i PATH=' \
    | grep -q .; then
    echo "unexpected caller-path env invocation class: $log_file" >&2
    return 1
  fi
}

run_case() {
  local label=$1
  local mmdebstrap_path=$2
  local target="$runtime/$label-root"
  local dpkg_log="$result_dir/$label-dpkg-wrapper.log"
  local outer_log="$result_dir/$label-outer-env.log"
  local source_spec="deb [trusted=yes] copy://$repository test main"
  local status

  : >"$dpkg_log"
  : >"$outer_log"
  write_dpkg_wrapper "$dpkg_log"

  set +e
  timeout 300 /usr/bin/env -i \
    PATH="$runtime/fake-bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    OUTER_ENV_LOG="$outer_log" \
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

  [[ "$status" -ne 124 ]] || {
    echo "$label transaction timed out" >&2
    exit 1
  }
  [[ "$status" -eq 0 ]]
  grep -F 'I: installing essential packages...' "$result_dir/$label.stderr"
  test -f "$target/usr/share/lf-essential-authority-probe/payload"
  grep -Fx 'postinst-ran=yes' \
    "$target/var/lib/lf-essential-authority-probe/result.txt"
  cp -a "$target/var/lib/lf-essential-authority-probe" \
    "$result_dir/$label-maintainer-script"
  dpkg-query --admindir="$target/var/lib/dpkg" \
    -W -f='${binary:Package}\n' \
    | sort >"$result_dir/$label-packages.txt"
  grep -Fx lf-essential-authority-probe "$result_dir/$label-packages.txt"
  grep -Fx -- '--print-architecture' "$dpkg_log"
}

run_case candidate "$candidate"
run_case inner-mutation "$inner_mutation"
run_case outer-mutation "$outer_mutation"

for label in candidate outer-mutation; do
  if grep -F -- '--force-script-chrootless' \
    "$result_dir/$label-dpkg-wrapper.log"; then
    echo "$label direct chrootless dpkg used caller PATH" >&2
    exit 1
  fi
done
grep -F -- '--force-script-chrootless' \
  "$result_dir/inner-mutation-dpkg-wrapper.log"

assert_version_probe_only "$result_dir/candidate-outer-env.log"
assert_version_probe_only "$result_dir/inner-mutation-outer-env.log"
assert_version_probe_and_sanitizer "$result_dir/outer-mutation-outer-env.log"

canonical_path=/usr/sbin:/usr/bin:/sbin:/bin
candidate_path="$(cat "$result_dir/candidate-maintainer-script/path.txt")"
inner_path="$(cat "$result_dir/inner-mutation-maintainer-script/path.txt")"
outer_path="$(cat "$result_dir/outer-mutation-maintainer-script/path.txt")"
[[ "$candidate_path" == "$canonical_path" ]]
[[ "$outer_path" == "$canonical_path" ]]
[[ "$inner_path" == "$runtime/fake-bin:"* ]]

cmp "$result_dir/candidate-packages.txt" \
  "$result_dir/inner-mutation-packages.txt"
cmp "$result_dir/candidate-packages.txt" \
  "$result_dir/outer-mutation-packages.txt"

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
candidate_transaction_status=$(cat "$result_dir/candidate.status")
candidate_direct_run_essential_reached=yes
candidate_maintainer_script_path=$candidate_path
candidate_caller_dpkg_received_chrootless_args=no
candidate_caller_env_host_probe=version-only
candidate_caller_env_sanitizer_launch=no
inner_mutation_transaction_status=$(cat "$result_dir/inner-mutation.status")
inner_mutation_maintainer_script_path=$inner_path
inner_mutation_caller_dpkg_received_chrootless_args=yes
inner_mutation_caller_env_host_probe=version-only
inner_mutation_caller_env_sanitizer_launch=no
outer_mutation_transaction_status=$(cat "$result_dir/outer-mutation.status")
outer_mutation_maintainer_script_path=$outer_path
outer_mutation_caller_dpkg_received_chrootless_args=no
outer_mutation_caller_env_host_probe=version-only
outer_mutation_caller_env_sanitizer_launch=yes
candidate_mutation_package_sets_equal=yes
interpretation=direct run_essential requires both absolute sanitizer authority and configured inner DPkg::Path; host dependency probes remain caller-PATH based and outside this patch boundary
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap direct chrootless authority transaction passed'
