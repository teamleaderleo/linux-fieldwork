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
work_root=$(mktemp -d "${RUNNER_TEMP:-/tmp}/glibc-cache-numeric-overflow-candidate.XXXXXX")
cleanup() { rm -rf -- "$work_root"; }
trap cleanup EXIT INT TERM

cat >"$work_root/probe.c" <<'EOF'
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

/* Candidate replacement for glibc elf/dl-cache.c::_dl_cache_libcmp's
   decimal-run handling.  Non-digit handling is unchanged.  */
static int cache_libcmp(const char *p1, const char *p2)
{
  while (*p1 != '\0')
    {
      if (*p1 >= '0' && *p1 <= '9')
        {
          if (*p2 >= '0' && *p2 <= '9')
            {
              const char *run1 = p1;
              const char *run2 = p2;
              while (*p1 >= '0' && *p1 <= '9')
                ++p1;
              while (*p2 >= '0' && *p2 <= '9')
                ++p2;

              while (run1 + 1 < p1 && *run1 == '0')
                ++run1;
              while (run2 + 1 < p2 && *run2 == '0')
                ++run2;

              size_t length1 = (size_t) (p1 - run1);
              size_t length2 = (size_t) (p2 - run2);
              if (length1 != length2)
                return length1 < length2 ? -1 : 1;

              while (run1 < p1)
                {
                  if (*run1 != *run2)
                    return *run1 - *run2;
                  ++run1;
                  ++run2;
                }
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
    "libwide.so.00",
    "libwide.so.1",
    "libwide.so.01",
    "libwide.so.001",
    "libwide.so.2",
    "libwide.so.10",
    "libwide.so.2147483647",
    "libwide.so.2147483648",
    "libwide.so.4294967296",
    "libwide.so.8589934592",
    "libwide.so.18446744073709551616000000000000000000000000000000",
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
  printf("zero_alias_equal\t%d\n",
         cache_libcmp("libwide.so.0", "libwide.so.00") == 0);
  printf("one_alias_equal\t%d\n",
         cache_libcmp("libwide.so.1", "libwide.so.01") == 0
         && cache_libcmp("libwide.so.01", "libwide.so.001") == 0);

  if (!(cache_libcmp("libwide.so.1", "libwide.so.2") < 0
        && cache_libcmp("libwide.so.2", "libwide.so.10") < 0
        && cache_libcmp("libwide.so.2147483647", "libwide.so.2147483648") < 0
        && cache_libcmp("libwide.so.4294967296", "libwide.so.8589934592") < 0))
    {
      fputs("numeric ordering control failed\n", stderr);
      return 2;
    }
  if (!antisymmetric || !transitive)
    return 3;
  if (cache_libcmp("libwide.so.1", "libwide.so.01") != 0
      || cache_libcmp("libwide.so.01", "libwide.so.001") != 0)
    return 4;
  return 0;
}
EOF

cc -O2 -Wall -Wextra -Werror "$work_root/probe.c" -o "$work_root/probe-opt"
"$work_root/probe-opt" >"$output_dir/plain-matrix.tsv"

cc -O1 -g -Wall -Wextra -Werror \
  -fsanitize=undefined -fno-sanitize-recover=undefined \
  "$work_root/probe.c" -o "$work_root/probe-ubsan"
"$work_root/probe-ubsan" \
  >"$output_dir/ubsan.stdout" 2>"$output_dir/ubsan.stderr"

classification=candidate_ordering_restored
if [[ -s "$output_dir/ubsan.stderr" ]]; then
  classification=candidate_sanitizer_output
fi
if ! grep -Fqx $'antisymmetric\t1' "$output_dir/plain-matrix.tsv" \
  || ! grep -Fqx $'transitive\t1' "$output_dir/plain-matrix.tsv" \
  || ! grep -Fqx $'zero_alias_equal\t1' "$output_dir/plain-matrix.tsv" \
  || ! grep -Fqx $'one_alias_equal\t1' "$output_dir/plain-matrix.tsv"; then
  classification=candidate_ordering_failed
fi

{
  printf 'classification\t%s\n' "$classification"
  printf 'source_commit\t6288139c32a194e0005593c30af6c79bb698cdf2\n'
  printf 'compiler\t%s\n' "$(cc --version | head -n 1)"
} >"$output_dir/summary.tsv"

cat "$output_dir/summary.tsv"
tail -n 4 "$output_dir/plain-matrix.tsv"

[[ "$classification" == candidate_ordering_restored ]]
