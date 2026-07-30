#!/usr/bin/env bash
set -euo pipefail

ROOT_INPUT=${1:-/tmp/lf12-variance-run}
ROOT=$(realpath -m -- "$ROOT_INPUT")
case "$ROOT" in
    /|/tmp|/var/tmp)
        echo "refusing unsafe run directory: $ROOT" >&2
        exit 2
        ;;
    /tmp/*|/var/tmp/*)
        ;;
    *)
        echo "run directory must be beneath /tmp or /var/tmp: $ROOT" >&2
        exit 2
        ;;
esac

FIXTURE="$ROOT/fixture"
RUNS="$ROOT/runs"
OUT="$ROOT/out"
rm -rf -- "$ROOT"
mkdir -p "$FIXTURE/src" "$FIXTURE/debian/source" "$RUNS" "$OUT"

cat > "$FIXTURE/src/message.h" <<'EOF'
#ifndef LF12_MESSAGE_H
#define LF12_MESSAGE_H
const char *lf12_message(void);
#endif
EOF

cat > "$FIXTURE/src/message.c" <<'EOF'
#include "message.h"
const char *lf12_message(void) {
    return "LF-12 variance probe 1.0";
}
EOF

cat > "$FIXTURE/src/probe.c" <<'EOF'
#include <stdio.h>
#include "message.h"
int main(void) {
    puts(lf12_message());
    return 0;
}
EOF

cat > "$FIXTURE/Makefile" <<'EOF'
CC ?= cc
CPPFLAGS += $(shell dpkg-buildflags --get CPPFLAGS)
CFLAGS += $(shell dpkg-buildflags --get CFLAGS)
LDFLAGS += $(shell dpkg-buildflags --get LDFLAGS)
OBJECTS = src/probe.o src/message.o

all: lf12-variance-probe

lf12-variance-probe: $(OBJECTS)
	$(CC) -o $@ $(OBJECTS) $(LDFLAGS)

src/probe.o: src/probe.c src/message.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

src/message.o: src/message.c src/message.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

clean:
	rm -f lf12-variance-probe $(OBJECTS)
EOF

cat > "$FIXTURE/debian/changelog" <<'EOF'
lf12-variance-probe (1.0) unstable; urgency=medium

  * Controlled source package for LF-12 variance probing.

 -- Linux Fieldwork <fieldwork@example.invalid>  Thu, 30 Jul 2026 04:30:00 +0000
EOF

cat > "$FIXTURE/debian/control" <<'EOF'
Source: lf12-variance-probe
Section: misc
Priority: optional
Maintainer: Linux Fieldwork <fieldwork@example.invalid>
Build-Depends: dpkg-dev, gcc, make, libc6-dev
Standards-Version: 4.7.2
Rules-Requires-Root: no

Package: lf12-variance-probe
Architecture: any
Depends: libc6 (>= 2.34)
Description: controlled package for reproducibility variance probing
 A one-binary native source package used to compare Debian build outputs while
 changing one environmental input at a time.
EOF

cat > "$FIXTURE/debian/source/format" <<'EOF'
3.0 (native)
EOF

cat > "$FIXTURE/debian/rules" <<'EOF'
#!/usr/bin/make -f

PARALLEL_JOBS = $(patsubst parallel=%,%,$(filter parallel=%,$(DEB_BUILD_OPTIONS)))
MAKE_JOBS = $(if $(PARALLEL_JOBS),-j$(PARALLEL_JOBS),)

%:
	@echo "unsupported target: $@" >&2
	@exit 2

build build-arch build-indep:
	$(MAKE) $(MAKE_JOBS)

test:
	./lf12-variance-probe | grep -Fx 'LF-12 variance probe 1.0'

clean:
	$(MAKE) clean
	rm -rf debian/lf12-variance-probe debian/files debian/substvars

binary binary-arch: build test
	rm -rf debian/lf12-variance-probe
	install -d debian/lf12-variance-probe/usr/bin
	install -m 0755 lf12-variance-probe debian/lf12-variance-probe/usr/bin/lf12-variance-probe
	install -d debian/lf12-variance-probe/usr/share/doc/lf12-variance-probe
	if [ "$${LF_FILE_ORDER:-forward}" = reverse ]; then \
		printf '%s\n' 'Second deterministic payload file.' > debian/lf12-variance-probe/usr/share/doc/lf12-variance-probe/DETAILS; \
		printf '%s\n' 'LF-12 controlled variance fixture.' > debian/lf12-variance-probe/usr/share/doc/lf12-variance-probe/README; \
	else \
		printf '%s\n' 'LF-12 controlled variance fixture.' > debian/lf12-variance-probe/usr/share/doc/lf12-variance-probe/README; \
		printf '%s\n' 'Second deterministic payload file.' > debian/lf12-variance-probe/usr/share/doc/lf12-variance-probe/DETAILS; \
	fi
	install -d debian/lf12-variance-probe/DEBIAN
	dpkg-gencontrol -plf12-variance-probe -Pdebian/lf12-variance-probe -Tdebian/substvars
	dpkg-deb --build --root-owner-group debian/lf12-variance-probe ..

binary-indep:
	@:
EOF
chmod +x "$FIXTURE/debian/rules"

SOURCE_EPOCH=$(dpkg-parsechangelog -l"$FIXTURE/debian/changelog" -STimestamp)
ALT_EPOCH=$((SOURCE_EPOCH - 86400))
HOST=$(hostname)

build_one() {
    local name=$1 path=$2 locale=$3 tz=$4 user_mode=$5 file_order=$6 parallel=$7 epoch_mode=$8 host_env=$9
    local parent="$RUNS/$path"
    local src="$parent/src"
    local result="$OUT/$name"
    rm -rf -- "$parent" "$result"
    mkdir -p "$parent" "$result"
    cp -a "$FIXTURE" "$src"
    local epoch_args=()
    if [[ "$epoch_mode" == alternate ]]; then
        epoch_args=(SOURCE_DATE_EPOCH="$ALT_EPOCH")
    fi
    local env_args=(
        HOME=/tmp
        LC_ALL="$locale"
        TZ="$tz"
        USER="$user_mode"
        LOGNAME="$user_mode"
        HOSTNAME="$host_env"
        LF_FILE_ORDER="$file_order"
        DEB_BUILD_OPTIONS="parallel=$parallel"
    )
    if [[ "$user_mode" == nobody ]]; then
        chown -R nobody:nogroup "$parent"
        (cd "$src" && runuser -u nobody -- env "${env_args[@]}" "${epoch_args[@]}" dpkg-buildpackage -us -uc -b) >"$result/build.log" 2>&1
    else
        (cd "$src" && env "${env_args[@]}" "${epoch_args[@]}" dpkg-buildpackage -us -uc -b) >"$result/build.log" 2>&1
    fi
    cp "$parent"/*.deb "$parent"/*.buildinfo "$parent"/*.changes "$result"/
    local deb
    deb=$(find "$result" -name '*.deb' -print -quit)
    dpkg-deb -x "$deb" "$result/unpacked"
    dpkg-deb -e "$deb" "$result/control"
    ar tv "$deb" > "$result/ar-members.txt"
    dpkg-deb --fsys-tarfile "$deb" | tar --full-time -tvf - > "$result/data-members.txt"
    sha256sum "$result"/*.deb "$result"/*.buildinfo "$result"/*.changes > "$result/sha256.txt"
}

build_one baseline-a common-path C UTC root forward 1 default "$HOST"
sleep 2
build_one baseline-b common-path C UTC root forward 1 default "$HOST"
build_one path-long very/long/alternate/build/path C UTC root forward 1 default "$HOST"
build_one locale-cutf8 locale-path C.UTF-8 UTC root forward 1 default "$HOST"
build_one timezone-au timezone-path C Pacific/Auckland root forward 1 default "$HOST"
build_one hostname-env hostname-path C UTC root forward 1 default lf12-other-host
build_one user-nobody user-path C UTC nobody forward 1 default "$HOST"
build_one input-order order-path C UTC root reverse 1 default "$HOST"
build_one parallel-4 parallel-path C UTC root forward 4 default "$HOST"
build_one source-date-minus1d epoch-path C UTC root forward 1 alternate "$HOST"

base_deb=$(find "$OUT/baseline-a" -name '*.deb' -print -quit)
base_buildinfo=$(find "$OUT/baseline-a" -name '*.buildinfo' -print -quit)
base_changes=$(find "$OUT/baseline-a" -name '*.changes' -print -quit)

printf 'variant\tdeb_equal\tunpacked_bytes_equal\tcontrol_equal\tbuildinfo_equal\tbuildinfo_equal_without_build_date\tchanges_equal\tdeb_sha256\n' > "$ROOT/variance-matrix.tsv"
for dir in "$OUT"/*; do
    name=$(basename "$dir")
    deb=$(find "$dir" -name '*.deb' -print -quit)
    buildinfo=$(find "$dir" -name '*.buildinfo' -print -quit)
    changes=$(find "$dir" -name '*.changes' -print -quit)
    deb_equal=no; cmp -s "$base_deb" "$deb" && deb_equal=yes
    unpacked_equal=no; diff -qr "$OUT/baseline-a/unpacked" "$dir/unpacked" >/dev/null && unpacked_equal=yes
    control_equal=no; diff -qr "$OUT/baseline-a/control" "$dir/control" >/dev/null && control_equal=yes
    buildinfo_equal=no; cmp -s "$base_buildinfo" "$buildinfo" && buildinfo_equal=yes
    buildinfo_norm_equal=no; diff -u <(sed '/^Build-Date:/d' "$base_buildinfo") <(sed '/^Build-Date:/d' "$buildinfo") >/dev/null && buildinfo_norm_equal=yes
    changes_equal=no; cmp -s "$base_changes" "$changes" && changes_equal=yes
    deb_sha=$(sha256sum "$deb" | awk '{print $1}')
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$deb_equal" "$unpacked_equal" "$control_equal" "$buildinfo_equal" "$buildinfo_norm_equal" "$changes_equal" "$deb_sha" >> "$ROOT/variance-matrix.tsv"
done

for variant in baseline-a baseline-b hostname-env input-order locale-cutf8 parallel-4 path-long timezone-au user-nobody; do
    awk -F '\t' -v variant="$variant" '$1 == variant && $2 == "yes" && $3 == "yes" && $4 == "yes" {found=1} END {exit !found}' "$ROOT/variance-matrix.tsv"
done
awk -F '\t' '$1 == "source-date-minus1d" && $2 == "no" && $3 == "yes" && $4 == "yes" {found=1} END {exit !found}' "$ROOT/variance-matrix.tsv"
grep -F 'make -j4' "$OUT/parallel-4/build.log" >/dev/null

{
    echo '## Environment'
    cat /etc/os-release
    echo "architecture=$(dpkg --print-architecture)"
    echo "kernel=$(uname -srmo)"
    echo "hostname=$(hostname)"
    echo "source_date_epoch_from_changelog=$SOURCE_EPOCH"
    echo "alternate_source_date_epoch=$ALT_EPOCH"
    for pkg in dpkg dpkg-dev gcc make fakeroot libc6 libc6-dev binutils coreutils tar xz-utils gzip; do
        dpkg-query -W -f='${Package}=${Version}\n' "$pkg" 2>/dev/null || true
    done
    echo 'locales:'
    locale -a
} > "$ROOT/environment.txt"

{
    echo '## Baseline .buildinfo difference'
    diff -u "$OUT/baseline-a"/*.buildinfo "$OUT/baseline-b"/*.buildinfo || true
    echo
    echo '## Path .buildinfo difference'
    diff -u "$OUT/baseline-a"/*.buildinfo "$OUT/path-long"/*.buildinfo || true
    echo
    echo '## Parallel build command'
    grep -F 'make -j4' "$OUT/parallel-4/build.log" || true
    echo
    echo '## SOURCE_DATE_EPOCH package archive difference'
    echo 'baseline ar members:'
    cat "$OUT/baseline-a/ar-members.txt"
    echo 'alternate epoch ar members:'
    cat "$OUT/source-date-minus1d/ar-members.txt"
    echo
    echo 'baseline data members:'
    cat "$OUT/baseline-a/data-members.txt"
    echo 'alternate epoch data members:'
    cat "$OUT/source-date-minus1d/data-members.txt"
    echo
    echo 'first byte differences:'
    cmp -l "$base_deb" "$OUT/source-date-minus1d"/*.deb 2>/dev/null | head -20 || true
} > "$ROOT/diff-summary.txt"

cat "$ROOT/variance-matrix.tsv"
