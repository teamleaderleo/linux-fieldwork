#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/hook-authority-results"

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
    echo 'usage: hook_authority_transaction.sh --check-runtime-parent PATH' >&2
    exit 2
  }
  validate_runtime_parent "$2" >/dev/null
  exit
fi

runtime_parent="$(validate_runtime_parent "${RUNNER_TEMP:-/tmp}")"
runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-hook-authority")"
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

for command_name in cp patch perl python3 realpath stat timeout; do
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
hook_mutation="$prepared/mmdebstrap-hook-env-mutation"

cat >"$runtime/fake-bin/env" <<'EOF'
#!/bin/sh
set -eu
: "${OUTER_ENV_LOG:?}"
printf '%s\n' "$*" >>"$OUTER_ENV_LOG"
exec /usr/bin/env "$@"
EOF
chmod 0755 "$runtime/fake-bin/env"

cat >"$runtime/direct-hook" <<'EOF'
#!/bin/sh
set -eu
mkdir -p "$1/var/lib/lf-hook-authority"
printf 'direct-ran=yes\n' >"$1/var/lib/lf-hook-authority/direct.txt"
EOF
chmod 0755 "$runtime/direct-hook"

shell_hook='mkdir -p "$1/var/lib/lf-hook-authority"; printf "shell-ran=yes\n" >"$1/var/lib/lf-hook-authority/shell.txt"'

run_case() {
  local label=$1
  local mmdebstrap_path=$2
  local target="$runtime/$label-root"
  local outer_log="$result_dir/$label-outer-env.log"
  local status

  : >"$outer_log"
  set +e
  timeout 180 /usr/bin/env -i \
    PATH="$runtime/fake-bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    HOME="$runtime/home" \
    TMPDIR="$runtime" \
    LC_ALL=C.UTF-8 \
    OUTER_ENV_LOG="$outer_log" \
    "$mmdebstrap_path" \
      --mode=chrootless \
      --variant=custom \
      --format=directory \
      --skip=update \
      --setup-hook="$runtime/direct-hook" \
      --setup-hook="$shell_hook" \
      '' "$target" \
      >"$result_dir/$label.stdout" \
      2>"$result_dir/$label.stderr"
  status=$?
  set -e
  printf '%s\n' "$status" >"$result_dir/$label.status"

  [[ "$status" -ne 124 ]] || {
    echo "$label hook transaction timed out" >&2
    exit 1
  }
  [[ "$status" -eq 0 ]]
  grep -Fx 'direct-ran=yes' "$target/var/lib/lf-hook-authority/direct.txt"
  grep -Fx 'shell-ran=yes' "$target/var/lib/lf-hook-authority/shell.txt"
  cp -a "$target/var/lib/lf-hook-authority" "$result_dir/$label-markers"
}

classify_env_log() {
  local path=$1
  local host_probes=0 hook_launches=0 line
  while IFS= read -r line; do
    case "$line" in
      --version)
        host_probes=$((host_probes + 1))
        ;;
      --unset=TMPDIR*|--unset=APT_CONFIG*)
        hook_launches=$((hook_launches + 1))
        ;;
      '')
        ;;
      *)
        echo "unexpected caller-path env invocation in $path: $line" >&2
        return 1
        ;;
    esac
  done <"$path"
  printf '%s %s\n' "$host_probes" "$hook_launches"
}

run_case candidate "$candidate"
run_case hook-mutation "$hook_mutation"

read -r candidate_host_probes candidate_hook_launches < <(
  classify_env_log "$result_dir/candidate-outer-env.log"
)
read -r mutation_host_probes mutation_hook_launches < <(
  classify_env_log "$result_dir/hook-mutation-outer-env.log"
)

[[ "$candidate_host_probes" -ge 1 ]]
[[ "$candidate_hook_launches" -eq 0 ]]
[[ "$mutation_host_probes" -ge 1 ]]
[[ "$mutation_hook_launches" -eq 2 ]]

cmp "$result_dir/candidate-markers/direct.txt" \
  "$result_dir/hook-mutation-markers/direct.txt"
cmp "$result_dir/candidate-markers/shell.txt" \
  "$result_dir/hook-mutation-markers/shell.txt"

source_mode_after="$(stat -c '%a' "$source_root/mmdebstrap")"
[[ "$source_mode_after" == "$source_mode_before" ]]
git diff --exit-code -- upstream/mmdebstrap/mmdebstrap

cat >"$result_dir/summary.txt" <<EOF
product_source=upstream/mmdebstrap/mmdebstrap
executed_candidate_copy=$candidate
executed_hook_mutation=$hook_mutation
source_mode_before=$source_mode_before
source_mode_after=$source_mode_after
repository_source_unchanged=yes
candidate_status=$(cat "$result_dir/candidate.status")
candidate_direct_hook_ran=yes
candidate_shell_hook_ran=yes
candidate_caller_env_host_probe_count=$candidate_host_probes
candidate_caller_env_hook_launch_count=$candidate_hook_launches
hook_mutation_status=$(cat "$result_dir/hook-mutation.status")
hook_mutation_direct_hook_ran=yes
hook_mutation_shell_hook_ran=yes
hook_mutation_caller_env_host_probe_count=$mutation_host_probes
hook_mutation_caller_env_hook_launch_count=$mutation_hook_launches
candidate_mutation_outputs_equal=yes
interpretation=chrootless direct and shell hooks require validated absolute env authority; the losing mutation preserves hook behavior while exposing both launches to caller PATH
EOF

cat "$result_dir/summary.txt"
echo 'mmdebstrap chrootless hook authority transaction passed'
