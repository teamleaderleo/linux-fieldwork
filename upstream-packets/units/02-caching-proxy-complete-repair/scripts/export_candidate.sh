#!/bin/sh
set -eu

repo_root=$(git rev-parse --show-toplevel)
packet_dir="$repo_root/upstream-packets/units/02-caching-proxy-complete-repair"
workdir=${1:-"$packet_dir/artifacts/export"}
candidate_root="$workdir/candidate"
patch_path="$packet_dir/patches/0001-caching-proxy-complete-repair.patch"
receipt="$packet_dir/artifacts/export-receipt.txt"

rm -rf "$workdir"
mkdir -p "$candidate_root" "$(dirname "$patch_path")" "$(dirname "$receipt")"

python3 "$repo_root/investigations/caching-proxy-complete-stack/compose.py" \
  --repo-root "$repo_root" \
  --destination "$candidate_root"

candidate="$candidate_root/upstream/mmdebstrap/caching_proxy.py"
python3 -m py_compile "$candidate"

set +e
diff -u \
  --label a/caching_proxy.py \
  --label b/caching_proxy.py \
  "$repo_root/upstream/mmdebstrap/caching_proxy.py" \
  "$candidate" >"$patch_path"
status=$?
set -e
[ "$status" -eq 1 ]

{
  printf 'linux_fieldwork_head=%s\n' "$(git rev-parse HEAD)"
  printf 'imported_blob=%s\n' "$(git hash-object "$repo_root/upstream/mmdebstrap/caching_proxy.py")"
  printf 'candidate_sha256='
  sha256sum "$candidate" | awk '{print $1}'
  printf 'patch_sha256='
  sha256sum "$patch_path" | awk '{print $1}'
  printf 'candidate_lines=%s\n' "$(wc -l <"$candidate")"
  printf 'patch_lines=%s\n' "$(wc -l <"$patch_path")"
  printf 'py_compile=PASS\n'
} >"$receipt"

cat "$receipt"
printf 'candidate=%s\npatch=%s\n' "$candidate" "$patch_path"
