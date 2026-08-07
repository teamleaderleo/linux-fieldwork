#!/usr/bin/env bash
set -u -o pipefail

jq_bin=${1:?usage: probe.sh /path/to/jq output-dir}
output_dir=${2:?usage: probe.sh /path/to/jq output-dir}
mkdir -p "$output_dir/cases" "$output_dir/disassembly"
output_dir=$(cd "$output_dir" && pwd)

if [[ ! -x "$jq_bin" ]]; then
    echo "jq binary is not executable: $jq_bin" >&2
    exit 2
fi
jq_bin=$(cd "$(dirname "$jq_bin")" && pwd)/$(basename "$jq_bin")

run_case() {
    local name=$1
    local filter=$2
    local stdout="$output_dir/cases/$name.stdout"
    local stderr="$output_dir/cases/$name.stderr"
    local status=0

    "$jq_bin" -n -c "$filter" >"$stdout" 2>"$stderr" || status=$?
    printf '%s\t%d\t%s\t%s\n' \
        "$name" \
        "$status" \
        "$(sha256sum "$stdout" | cut -d' ' -f1)" \
        "$(sha256sum "$stderr" | cut -d' ' -f1)" \
        >>"$output_dir/results.tsv"
    printf '%s\t%s\n' "$name" "$filter" >>"$output_dir/filters.tsv"
}

: >"$output_dir/results.tsv"
: >"$output_dir/filters.tsv"

# Exact issue discriminators.
run_case issue-constant-object 'path({} as {$a} | .)'
run_case issue-dot-object 'path(. as {$a} | .)'

# Shape expansion: the binding expression must not contribute a path, while
# object/array matcher traversal still must.
run_case nested-constant-object 'path({b:{}} as {b:{$a}} | .)'
run_case constant-array 'path([] as [$a] | .)'
run_case constant-array-object 'path([{}] as [{$a}] | .)'
run_case dot-array-object 'path(. as [{$a}] | .)'

# bind_alternation_matchers has a separate compiler path and must be exercised
# for both the first and fallback matcher.
run_case alternation-object 'path({a:1} as {$a} ?// [$a] | .)'
run_case alternation-array 'path([1] as {$a} ?// [$a] | .)'
run_case alternation-scalar 'path(1 as {$a} ?// [$a] ?// $a | .)'

# Backtracking values expose stack and SUBEXP lifetime mistakes that a single
# successful output can hide.
run_case backtracking-object 'path(({}, {a:1}) as {$a} | .)'
run_case backtracking-alternation 'path(({a:1}, [2], 3) as {$a} ?// [$a] ?// $a | .)'

# Ordinary binding and path controls must remain unchanged.
run_case binding-object '{} as {$a} | $a'
run_case binding-nested '{b:{a:1}} as {b:{$a}} | $a'
run_case binding-array '[1] as [$a] | $a'
run_case plain-path-object 'path(.a)'
run_case plain-path-nested 'path(.b.a)'
run_case plain-path-array 'path(.[0])'

for name in issue-constant-object issue-dot-object alternation-object; do
    filter=$(awk -F '\t' -v name="$name" '$1 == name {sub($1 FS, ""); print; exit}' "$output_dir/filters.tsv")
    "$jq_bin" -n --debug-dump-disasm "$filter" \
        >"$output_dir/disassembly/$name.stdout" \
        2>"$output_dir/disassembly/$name.stderr" || true
done

{
    echo "jq_version=$($jq_bin --version)"
    echo "jq_sha256=$(sha256sum "$jq_bin" | cut -d' ' -f1)"
    echo "compiler=$(cc --version | head -n1)"
    echo "uname=$(uname -a)"
} >"$output_dir/environment.txt"

# These controls establish that the built binary and probe itself are usable.
plain_status=$(awk -F '\t' '$1 == "plain-path-object" {print $2}' "$output_dir/results.tsv")
binding_status=$(awk -F '\t' '$1 == "binding-nested" {print $2}' "$output_dir/results.tsv")
[[ "$plain_status" == 0 ]]
[[ "$binding_status" == 0 ]]
grep -Fxq '["a"]' "$output_dir/cases/plain-path-object.stdout"
grep -Fxq '1' "$output_dir/cases/binding-nested.stdout"

cat "$output_dir/environment.txt"
cat "$output_dir/results.tsv"
