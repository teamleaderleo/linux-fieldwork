#!/usr/bin/env bash
set -euxo pipefail

UPSTREAM_HEAD=5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491
V3_GENERATOR_HEAD=26c9d659049def8288455ad8e4766337b721388b

sudo apt-get update
sudo apt-get install -y build-essential clang zlib1g-dev liblzma-dev liblzo2-dev liblz4-dev libzstd-dev
rm -rf /tmp/sq /tmp/sq-v3 /tmp/evidence /tmp/src-v3 /tmp/src-v4 /tmp/append-src
mkdir -p /tmp/evidence /tmp/src-v3 /tmp/src-v4 /tmp/append-src
uname -a | tee /tmp/evidence/environment.txt
clang --version | tee -a /tmp/evidence/environment.txt
gcc --version | head -1 | tee -a /tmp/evidence/environment.txt
git --version | tee -a /tmp/evidence/environment.txt

git clone https://github.com/plougher/squashfs-tools.git /tmp/sq
git -C /tmp/sq checkout --detach "$UPSTREAM_HEAD"
test "$(git -C /tmp/sq rev-parse HEAD)" = "$UPSTREAM_HEAD"
git -C /tmp/sq show -s --format='%H %cI %s' HEAD | tee /tmp/evidence/upstream-head.txt
make -C /tmp/sq/squashfs-tools -j2 mksquashfs
cp /tmp/sq/squashfs-tools/mksquashfs /tmp/mksquashfs-v4

git clone https://github.com/plougher/squashfs-tools.git /tmp/sq-v3
git -C /tmp/sq-v3 checkout --detach "$V3_GENERATOR_HEAD"
OLD_CFLAGS='-I. -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_GNU_SOURCE -O2 -fcommon -include sys/sysmacros.h'
make -C /tmp/sq-v3/squashfs-tools CFLAGS="$OLD_CFLAGS" mksquashfs
cp /tmp/sq-v3/squashfs-tools/mksquashfs /tmp/mksquashfs-v3
git -C /tmp/sq-v3 show -s --format='%H %cI %s' HEAD | tee /tmp/evidence/v3-generator-head.txt

cat > /tmp/layout-v4.c <<'EOF'
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include "squashfs_fs.h"
int main(int argc, char **argv) {
    FILE *f; struct squashfs_super_block sb; unsigned short mh; unsigned int len;
    unsigned char *buf; struct squashfs_base_inode_header *base;
    struct squashfs_lreg_inode_header *inode;
    if(argc != 2) return 2;
    f = fopen(argv[1], "rb"); if(!f) return 3;
    if(fread(&sb, sizeof(sb), 1, f) != 1) return 4;
    if(fseeko(f, sb.inode_table_start, SEEK_SET) != 0) return 5;
    if(fread(&mh, sizeof(mh), 1, f) != 1 || (mh & 0x8000) == 0) return 6;
    len = mh & 0x7fff; buf = malloc(len); if(!buf) return 7;
    if(fread(buf, 1, len, f) != len) return 8;
    base = (struct squashfs_base_inode_header *) buf;
    if(base->inode_type != SQUASHFS_LREG_TYPE) return 9;
    inode = (struct squashfs_lreg_inode_header *) buf;
    printf("BLOCK_SIZE=%u\n", sb.block_size);
    printf("FILE_SIZE_ABS=%lld\n", (long long) sb.inode_table_start + 2 + (long long) offsetof(struct squashfs_lreg_inode_header, file_size));
    printf("INODE_TYPE=%u\n", base->inode_type);
    printf("FRAGMENT=%u\n", inode->fragment);
    printf("NLINK=%u\n", inode->nlink);
    free(buf); fclose(f); return 0;
}
EOF

