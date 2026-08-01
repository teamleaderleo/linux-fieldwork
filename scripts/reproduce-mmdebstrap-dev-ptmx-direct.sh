#!/usr/bin/env bash
# Run only mmdebstrap's dev-ptmx root/apt case against current Debian sid.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
imported_source="$repo_root/upstream/mmdebstrap"
candidate_patch="$repo_root/investigations/mmdebstrap-dev-ptmx-bsdutils/dev-ptmx-bsdutils-source.patch"
run_id=${RUN_ID:-"local-$(date -u +%Y%m%dT%H%M%SZ)"}
run_dir=${RUN_DIR:-"$repo_root/investigations/mmdebstrap-dev-ptmx-bsdutils/runs/$run_id"}
mirror=${MMDEBSTRAP_MIRROR:-https://deb.debian.org/debian}
dist=${MMDEBSTRAP_DIST:-unstable}
mkdir -p "$run_dir"

finish_early() {
  local status=$1
  shift
  local reason=$*
  printf '%s\n' "$reason" >&2
  printf '%s\n' "$status" >"$run_dir/exit-status"
  printf '%s\n' "$reason" >"$run_dir/preflight-error.txt"
  {
    printf '# Direct dev-ptmx result\n\n'
    printf -- '- Exit status: `%s`\n' "$status"
    printf -- '- Classification: `carrier-preflight-failure`\n'
    printf -- '- Reason: `%s`\n' "$reason"
  } >"$run_dir/result.md"
  exit "$status"
}

if [[ $(id -u) -ne 0 ]]; then
  finish_early 77 "direct dev-ptmx reproduction requires root in a disposable container"
fi
for command in curl findmnt mmdebstrap patch pgrep python3 shellcheck shfmt sudo script; do
  command -v "$command" >/dev/null 2>&1 || finish_early 77 "$command is unavailable"
done
[[ -f $imported_source/coverage.py ]] || finish_early 2 "imported coverage.py is missing"
[[ -f $imported_source/tests/dev-ptmx ]] || finish_early 2 "imported dev-ptmx test is missing"
[[ -f $candidate_patch ]] || finish_early 2 "unit-09 source patch is missing"

work_root=$(mktemp -d "${TMPDIR:-/tmp}/lf-unit09-direct.XXXXXXXX")
case "$work_root" in
  /|/tmp|/var/tmp)
    finish_early 2 "refusing unsafe temporary root: $work_root"
    ;;
esac
source_tree="$work_root/mmdebstrap"
cleanup_work_root() {
  rm -rf -- "$work_root"
}
trap cleanup_work_root EXIT INT TERM
cp -a "$imported_source" "$source_tree"
chmod 0755 "$source_tree/run_null.sh"

python3 - "$source_tree/tests/dev-ptmx" <<'PY' >"$run_dir/baseline-identity.txt"
import hashlib
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = path.read_bytes()
blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
text = data.decode()
assert blob == "ca1cde040f945fe871f904ef6a56e040b6a5c9ea", blob
assert "--include=gcc,libc6-dev,python3,passwd" in text
assert text.count("script -c") == 2
print(f"baseline_blob={blob}")
print("baseline_include=gcc,libc6-dev,python3,passwd")
print("inner_script_hooks=2")
PY

patch_stdout="$run_dir/candidate-patch.stdout"
patch_stderr="$run_dir/candidate-patch.stderr"
if ! patch --batch --forward --fuzz=0 -p1 -d "$source_tree" -i "$candidate_patch" \
    >"$patch_stdout" 2>"$patch_stderr"; then
  finish_early 2 "unit-09 patch failed exact application"
fi
if grep -Eiq '(^|[^[:alpha:]])(fuzz|offset)([^[:alpha:]]|$)' \
    "$patch_stdout" "$patch_stderr"; then
  finish_early 2 "unit-09 patch reported fuzz or offset"
fi

python3 - "$source_tree/tests/dev-ptmx" <<'PY' >"$run_dir/candidate-identity.txt"
import hashlib
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = path.read_bytes()
blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
text = data.decode()
assert blob == "fa93b4b845ff4927a72f258364bd920e8c7dc573", blob
assert "--include=bsdutils,gcc,libc6-dev,python3,passwd" in text
assert text.count("script -c") == 2
print(f"candidate_blob={blob}")
print("candidate_include=bsdutils,gcc,libc6-dev,python3,passwd")
print("inner_script_hooks=2")
PY

mkdir -p "$source_tree/shared/cache/debian/dists/$dist"
inrelease="$source_tree/shared/cache/debian/dists/$dist/InRelease"
curl --fail --location --silent --show-error \
  "$mirror/dists/$dist/InRelease" --output "$inrelease"

