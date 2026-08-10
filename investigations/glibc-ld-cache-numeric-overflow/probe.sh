#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
if [[ -z "$output_dir" ]]; then
  printf 'usage: %s OUTPUT_DIR\n' "$0" >&2
  exit 64
fi
for command in cc grep; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'required command is unavailable: %s\n' "$command" >&2
    exit 69
  }
done

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
work_root=$(mktemp -d "${RUNNER_TEMP:-/tmp}/glibc-cache-numeric-overflow.XXXXXX")
cleanup() { rm -rf -- "$work_root"; }
trap cleanup EXIT INT TERM

cat >"$work_root/probe.c" <<'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Exact body of glibc elf/dl-cache.c::_dl_cache_libcmp at
   6288139c32a194e0005593c30af6c79bb698cdf2, renamed only so this
   standalone fixture does not pretend to provide a glibc symbol.  */
static int cache_libcmp(const char *p1, const char *p2)
{
  while (*p1 != '\0')
    {
      if (*p1 >= '0' && *p1 <= '9')
        {
          if (*p2 >= '0' && *p2 <= '9')
            {
              int val1;
              int val2;

              val1 = *p1++ - '0';
              val2 = *p2++ - '0';
              while (*p1 >= '0' && *p1 <= '9')
                val1 = val1 * 10 + *p1++ - '0';
              while (*p2 >= '0' && *p2 <= '9')
                val2 = val2 * 10 + *p2++ - '0';
              if (val1 != val2)
                return val1 - val2;
            }
          else
            return 1;
        }
      else if (*p2 >= '0' && *p2 <= '9')
        return -1;
      else if (*p1 != *p2)
        return *p1 - *p2;
      else
        {
          ++p1;
          ++p2;
        }
    }
  return *p1 - *p2;
}

static int sign_of(int value)
{
  return (value > 0) - (value < 0);
}

int main(int argc, char **argv)
{
  if (argc == 3)
    {
      printf("%d\n", cache_libcmp(argv[1], argv[2]));
      return 0;
    }

  static const char *const names[] = {
    "libwide.so.0",
    "libwide.so.1",
    "libwide.so.2",
    "libwide.so.10",
    "libwide.so.2147483647",
    "libwide.so.2147483648",
    "libwide.so.4294967296",
    "libwide.so.8589934592",
  };
  const size_t count = sizeof(names) / sizeof(names[0]);
  int signs[sizeof(names) / sizeof(names[0])][sizeof(names) / sizeof(names[0])];

  puts("left\tright\tsign");
  for (size_t i = 0; i < count; ++i)
    for (size_t j = 0; j < count; ++j)
      {
        signs[i][j] = sign_of(cache_libcmp(names[i], names[j]));
        printf("%s\t%s\t%d\n", names[i], names[j], signs[i][j]);
      }

  int antisymmetric = 1;
  int transitive = 1;
  for (size_t i = 0; i < count; ++i)
    for (size_t j = 0; j < count; ++j)
      {
        if (signs[i][j] != -signs[j][i])
          antisymmetric = 0;
        for (size_t k = 0; k < count; ++k)
          if (signs[i][j] < 0 && signs[j][k] < 0 && signs[i][k] >= 0)
            transitive = 0;
      }

  printf("antisymmetric\t%d\n", antisymmetric);
  printf("transitive\t%d\n", transitive);

  if (!(signs[1][2] < 0 && signs[2][3] < 0 && signs[1][3] < 0))
    {
      fputs("small numeric control failed\n", stderr);
      return 2;
    }
  return 0;
}
EOF

cc -O2 -Wall -Wextra -Werror "$work_root/probe.c" -o "$work_root/probe-opt"
"$work_root/probe-opt" >"$output_dir/plain-matrix.tsv"

cc -O1 -g -Wall -Wextra -Werror \
  -fsanitize=undefined -fno-sanitize-recover=undefined \
  "$work_root/probe.c" -o "$work_root/probe-ubsan"

set +e
"$work_root/probe-ubsan" \
  libwide.so.2147483648 libwide.so.0 \
  >"$output_dir/ubsan.stdout" 2>"$output_dir/ubsan.stderr"
ubsan_status=$?
set -e

classification=no_signed_overflow_observed
if [[ "$ubsan_status" -ne 0 ]] \
  && grep -Fq 'signed integer overflow' "$output_dir/ubsan.stderr"; then
  classification=signed_overflow_reproduced
fi

{
  printf 'classification\t%s\n' "$classification"
  printf 'ubsan_status\t%d\n' "$ubsan_status"
  printf 'source_commit\t6288139c32a194e0005593c30af6c79bb698cdf2\n'
  printf 'compiler\t%s\n' "$(cc --version | head -n 1)"
} >"$output_dir/summary.tsv"

cat "$output_dir/summary.tsv"
tail -n 2 "$output_dir/plain-matrix.tsv"