cat > /tmp/layout-v3.c <<'EOF'
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include "squashfs_fs.h"
#include "squashfs_compat.h"
int main(int argc, char **argv) {
    FILE *f; squashfs_super_block_3 sb; unsigned short mh; unsigned int len;
    unsigned char *buf; squashfs_base_inode_header_3 *base;
    squashfs_lreg_inode_header_3 *inode;
    if(argc != 2) return 2;
    f = fopen(argv[1], "rb"); if(!f) return 3;
    if(fread(&sb, sizeof(sb), 1, f) != 1) return 4;
    if(fseeko(f, sb.inode_table_start, SEEK_SET) != 0) return 5;
    if(fread(&mh, sizeof(mh), 1, f) != 1 || (mh & 0x8000) == 0) return 6;
    len = mh & 0x7fff; buf = malloc(len); if(!buf) return 7;
    if(fread(buf, 1, len, f) != len) return 8;
    base = (squashfs_base_inode_header_3 *) buf;
    if(base->inode_type != SQUASHFS_LREG_TYPE) return 9;
    inode = (squashfs_lreg_inode_header_3 *) buf;
    printf("BLOCK_SIZE=%u\n", sb.block_size);
    printf("FILE_SIZE_ABS=%lld\n", (long long) sb.inode_table_start + 2 + (long long) offsetof(squashfs_lreg_inode_header_3, file_size));
    printf("INODE_TYPE=%u\n", base->inode_type);
    printf("FRAGMENT=%u\n", inode->fragment);
    printf("NLINK=%u\n", inode->nlink);
    free(buf); fclose(f); return 0;
}
EOF

cc -O2 -I/tmp/sq/squashfs-tools /tmp/layout-v4.c -o /tmp/layout-v4
cc -O2 -I/tmp/sq/squashfs-tools /tmp/layout-v3.c -o /tmp/layout-v3
printf Z > /tmp/src-v4/file
ln /tmp/src-v4/file /tmp/src-v4/file-hardlink
printf Z > /tmp/src-v3/file
ln /tmp/src-v3/file /tmp/src-v3/file-hardlink
printf A > /tmp/append-src/new-file

/tmp/mksquashfs-v4 /tmp/src-v4 /tmp/v4-nofrag-base.sqfs -noI -no-fragments -nopad -noappend -no-progress
/tmp/mksquashfs-v4 /tmp/src-v4 /tmp/v4-frag-base.sqfs -noI -nopad -noappend -no-progress
/tmp/mksquashfs-v3 /tmp/src-v3 /tmp/v3-nofrag-base.sqfs -noI -no-fragments -nopad -noappend -no-progress
/tmp/mksquashfs-v3 /tmp/src-v3 /tmp/v3-frag-base.sqfs -noI -nopad -noappend -no-progress
/tmp/layout-v4 /tmp/v4-nofrag-base.sqfs | tee /tmp/evidence/v4-nofrag-layout.txt
/tmp/layout-v4 /tmp/v4-frag-base.sqfs | tee /tmp/evidence/v4-frag-layout.txt
/tmp/layout-v3 /tmp/v3-nofrag-base.sqfs | tee /tmp/evidence/v3-nofrag-layout.txt
/tmp/layout-v3 /tmp/v3-frag-base.sqfs | tee /tmp/evidence/v3-frag-layout.txt
grep -q '^FRAGMENT=4294967295$' /tmp/evidence/v4-nofrag-layout.txt
grep -q '^FRAGMENT=0$' /tmp/evidence/v4-frag-layout.txt
grep -q '^FRAGMENT=4294967295$' /tmp/evidence/v3-nofrag-layout.txt
grep -q '^FRAGMENT=0$' /tmp/evidence/v3-frag-layout.txt

patch_size() {
    local src="$1" dst="$2" off="$3" value="$4"
    cp "$src" "$dst"
    python3 - "$dst" "$off" "$value" <<'PY'
import hashlib, struct, sys
p, off, value = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
d = bytearray(open(p, 'rb').read())
old = struct.unpack_from('<q', d, off)[0]
struct.pack_into('<q', d, off, value)
open(p, 'wb').write(d)
print(f"path={p} offset={off} old={old} new={value} sha256={hashlib.sha256(d).hexdigest()}")
PY
}