{
  printf '# Direct dev-ptmx provenance\n\n'
  printf -- '- Started: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Run ID: `%s`\n' "$run_id"
  printf -- '- Distribution: `%s`\n' "$dist"
  printf -- '- Mirror: `%s`\n' "$mirror"
  printf -- '- Command: `/usr/bin/mmdebstrap`\n'
  printf -- '- Selected case: `dev-ptmx --mode=root --variant=apt`\n'
  printf -- '- Imported baseline blob: `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`\n'
  printf -- '- Candidate blob: `fa93b4b845ff4927a72f258364bd920e8c7dc573`\n'
  printf -- '- Patch contract: `zero fuzz and zero offset`\n'
  printf '\n## Package versions\n\n```text\n'
  dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
    mmdebstrap apt bsdutils procps python3-debian shellcheck shfmt sudo util-linux 2>&1 || true
  printf '```\n\n## Input hashes\n\n```text\n'
  sha256sum "$candidate_patch" "$inrelease" "$source_tree/tests/dev-ptmx"
  printf '```\n'
} >"$run_dir/provenance.md"

command=(
  python3 ./coverage.py
  --exitfirst
  --mode=root
  --variant=apt
  dev-ptmx
)
printf '%q ' env \
  CMD=/usr/bin/mmdebstrap \
  DEFAULT_DIST="$dist" \
  mirror="$mirror" \
  HAVE_QEMU=no \
  HAVE_BINFMT=no \
  RUN_MA_SAME_TESTS=no \
  USE_HOST_APT_CONFIG=no \
  "${command[@]}" >"$run_dir/command.txt"
printf '\n' >>"$run_dir/command.txt"

set +e
(
  cd "$source_tree"
  env \
    CMD=/usr/bin/mmdebstrap \
    DEFAULT_DIST="$dist" \
    mirror="$mirror" \
    HAVE_QEMU=no \
    HAVE_BINFMT=no \
    RUN_MA_SAME_TESTS=no \
    USE_HOST_APT_CONFIG=no \
    "${command[@]}"
) >"$run_dir/coverage.stdout" 2>"$run_dir/coverage.stderr"
test_status=$?
set -e
printf '%s\n' "$test_status" >"$run_dir/test-exit-status"

if [[ -f $source_tree/shared/test.sh ]]; then
  cp "$source_tree/shared/test.sh" "$run_dir/rendered-test.sh"
fi
if [[ -f $source_tree/shared/output.txt ]]; then
  cp "$source_tree/shared/output.txt" "$run_dir/test-output.txt"
fi

cleanup_status=0
findmnt -rn -o TARGET | grep -F "$work_root" >"$run_dir/residual-mounts.txt" || true
if [[ -s $run_dir/residual-mounts.txt ]]; then
  cleanup_status=2
fi
for path in /tmp/test.c /tmp/log; do
  if [[ -e $path ]]; then
    printf '%s\n' "$path" >>"$run_dir/residual-files.txt"
    cleanup_status=2
  fi
done
pgrep -af '/usr/bin/mmdebstrap|/run_null.sh|/shared/test.sh' \
  >"$run_dir/residual-processes.txt" || true
if [[ -s $run_dir/residual-processes.txt ]]; then
  cleanup_status=2
fi
printf '%s\n' "$cleanup_status" >"$run_dir/cleanup-exit-status"

final_status=$test_status
if [[ $final_status -eq 0 && $cleanup_status -ne 0 ]]; then
  final_status=$cleanup_status
fi
printf '%s\n' "$final_status" >"$run_dir/exit-status"

{
  printf '# Direct dev-ptmx result\n\n'
  printf -- '- Finished: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Test exit status: `%s`\n' "$test_status"
  printf -- '- Cleanup exit status: `%s`\n' "$cleanup_status"
  printf -- '- Final exit status: `%s`\n' "$final_status"
  case "$final_status" in
    0) printf -- '- Classification: `pass`\n' ;;
    77) printf -- '- Classification: `neutral-or-skipped`\n' ;;
    *) printf -- '- Classification: `failure`\n' ;;
  esac
  if grep -q 'result: SUCCESS' "$run_dir/coverage.stderr"; then
    printf -- '- Named result: `dev-ptmx SUCCESS`\n'
  elif grep -q 'result: FAILURE' "$run_dir/coverage.stderr"; then
    printf -- '- Named result: `dev-ptmx FAILURE`\n'
  else
    printf -- '- Named result: `absent`\n'
  fi
  printf -- '- Residual mounts: `%s`\n' "$(wc -l <"$run_dir/residual-mounts.txt")"
  printf -- '- Residual files: `%s`\n' "$(test -f "$run_dir/residual-files.txt" && wc -l <"$run_dir/residual-files.txt" || printf 0)"
  printf -- '- Residual processes: `%s`\n' "$(wc -l <"$run_dir/residual-processes.txt")"
} >"$run_dir/result.md"

exit "$final_status"
