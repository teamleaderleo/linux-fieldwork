#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/wrapper-results"

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
    echo 'usage: trusted_env_wrapper_probe.sh --check-runtime-parent PATH' >&2
    exit 2
  fi
  validate_runtime_parent "$2" >/dev/null
  exit
fi

runtime_parent="$(validate_runtime_parent "${RUNNER_TEMP:-/tmp}")"
runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-trusted-env")"
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

outer_mutation="$runtime/mmdebstrap-bare-env-mutation"
missing_mutation="$runtime/mmdebstrap-missing-env-mutation"
python3 - "$candidate" "$outer_mutation" "$missing_mutation" "$runtime/missing-env" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
direct_old = "                    chrootless_env_path(),\n"
direct_new = "                    'env',\n"
apt_old = "                '-oDir::Bin::dpkg=' . chrootless_env_path(),\n"
apt_new = "                '-oDir::Bin::dpkg=env',\n"
envpath_old = "    my $envpath = '/usr/bin/env';\n"
envpath_new = f"    my $envpath = '{sys.argv[4]}';\n"
for marker in (direct_old, apt_old, envpath_old):
    if source.count(marker) != 1:
        raise SystemExit(f"source marker not found exactly once: {marker!r}")
outer = source.replace(direct_old, direct_new).replace(apt_old, apt_new)
missing = source.replace(envpath_old, envpath_new)
Path(sys.argv[2]).write_text(outer, encoding="utf-8")
Path(sys.argv[3]).write_text(missing, encoding="utf-8")
PY
chmod 0755 "$outer_mutation" "$missing_mutation"

grep -F "my \$envpath = '/usr/bin/env';" "$candidate"
grep -F "'-oDir::Bin::dpkg=' . chrootless_env_path()" "$candidate"
if grep -F "'-oDir::Bin::dpkg=env'" "$candidate"; then
  echo 'candidate still uses caller-resolved apt env wrapper' >&2
  exit 1
fi

cat >"$runtime/fake-bin/env" <<'PY'
#!/usr/bin/python3
import os
import pathlib
import sys

log = pathlib.Path(os.environ["LF_WRAPPER_LOG"])
with log.open("a", encoding="utf-8") as handle:
    handle.write("argv=" + "\x1f".join(sys.argv[1:]) + "\n")
    handle.write("inherited_path=" + os.environ.get("PATH", "") + "\n")
args = []
for arg in sys.argv[1:]:
    if arg.startswith("PATH="):
        args.append("PATH=" + os.environ.get("PATH", ""))
    else:
        args.append(arg)
os.execv("/usr/bin/env", ["/usr/bin/env", *args])
PY
chmod 0755 "$runtime/fake-bin/env"

cat >"$runtime/fake-bin/dpkg" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >>"$LF_DPKG_LOG"
exec /usr/bin/dpkg "$@"
EOF
chmod 0755 "$runtime/fake-bin/dpkg"

build_package() {
  local fixture=$1 package=$2 package_name=$3 essential=$4
  mkdir -p "$fixture/DEBIAN" "$fixture/usr/share/$package_name"
  cat >"$fixture/DEBIAN/control" <<EOF
Package: $package_name
Version: 1.0
Section: misc
Priority: optional
Architecture: all
Essential: $essential
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: trusted env wrapper probe
 A local-only package for testing the outer chrootless sanitizer boundary.
EOF
  cat >"$fixture/DEBIAN/postinst" <<EOF
#!/bin/sh
set -eu
result_dir="\$DPKG_ROOT/var/lib/$package_name"
mkdir -p "\$result_dir"
printf '%s\n' "\$PATH" >"\$result_dir/path.txt"
printf 'postinst-ran=yes\n' >"\$result_dir/result.txt"
EOF
  chmod 0755 "$fixture/DEBIAN/postinst"
  printf 'fixture payload\n' >"$fixture/usr/share/$package_name/payload"
  dpkg-deb --build --root-owner-group "$fixture" "$package" >/dev/null
}

apt_package="$runtime/lf-env-wrapper-apt-probe_1.0_all.deb"
build_package \
  "$runtime/apt-fixture" \
  "$apt_package" \
  lf-env-wrapper-apt-probe \
  no

direct_fixture="$runtime/direct-fixture"
repository="$runtime/repository"
pool="$repository/pool/main/l/lf-env-wrapper-direct-probe"
arch="$(dpkg --print-architecture)"
binary_dir="$repository/dists/test/main/binary-$arch"
mkdir -p "$pool" "$binary_dir"
direct_package="$pool/lf-env-wrapper-direct-probe_1.0_all.deb"
build_package \
  "$direct_fixture" \
  "$direct_package" \
  lf-env-wrapper-direct-probe \
  yes
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

system_path=/usr/sbin:/usr/bin:/sbin:/bin
tainted_path="$runtime/fake-bin:$system_path"

run_apt_case() {
  local label=$1 mmdebstrap_path=$2
  local target="$runtime/$label-root"
  local wrapper_log="$result_dir/$label-env.log"
  local dpkg_log="$result_dir/$label-dpkg.log"
  local package_dir hook
  package_dir="$(dirname "$apt_package")"
  printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' \
    "$package_dir" "$apt_package" "$apt_package"
  : >"$wrapper_log"
  : >"$dpkg_log"
  env -i \
    PATH="$tainted_path" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    LF_WRAPPER_LOG="$wrapper_log" \
    LF_DPKG_LOG="$dpkg_log" \
    "$mmdebstrap_path" \
      --mode=chrootless \
      --variant=custom \
      --format=directory \
      --skip=update \
      --include="$apt_package" \
      --setup-hook="$hook" \
      '' "$target" \
      >"$result_dir/$label.stdout" \
      2>"$result_dir/$label.stderr"
  grep -Fx 'postinst-ran=yes' \
    "$target/var/lib/lf-env-wrapper-apt-probe/result.txt"
  cp -a "$target/var/lib/lf-env-wrapper-apt-probe" \
    "$result_dir/$label-maintainer-script"
}