make_cases() {
    local ver="$1" nofrag="$2" frag="$3" no_layout="$4" frag_layout="$5"
    local block no_off frag_off max_blocks max_size plusbyte frag_max frag_plus
    block="$(awk -F= '$1=="BLOCK_SIZE" {print $2}' "$no_layout")"
    no_off="$(awk -F= '$1=="FILE_SIZE_ABS" {print $2}' "$no_layout")"
    frag_off="$(awk -F= '$1=="FILE_SIZE_ABS" {print $2}' "$frag_layout")"
    max_blocks=$((2147483647 / 4))
    max_size=$((max_blocks * block))
    plusbyte=$((max_size + 1))
    frag_max=$((max_size + 1))
    frag_plus=$(((max_blocks + 1) * block + 1))
    printf '%s block=%s max_blocks=%s max_size=%s plusbyte=%s frag_max=%s frag_plus=%s llmax=%s\n' "$ver" "$block" "$max_blocks" "$max_size" "$plusbyte" "$frag_max" "$frag_plus" 9223372036854775807 | tee "/tmp/evidence/${ver}-boundaries.txt"
    patch_size "$nofrag" "/tmp/${ver}-nofrag-max.sqfs" "$no_off" "$max_size" | tee "/tmp/evidence/${ver}-mutations.txt"
    patch_size "$nofrag" "/tmp/${ver}-nofrag-plus.sqfs" "$no_off" "$plusbyte" | tee -a "/tmp/evidence/${ver}-mutations.txt"
    patch_size "$nofrag" "/tmp/${ver}-nofrag-llmax.sqfs" "$no_off" 9223372036854775807 | tee -a "/tmp/evidence/${ver}-mutations.txt"
    patch_size "$frag" "/tmp/${ver}-frag-max.sqfs" "$frag_off" "$frag_max" | tee -a "/tmp/evidence/${ver}-mutations.txt"
    patch_size "$frag" "/tmp/${ver}-frag-plus.sqfs" "$frag_off" "$frag_plus" | tee -a "/tmp/evidence/${ver}-mutations.txt"
}
make_cases v4 /tmp/v4-nofrag-base.sqfs /tmp/v4-frag-base.sqfs /tmp/evidence/v4-nofrag-layout.txt /tmp/evidence/v4-frag-layout.txt
make_cases v3 /tmp/v3-nofrag-base.sqfs /tmp/v3-frag-base.sqfs /tmp/evidence/v3-nofrag-layout.txt /tmp/evidence/v3-frag-layout.txt

python3 <<'PY'
from pathlib import Path
root = Path('/tmp/sq/squashfs-tools')
for name in ('unsquash-3.c', 'unsquash-4.c'):
    p = root / name
    s = p.read_text()
    s = s.replace('#include "unsquashfs.h"\n', '#include <limits.h>\n\n#include "unsquashfs.h"\n', 1)
    marker = ('\t\t\tsquashfs_lreg_inode_header_3 *inode = &header.lreg;\n'
              if name == 'unsquash-3.c' else
              '\t\t\tstruct squashfs_lreg_inode_header *inode = &header.lreg;\n')
    if s.count(marker) != 1:
        raise SystemExit(f'{name}: LREG marker count={s.count(marker)}')
    s = s.replace(marker, marker + '\t\t\tlong long blocks;\n', 1)
    old = '''\t\t\ti.data = inode->file_size;\n\t\t\ti.frag_bytes = inode->fragment == SQUASHFS_INVALID_FRAG\n\t\t\t\t?  0 : inode->file_size % sBlk.s.block_size;\n\t\t\ti.fragment = inode->fragment;\n\t\t\ti.offset = inode->offset;\n\t\t\ti.blocks = inode->fragment == SQUASHFS_INVALID_FRAG ?\n\t\t\t\t(inode->file_size + sBlk.s.block_size - 1) >>\n\t\t\t\tsBlk.s.block_log :\n\t\t\t\tinode->file_size >> sBlk.s.block_log;\n'''
    new = '''\t\t\tblocks = inode->file_size >> sBlk.s.block_log;\n\t\t\tif(inode->fragment == SQUASHFS_INVALID_FRAG &&\n\t\t\t\tinode->file_size % sBlk.s.block_size)\n\t\t\t\tblocks++;\n\t\t\tif(blocks > INT_MAX / (int) sizeof(unsigned int))\n\t\t\t\tEXIT_UNSQUASH("File system corrupted - block count in inode too large (blocks: %lld)\\n", blocks);\n\n\t\t\ti.data = inode->file_size;\n\t\t\ti.frag_bytes = inode->fragment == SQUASHFS_INVALID_FRAG\n\t\t\t\t?  0 : inode->file_size % sBlk.s.block_size;\n\t\t\ti.fragment = inode->fragment;\n\t\t\ti.offset = inode->offset;\n\t\t\ti.blocks = (int) blocks;\n'''
    if s.count(old) != 1:
        raise SystemExit(f'{name}: LREG calculation count={s.count(old)}')
    p.write_text(s.replace(old, new, 1))

