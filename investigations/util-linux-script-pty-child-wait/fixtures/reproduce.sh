#!/usr/bin/env bash
set -u

out=$(mktemp)
typescript=$(mktemp)
trap 'rm -f "$out" "$typescript"' EXIT

run_case() {
    local name=$1
    local expected=$2
    shift 2

    : >"$out"
    set +e
    "$@" >"$out" 2>&1
    local rc=$?
    set -e

    printf '=== %s ===\n' "$name"
    cat "$out"
    printf 'rc=%d expected=%d\n' "$rc" "$expected"

    if [[ $rc -ne $expected ]]; then
        printf 'unexpected result for %s\n' "$name" >&2
        return 1
    fi
}

set -e

run_case 'ordinary file' 0 \
    timeout 3s script -q -c 'echo test' "$typescript"

run_case 'process substitution, exec-eligible last command' 124 \
    timeout 3s bash -c 'script -q -c "echo test" >(wc -c)'

run_case 'process substitution, trailing no-op control' 0 \
    timeout 3s bash -c 'script -q -c "echo test" >(wc -c); :'
