#!/bin/sh
set -eu

src=${1:-prototype_exact_option_transport.c}
outdir=${2:-artifacts/exact-option-v2-results}

rm -rf "$outdir"
mkdir -p "$outdir"

for cc in gcc clang; do
	"$cc" -std=gnu11 -Wall -Wextra -Werror -O1 -g \
		-fsanitize=address,undefined -fno-omit-frame-pointer \
		"$src" -o "$outdir/exact-option-$cc"
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
		"$outdir/exact-option-$cc" >"$outdir/$cc.json"
done

cmp "$outdir/gcc.json" "$outdir/clang.json"
sha256sum "$src" "$outdir"/* >"$outdir/sha256.txt"
