#!/bin/sh
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out=${1:-"$here/results/fnmatch-matrix.csv"}
bin=${TMPDIR:-/tmp}/lf39-fnmatch-matrix.$$

cleanup() {
    rm -f -- "$bin"
}
trap cleanup EXIT HUP INT TERM

mkdir -p -- "$(dirname -- "$out")"

cc -O2 -Wall -Wextra -Werror \
    -o "$bin" "$here/bench_fnmatch.c"

printf '%s\n' 'pattern,n,final,flags,reps,result,seconds,per_call' >"$out"

for n in 14 16 18 20 22 24 26 28 30 32 34; do
    reps=3
    if [ "$n" -ge 30 ]; then
        reps=1
    fi

    timeout 12s "$bin" '*(a|aa)b' "$n" c 32 "$reps" >>"$out"
    timeout 12s "$bin" '*(a|aa)b' "$n" b 32 "$reps" >>"$out"
    timeout 12s "$bin" '*(a)b' "$n" c 32 "$reps" >>"$out"
    timeout 12s "$bin" '*(a|b)b' "$n" c 32 "$reps" >>"$out"
    timeout 12s "$bin" '*(a|aa)b' "$n" c 0 "$reps" >>"$out"
done

cat "$out"