p = root / 'read_fs.c'
s = p.read_text()
anchor = '''\t\tcase SQUASHFS_LREG_TYPE: {\n\t\t\tstruct squashfs_lreg_inode_header inode;\n\t\t\tint frag_bytes, blocks, i;\n\t\t\tlong long start, file_bytes = 0;\n'''
replacement = '''\t\tcase SQUASHFS_LREG_TYPE: {\n\t\t\tstruct squashfs_lreg_inode_header inode;\n\t\t\tint frag_bytes, blocks, i;\n\t\t\tlong long start, file_bytes = 0, block_count;\n'''
if s.count(anchor) != 1:
    raise SystemExit(f'read_fs LREG declaration anchor count={s.count(anchor)}')
s = s.replace(anchor, replacement, 1)
old = '''\t\t\tfrag_bytes = inode.fragment == SQUASHFS_INVALID_FRAG ?\n\t\t\t\t0 : inode.file_size % sBlk->block_size;\n\t\t\tblocks = inode.fragment == SQUASHFS_INVALID_FRAG ?\n\t\t\t\t(inode.file_size + sBlk->block_size - 1) >>\n\t\t\t\tsBlk->block_log : inode.file_size >>\n\t\t\t\tsBlk->block_log;\n\t\t\tstart = inode.start_block;\n'''
new = '''\t\t\tfrag_bytes = inode.fragment == SQUASHFS_INVALID_FRAG ?\n\t\t\t\t0 : inode.file_size % sBlk->block_size;\n\t\t\tblock_count = inode.file_size >> sBlk->block_log;\n\t\t\tif(inode.fragment == SQUASHFS_INVALID_FRAG &&\n\t\t\t\tinode.file_size % sBlk->block_size)\n\t\t\t\tblock_count++;\n\t\t\tif(block_count > INT_MAX / (int) sizeof(unsigned int)) {\n\t\t\t\tERROR("File system corrupted - block count in inode too large (blocks: %lld)\\n", block_count);\n\t\t\t\tgoto corrupted2;\n\t\t\t}\n\t\t\tblocks = (int) block_count;\n\t\t\tstart = inode.start_block;\n'''
if s.count(old) != 1:
    raise SystemExit(f'read_fs LREG calculation count={s.count(old)}')
p.write_text(s.replace(old, new, 1))
PY

git -C /tmp/sq diff --check
git -C /tmp/sq diff -- squashfs-tools/unsquash-3.c squashfs-tools/unsquash-4.c squashfs-tools/read_fs.c | tee /tmp/evidence/candidate.diff
test "$(git -C /tmp/sq diff --name-only | sort)" = $'squashfs-tools/read_fs.c\nsquashfs-tools/unsquash-3.c\nsquashfs-tools/unsquash-4.c'

make -C /tmp/sq/squashfs-tools clean
make -C /tmp/sq/squashfs-tools -j2
echo NORMAL_FULL_BUILD_OK | tee /tmp/evidence/normal-build.txt

SAN='-O1 -g -fsanitize=address,undefined,implicit-integer-truncation -fno-sanitize-recover=all -fno-omit-frame-pointer'
make -C /tmp/sq/squashfs-tools clean
make -C /tmp/sq/squashfs-tools -j2 CC=clang EXTRA_CFLAGS="$SAN" EXTRA_LDFLAGS='-fsanitize=address,undefined,implicit-integer-truncation' unsquashfs mksquashfs
cp /tmp/sq/squashfs-tools/unsquashfs /tmp/unsquashfs-candidate
cp /tmp/sq/squashfs-tools/mksquashfs /tmp/mksquashfs-candidate
export ASAN_OPTIONS='halt_on_error=1:abort_on_error=1:detect_leaks=0'
export UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'

