#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-unwritable-tmpdir/results"
runtime_leaf=linux-fieldwork-mmdebstrap-deep-review
source "$repo_root/investigations/mmdebstrap-unwritable-tmpdir/runtime_guard.sh"

if [[ ${1:-} == --check-runtime-parent ]]; then
  if [[ $# -ne 2 ]]; then
    echo "usage: $0 --check-runtime-parent PATH" >&2
    exit 2
  fi
  validate_disposable_runtime \
    "$repo_root" "${HOME:-/nonexistent-home}" "$2" "$runtime_leaf" \
    >/dev/null
  exit
fi

runtime_root="$(validate_disposable_runtime \
  "$repo_root" \
  "${HOME:-/nonexistent-home}" \
  "${RUNNER_TEMP:-/tmp}" \
  "$runtime_leaf")"
source_spec="deb [trusted=yes] https://deb.debian.org/debian sid main"

cleanup() {
  chmod -R u+w "$runtime_root" 2>/dev/null || true
  rm -rf "$runtime_root"
}

finish() {
  local primary_status=$1 cleanup_status=0
  trap - EXIT INT TERM
  cleanup || cleanup_status=$?
  if [[ $primary_status -ne 0 ]]; then
    exit "$primary_status"
  fi
  exit "$cleanup_status"
}

exit_cleanup() {
  finish "$?"
}

trap exit_cleanup EXIT
trap 'finish 130' INT
trap 'finish 143' TERM

rm -rf "$runtime_root"
mkdir -p "$runtime_root" "$result_dir"
chmod +x "$source_root/mmdebstrap"

run_mmdebstrap() {
  local log_file=$1
  shift
  set +e
  env -i \
    PATH=/usr/sbin:/usr/bin:/sbin:/bin \
    HOME="${HOME:-/tmp}" \
    LC_ALL=C.UTF-8 \
    timeout 240 "$@" \
    "$source_root/mmdebstrap" \
    --dry-run \
    --mode=chrootless \
    --variant=apt \
    sid \
    /dev/null \
    "$source_spec" \
    >"$log_file" 2>&1
  local status=$?
  set -e
  printf '%s\n' "$status"
}

selected_tmpdir() {
  sed -n 's/^I: using \(.*\) as tempdir$/\1/p' "$1" | head -n 1
}

assert_no_selected_tmpdir() {
  local log_file=$1
  local selected
  selected="$(selected_tmpdir "$log_file")"
  if [[ -n "$selected" ]]; then
    echo "unexpected temporary directory selection: $selected" >&2
    cat "$log_file" >&2
    exit 1
  fi
}

assert_failure_names_path() {
  local status=$1
  local log_file=$2
  local requested=$3
  if [[ "$status" -eq 0 ]]; then
    echo "expected failure for TMPDIR=$requested" >&2
    cat "$log_file" >&2
    exit 1
  fi
  assert_no_selected_tmpdir "$log_file"
  grep -F "$requested" "$log_file" >/dev/null
  grep -F 'Error in tempdir()' "$log_file" >/dev/null
}

# Normal library-selected path when TMPDIR is absent.
unset_log="$result_dir/deep-unset.log"
unset_status="$(run_mmdebstrap "$unset_log" env -u TMPDIR)"
unset_selected="$(selected_tmpdir "$unset_log")"
[[ "$unset_status" -eq 0 ]]
[[ "$unset_selected" == /tmp/mmdebstrap.* ]]

# Empty TMPDIR retains the pre-existing default behavior.
empty_log="$result_dir/deep-empty.log"
empty_status="$(run_mmdebstrap "$empty_log" env TMPDIR=)"
empty_selected="$(selected_tmpdir "$empty_log")"
[[ "$empty_status" -eq 0 ]]
[[ "$empty_selected" == /tmp/mmdebstrap.* ]]

# A writable explicit directory is honored and cleaned.
writable="$runtime_root/writable"
mkdir "$writable"
writable_log="$result_dir/deep-writable.log"
writable_status="$(run_mmdebstrap "$writable_log" env TMPDIR="$writable")"
writable_selected="$(selected_tmpdir "$writable_log")"
[[ "$writable_status" -eq 0 ]]
[[ "$writable_selected" == "$writable"/mmdebstrap.* ]]
if find "$writable" -mindepth 1 -print -quit | grep -q .; then
  echo "temporary content remained below writable TMPDIR" >&2
  find "$writable" -mindepth 1 -maxdepth 2 -print >&2
  exit 1
fi

# An existing but unwritable explicit directory fails at the real operation.
unwritable="$runtime_root/unwritable"
mkdir "$unwritable"
chmod 0555 "$unwritable"
unwritable_log="$result_dir/deep-unwritable.log"
unwritable_status="$(run_mmdebstrap "$unwritable_log" env TMPDIR="$unwritable")"
assert_failure_names_path "$unwritable_status" "$unwritable_log" "$unwritable"
grep -F 'Permission denied' "$unwritable_log" >/dev/null

# A missing explicit directory fails rather than falling back.
missing="$runtime_root/missing"
missing_log="$result_dir/deep-missing.log"
missing_status="$(run_mmdebstrap "$missing_log" env TMPDIR="$missing")"
assert_failure_names_path "$missing_status" "$missing_log" "$missing"

# A regular file supplied as TMPDIR fails rather than falling back.
not_directory="$runtime_root/not-a-directory"
printf 'not a directory\n' >"$not_directory"
not_directory_log="$result_dir/deep-not-directory.log"
not_directory_status="$(run_mmdebstrap "$not_directory_log" env TMPDIR="$not_directory")"
assert_failure_names_path "$not_directory_status" "$not_directory_log" "$not_directory"

# Match checks that do not depend on a particular formatter release.
perl -c "$source_root/mmdebstrap"
max_line_length="$(sed -e '/^__END__$/,$d' "$source_root/mmdebstrap" | wc --max-line-length)"
if [[ "$max_line_length" -gt 79 ]]; then
  echo "source exceeds 79 columns: $max_line_length" >&2
  exit 1
fi
perlcritic --severity 4 --verbose 8 "$source_root/mmdebstrap"
pod2man "$source_root/mmdebstrap" >/dev/null
sh -n "$source_root/tests/fail-with-unwritable-tmpdir"

# Upstream tests are templates. coverage.py substitutes these placeholders before
# ShellCheck and shfmt, so reproduce that step here.
rendered_test="$runtime_root/fail-with-unwritable-tmpdir.rendered.sh"
sed \
  -e "s|{{ CMD }}|$source_root/mmdebstrap|g" \
  -e 's|{{ MODE }}|chrootless|g' \
  -e 's|{{ VARIANT }}|apt|g' \
  -e 's|{{ DIST }}|sid|g' \
  -e 's|{{ MIRROR }}|http://127.0.0.1/debian|g' \
  "$source_root/tests/fail-with-unwritable-tmpdir" >"$rendered_test"
sh -n "$rendered_test"
shellcheck --exclude=SC2050,SC2194,SC2016 "$rendered_test"
shfmt --posix --binary-next-line --case-indent --indent 2 --simplify -d \
  "$rendered_test"

# Confirm the reviewed block is exactly the small, readable form under review.
python3 - "$source_root/mmdebstrap" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
expected = """        my @tempdir_options = (TMPDIR => 1);
        if (defined $ENV{TMPDIR} && $ENV{TMPDIR} ne '') {
            @tempdir_options = (DIR => $ENV{TMPDIR});
        }
        $options->{root} = tempdir('mmdebstrap.XXXXXXXXXX', @tempdir_options);
"""
if source.count(expected) != 1:
    raise SystemExit("reviewed TMPDIR block differs from the expected readable form")
PY

# The source tree runs an exact whole-file perltidy comparison, but its existing
# source comments identify perltidy 20220613. A newer formatter rewrites many
# untouched upstream lines, so record the local formatter version instead of
# treating cross-version output as a patch defect.
perltidy_version="$(perltidy --version 2>&1 | head -n 1)"
printf '%s\n' "$perltidy_version" >"$result_dir/perltidy-version.txt"

python3 "$repo_root/investigations/mmdebstrap-unwritable-tmpdir/suite_inventory.py"

python3 - "$result_dir/deep-review-summary.json" \
  "$unset_status" "$unset_selected" \
  "$empty_status" "$empty_selected" \
  "$writable_status" "$writable_selected" \
  "$unwritable_status" "$missing_status" "$not_directory_status" \
  "$max_line_length" "$perltidy_version" <<'PY'
import json
import pathlib
import sys

(
    output,
    unset_status,
    unset_selected,
    empty_status,
    empty_selected,
    writable_status,
    writable_selected,
    unwritable_status,
    missing_status,
    not_directory_status,
    max_line_length,
    perltidy_version,
) = sys.argv[1:]

data = {
    "unset_tmpdir": {"status": int(unset_status), "selected": unset_selected},
    "empty_tmpdir": {"status": int(empty_status), "selected": empty_selected},
    "writable_tmpdir": {
        "status": int(writable_status),
        "selected": writable_selected,
        "cleanup_complete": True,
    },
    "unwritable_tmpdir": {"status": int(unwritable_status), "selected": None},
    "missing_tmpdir": {"status": int(missing_status), "selected": None},
    "file_as_tmpdir": {"status": int(not_directory_status), "selected": None},
    "static_checks": {
        "perl_syntax": "passed",
        "reviewed_block_exact_form": "passed",
        "perlcritic_severity_4": "passed",
        "pod": "passed",
        "rendered_regression_test_shellcheck": "passed",
        "rendered_regression_test_shfmt": "passed",
        "maximum_code_line_length": int(max_line_length),
        "perltidy_version_recorded": perltidy_version,
        "whole_file_perltidy": "not compared across formatter versions",
    },
}
pathlib.Path(output).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(json.dumps(data, indent=2))
PY

echo "Deep review passed: explicit TMPDIR is strict; unset and empty behavior is preserved"