run_direct_case() {
  local label=$1 mmdebstrap_path=$2
  local target="$runtime/$label-root"
  local wrapper_log="$result_dir/$label-env.log"
  local dpkg_log="$result_dir/$label-dpkg.log"
  local source_spec="deb [trusted=yes] copy://$repository test main"
  : >"$wrapper_log"
  : >"$dpkg_log"
  timeout 300 env -i \
    PATH="$tainted_path" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    LF_WRAPPER_LOG="$wrapper_log" \
    LF_DPKG_LOG="$dpkg_log" \
    "$mmdebstrap_path" \
      --mode=chrootless \
      --variant=essential \
      --format=directory \
      test "$target" "$source_spec" \
      >"$result_dir/$label.stdout" \
      2>"$result_dir/$label.stderr"
  grep -Fx 'postinst-ran=yes' \
    "$target/var/lib/lf-env-wrapper-direct-probe/result.txt"
  cp -a "$target/var/lib/lf-env-wrapper-direct-probe" \
    "$result_dir/$label-maintainer-script"
}

run_apt_case apt-candidate "$candidate"
test ! -s "$result_dir/apt-candidate-env.log"
if grep -F -- '--force-script-chrootless' "$result_dir/apt-candidate-dpkg.log"; then
  echo 'apt candidate used caller dpkg wrapper' >&2
  exit 1
fi
apt_candidate_path="$(cat "$result_dir/apt-candidate-maintainer-script/path.txt")"
[[ "$apt_candidate_path" == "$system_path" ]]

run_apt_case apt-outer-mutation "$outer_mutation"
test -s "$result_dir/apt-outer-mutation-env.log"
grep -F -- '--force-script-chrootless' "$result_dir/apt-outer-mutation-dpkg.log"
apt_mutation_path="$(cat "$result_dir/apt-outer-mutation-maintainer-script/path.txt")"
[[ "$apt_mutation_path" == "$runtime/fake-bin:"* ]]

run_direct_case direct-candidate "$candidate"
test ! -s "$result_dir/direct-candidate-env.log"
if grep -F -- '--force-script-chrootless' "$result_dir/direct-candidate-dpkg.log"; then
  echo 'direct candidate used caller dpkg wrapper' >&2
  exit 1
fi
direct_candidate_path="$(cat "$result_dir/direct-candidate-maintainer-script/path.txt")"
[[ "$direct_candidate_path" == "$system_path" ]]

run_direct_case direct-outer-mutation "$outer_mutation"
test -s "$result_dir/direct-outer-mutation-env.log"
grep -F -- '--force-script-chrootless' "$result_dir/direct-outer-mutation-dpkg.log"
direct_mutation_path="$(cat "$result_dir/direct-outer-mutation-maintainer-script/path.txt")"
[[ "$direct_mutation_path" == "$runtime/fake-bin:"* ]]

missing_target="$runtime/missing-wrapper-root"
missing_package_dir="$(dirname "$apt_package")"
printf -v missing_hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' \
  "$missing_package_dir" "$apt_package" "$apt_package"
set +e
env -i \
  PATH="$system_path" \
  HOME="$runtime/home" \
  TMPDIR="$runtime" \
  LC_ALL=C.UTF-8 \
  "$missing_mutation" \
    --mode=chrootless \
    --variant=custom \
    --format=directory \
    --skip=update \
    --include="$apt_package" \
    --setup-hook="$missing_hook" \
    '' "$missing_target" \
    >"$result_dir/missing-wrapper.stdout" \
    2>"$result_dir/missing-wrapper.stderr"
missing_status=$?
set -e
[[ "$missing_status" -ne 0 ]]
grep -F 'cannot execute trusted environment wrapper:' \
  "$result_dir/missing-wrapper.stderr"
test ! -f "$missing_target/var/lib/lf-env-wrapper-apt-probe/result.txt"

source_mode_after="$(stat -c '%a' "$source_root/mmdebstrap")"
[[ "$source_mode_after" == "$source_mode_before" ]]
git diff --exit-code -- upstream/mmdebstrap/mmdebstrap

cat >"$result_dir/summary.txt" <<EOF
product_source=upstream/mmdebstrap/mmdebstrap
trusted_wrapper=/usr/bin/env
repository_source_unchanged=yes
apt_candidate_fake_env_executed=no
apt_candidate_maintainer_script_path=$apt_candidate_path
apt_outer_mutation_fake_env_executed=yes
apt_outer_mutation_maintainer_script_path=$apt_mutation_path
direct_candidate_fake_env_executed=no
direct_candidate_maintainer_script_path=$direct_candidate_path
direct_outer_mutation_fake_env_executed=yes
direct_outer_mutation_maintainer_script_path=$direct_mutation_path
missing_wrapper_status=$missing_status
missing_wrapper_failed_closed=yes
interpretation=absolute trusted env wrapper closes the caller PATH boundary before environment sanitization
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap trusted env wrapper boundary probe passed'