clean_log() { ! grep -Eq 'runtime error:|AddressSanitizer|UndefinedBehaviorSanitizer' "$1"; }
unsq_ok() {
    local label="$1" image="$2"
    /tmp/unsquashfs-candidate -processors 1 -no-progress -ll "$image" > "/tmp/evidence/${label}.log" 2>&1
    clean_log "/tmp/evidence/${label}.log"
    cat "/tmp/evidence/${label}.log"
}
unsq_reject() {
    local label="$1" image="$2"
    set +e
    /tmp/unsquashfs-candidate -processors 1 -no-progress -ll "$image" > "/tmp/evidence/${label}.log" 2>&1
    local st=$?
    set -e
    echo "status=$st" >> "/tmp/evidence/${label}.log"
    test "$st" -ne 0
    grep -q 'File system corrupted - block count in inode too large' "/tmp/evidence/${label}.log"
    clean_log "/tmp/evidence/${label}.log"
    cat "/tmp/evidence/${label}.log"
}
for ver in v4 v3; do
    unsq_ok "${ver}-nofrag-base-candidate" "/tmp/${ver}-nofrag-base.sqfs"
    unsq_ok "${ver}-nofrag-max-candidate" "/tmp/${ver}-nofrag-max.sqfs"
    unsq_reject "${ver}-nofrag-plus-candidate" "/tmp/${ver}-nofrag-plus.sqfs"
    unsq_reject "${ver}-nofrag-llmax-candidate" "/tmp/${ver}-nofrag-llmax.sqfs"
    unsq_ok "${ver}-frag-base-candidate" "/tmp/${ver}-frag-base.sqfs"
    unsq_ok "${ver}-frag-max-candidate" "/tmp/${ver}-frag-max.sqfs"
    unsq_reject "${ver}-frag-plus-candidate" "/tmp/${ver}-frag-plus.sqfs"
done

append_ok() {
    local label="$1" image="$2"
    cp "$image" "/tmp/${label}-append.sqfs"
    /tmp/mksquashfs-candidate /tmp/append-src "/tmp/${label}-append.sqfs" -noI -no-progress > "/tmp/evidence/${label}.log" 2>&1
    clean_log "/tmp/evidence/${label}.log"
    grep -q 'Scanning existing filesystem' "/tmp/evidence/${label}.log"
    cat "/tmp/evidence/${label}.log"
}
append_reject() {
    local label="$1" image="$2"
    cp "$image" "/tmp/${label}-append.sqfs"
    set +e
    /tmp/mksquashfs-candidate /tmp/append-src "/tmp/${label}-append.sqfs" -noI -no-progress > "/tmp/evidence/${label}.log" 2>&1
    local st=$?
    set -e
    echo "status=$st" >> "/tmp/evidence/${label}.log"
    test "$st" -ne 0
    grep -q 'File system corrupted - block count in inode too large' "/tmp/evidence/${label}.log"
    clean_log "/tmp/evidence/${label}.log"
    cat "/tmp/evidence/${label}.log"
}
append_ok v4-append-nofrag-base /tmp/v4-nofrag-base.sqfs
append_ok v4-append-frag-base /tmp/v4-frag-base.sqfs
append_reject v4-append-nofrag-plus /tmp/v4-nofrag-plus.sqfs
append_reject v4-append-nofrag-llmax /tmp/v4-nofrag-llmax.sqfs
append_reject v4-append-frag-plus /tmp/v4-frag-plus.sqfs

sha256sum /tmp/v4-*.sqfs /tmp/v3-*.sqfs | sort | tee /tmp/evidence/fixture-sha256.txt
echo 'ALL LF-633 THREE-READER CANDIDATE ASSERTIONS PASSED' | tee /tmp/evidence/result.txt
