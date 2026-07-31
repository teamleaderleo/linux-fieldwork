#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/direct-authority-results"
argv_classifier="$repo_root/tools/classify_env_argv.py"

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
[[ -f "$argv_classifier" ]] || {
  echo "missing env argv classifier: $argv_classifier" >&2
  exit 2
}

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

write_dpkg_wrapper() {
  local record_dir=$1
  cat >"$runtime/fake-bin/dpkg" <<EOF
#!/bin/sh
set -eu
umask 077
record_dir="$record_dir"
record="\$record_dir/argv.\$\$"
set -C
exec 9>"\$record"
set +C
printf '%s\0' "\$@" >&9
exec 9>&-
exec /usr/bin/dpkg "\$@"
EOF
  chmod 0755 "$runtime/fake-bin/dpkg"
}

classify_outer_env() {
  local label=$1
  python3 "$argv_classifier" "$result_dir/$label-outer-env" \
    --output "$result_dir/$label-outer-env.json" \
    >"$result_dir/$label-outer-env.stdout" \
    2>"$result_dir/$label-outer-env.stderr"
}

summarize_dpkg_argv() {
  local label=$1
  python3 - \
    "$repo_root" \
    "$result_dir/$label-dpkg-argv" \
    "$result_dir/$label-dpkg-argv.json" <<'PY'
import json
import pathlib
import sys

repo_root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(repo_root))
from tools.classify_env_argv import iter_record_paths, read_argv_record

record_dir = pathlib.Path(sys.argv[2])
output = pathlib.Path(sys.argv[3])
records = [
    {"path": str(path), "argv": list(read_argv_record(path))}
    for path in iter_record_paths((record_dir,))
]
payload = {
    "schema_version": 1,
    "files_checked": len(records),
    "records": records,
}
output.write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(payload, sort_keys=True))
PY
}

require_direct_receipt() {
  local label=$1 expected_env_sanitizer=$2 expected_dpkg_chrootless=$3
  python3 - \
    "$result_dir/$label-outer-env.json" \
    "$result_dir/$label-dpkg-argv.json" \
    "$result_dir/$label-direct-receipt.json" \
    "$expected_env_sanitizer" \
    "$expected_dpkg_chrootless" <<'PY'
import json
import pathlib
import sys

env_path = pathlib.Path(sys.argv[1])
dpkg_path = pathlib.Path(sys.argv[2])
output_path = pathlib.Path(sys.argv[3])
expected_env_sanitizer = sys.argv[4]
expected_dpkg_chrootless = sys.argv[5]
env_payload = json.loads(env_path.read_text(encoding="utf-8"))
dpkg_payload = json.loads(dpkg_path.read_text(encoding="utf-8"))

if type(env_payload) is not dict or env_payload.get("schema_version") != 1:
    raise SystemExit(f"invalid env receipt schema: {env_path}")
counts = env_payload.get("counts")
required_classes = (
    "host-version-probe",
    "host-shell-hook",
    "sanitizer-dpkg",
    "other-host",
)
if type(counts) is not dict:
    raise SystemExit(f"env receipt counts are missing: {env_path}")
for name in required_classes:
    value = counts.get(name)
    if type(value) is not int or value < 0:
        raise SystemExit(f"invalid {name} count in {env_path}: {value!r}")
files_checked = env_payload.get("files_checked")
if type(files_checked) is not int or files_checked < 0:
    raise SystemExit(f"invalid env files_checked in {env_path}")
if sum(counts[name] for name in required_classes) != files_checked:
    raise SystemExit(f"env receipt count total mismatch: {env_path}")
if counts["host-version-probe"] < 1:
    raise SystemExit(f"caller-path env version probe was not observed: {env_path}")
if counts["host-shell-hook"] != 0:
    raise SystemExit(f"unexpected direct-path setup-hook env call: {env_path}")

sanitizer_count = counts["sanitizer-dpkg"]
if expected_env_sanitizer == "absent":
    if sanitizer_count != 0:
        raise SystemExit(
            f"caller-path dpkg sanitizer unexpectedly executed {sanitizer_count} time(s): {env_path}"
        )
elif expected_env_sanitizer == "present":
    if sanitizer_count < 1:
        raise SystemExit(f"caller-path dpkg sanitizer was not observed: {env_path}")
else:
    raise SystemExit(f"invalid env sanitizer expectation: {expected_env_sanitizer}")

if type(dpkg_payload) is not dict or dpkg_payload.get("schema_version") != 1:
    raise SystemExit(f"invalid dpkg receipt schema: {dpkg_path}")
dpkg_records = dpkg_payload.get("records")
dpkg_files = dpkg_payload.get("files_checked")
if type(dpkg_records) is not list or type(dpkg_files) is not int:
    raise SystemExit(f"invalid dpkg receipt inventory: {dpkg_path}")
if len(dpkg_records) != dpkg_files:
    raise SystemExit(f"dpkg receipt count mismatch: {dpkg_path}")
argv_vectors = []
for index, record in enumerate(dpkg_records):
    if type(record) is not dict or type(record.get("argv")) is not list:
        raise SystemExit(f"invalid dpkg argv record {index}: {dpkg_path}")
    argv = record["argv"]
    if not all(type(value) is str for value in argv):
        raise SystemExit(f"non-string dpkg argv record {index}: {dpkg_path}")
    argv_vectors.append(argv)

print_architecture_count = sum(
    argv == ["--print-architecture"] for argv in argv_vectors
)
chrootless_count = sum(
    "--force-script-chrootless" in argv for argv in argv_vectors
)
if print_architecture_count < 1:
    raise SystemExit(f"caller-path dpkg architecture probe was not observed: {dpkg_path}")
if expected_dpkg_chrootless == "absent":
    if chrootless_count != 0:
        raise SystemExit(
            f"caller-path dpkg unexpectedly received chrootless argv {chrootless_count} time(s): {dpkg_path}"
        )
elif expected_dpkg_chrootless == "present":
    if chrootless_count < 1:
        raise SystemExit(f"caller-path dpkg chrootless argv was not observed: {dpkg_path}")
else:
    raise SystemExit(
        f"invalid dpkg chrootless expectation: {expected_dpkg_chrootless}"
    )

summary = {
    "schema_version": 1,
    "env": {
        "host-version-probe": counts["host-version-probe"],
        "host-shell-hook": counts["host-shell-hook"],
        "sanitizer-dpkg": counts["sanitizer-dpkg"],
        "other-host": counts["other-host"],
    },
    "dpkg": {
        "files_checked": dpkg_files,
        "print-architecture": print_architecture_count,
        "force-script-chrootless": chrootless_count,
    },
}
output_path.write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(summary, sort_keys=True))
PY
}

receipt_count() {
  local summary=$1 section=$2 name=$3
  python3 - "$summary" "$section" "$name" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
value = payload[sys.argv[2]][sys.argv[3]]
if type(value) is not int or value < 0:
    raise SystemExit("invalid direct receipt count")
print(value)
PY
}

run_case() {
  local label=$1
  local mmdebstrap_path=$2
  local target="$runtime/$label-root"
  local dpkg_dir="$result_dir/$label-dpkg-argv"
  local outer_dir="$result_dir/$label-outer-env"
  local source_spec="deb [trusted=yes] copy://$repository test main"
  local status

  rm -rf "$dpkg_dir" "$outer_dir"
  mkdir -p "$dpkg_dir" "$outer_dir"
  write_dpkg_wrapper "$dpkg_dir"

  set +e
  timeout 300 /usr/bin/env -i \
    PATH="$runtime/fake-bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    OUTER_ENV_LOG_DIR="$outer_dir" \
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
  classify_outer_env "$label"
  summarize_dpkg_argv "$label" \
    >"$result_dir/$label-dpkg-argv.stdout" \
    2>"$result_dir/$label-dpkg-argv.stderr"

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
}

run_case candidate "$candidate"
run_case inner-mutation "$inner_mutation"
run_case outer-mutation "$outer_mutation"

require_direct_receipt candidate absent absent
require_direct_receipt inner-mutation absent present
require_direct_receipt outer-mutation present absent

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

candidate_env_version="$(receipt_count "$result_dir/candidate-direct-receipt.json" env host-version-probe)"
candidate_env_sanitizer="$(receipt_count "$result_dir/candidate-direct-receipt.json" env sanitizer-dpkg)"
candidate_dpkg_arch="$(receipt_count "$result_dir/candidate-direct-receipt.json" dpkg print-architecture)"
candidate_dpkg_chrootless="$(receipt_count "$result_dir/candidate-direct-receipt.json" dpkg force-script-chrootless)"
inner_env_sanitizer="$(receipt_count "$result_dir/inner-mutation-direct-receipt.json" env sanitizer-dpkg)"
inner_dpkg_chrootless="$(receipt_count "$result_dir/inner-mutation-direct-receipt.json" dpkg force-script-chrootless)"
outer_env_sanitizer="$(receipt_count "$result_dir/outer-mutation-direct-receipt.json" env sanitizer-dpkg)"
outer_dpkg_chrootless="$(receipt_count "$result_dir/outer-mutation-direct-receipt.json" dpkg force-script-chrootless)"

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
candidate_caller_env_version_calls=$candidate_env_version
candidate_caller_env_sanitizer_calls=$candidate_env_sanitizer
candidate_caller_dpkg_architecture_calls=$candidate_dpkg_arch
candidate_caller_dpkg_chrootless_calls=$candidate_dpkg_chrootless
inner_mutation_transaction_status=$(cat "$result_dir/inner-mutation.status")
inner_mutation_maintainer_script_path=$inner_path
inner_mutation_caller_env_sanitizer_calls=$inner_env_sanitizer
inner_mutation_caller_dpkg_chrootless_calls=$inner_dpkg_chrootless
outer_mutation_transaction_status=$(cat "$result_dir/outer-mutation.status")
outer_mutation_maintainer_script_path=$outer_path
outer_mutation_caller_env_sanitizer_calls=$outer_env_sanitizer
outer_mutation_caller_dpkg_chrootless_calls=$outer_dpkg_chrootless
candidate_mutation_package_sets_equal=yes
interpretation=direct run_essential requires both absolute sanitizer authority and configured inner DPkg::Path; lossless argv receipts prove exact caller-path env and dpkg argument vectors without flattening boundaries
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap direct chrootless authority transaction passed'
