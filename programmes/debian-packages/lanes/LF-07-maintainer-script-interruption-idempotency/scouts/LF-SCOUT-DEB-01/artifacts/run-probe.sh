#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work_dir=${1:-"${TMPDIR:-/tmp}/lf07-maintainer-script-idempotency"}
fixture_dir="$script_dir/fixture/package"
package_name=lf-script-idempotency-fixture
package_dir="$work_dir/package"
package_deb="$work_dir/${package_name}_1.0_all.deb"
results_dir="$script_dir/results"
assertions_file="$results_dir/assertions.tsv"
assertion_failures=0

rm -rf "$work_dir" "$results_dir"
mkdir -p "$work_dir" "$results_dir"
cp -a "$fixture_dir" "$package_dir"
chmod 0755 "$package_dir/DEBIAN/postinst"

printf 'check\texpected\tactual\tresult\n' > "$assertions_file"

assert_equal() {
    check=$1
    expected=$2
    actual=$3
    if [ "$actual" = "$expected" ]; then
        result=passed
    else
        result=failed
        assertion_failures=$((assertion_failures + 1))
    fi
    printf '%s\t%s\t%s\t%s\n' "$check" "$expected" "$actual" "$result" >> "$assertions_file"
}

package_status() {
    root=$1
    awk -v package="$package_name" '
        $1 == "Package:" && $2 == package { in_package=1 }
        in_package && $1 == "Status:" { print $2 " " $3 " " $4; exit }
    ' "$root/var/lib/dpkg/status"
}

registry_line_count() {
    root=$1
    registry="$root/var/lib/$package_name/registry"
    if [ -f "$registry" ]; then
        wc -l < "$registry" | tr -d ' '
    else
        printf '0\n'
    fi
}

{
    date -u '+run_utc=%Y-%m-%dT%H:%M:%SZ'
    printf 'uid=%s\n' "$(id -u)"
    printf 'kernel='
    uname -srmo
    sed -n 's/^PRETTY_NAME=/os=/p' /etc/os-release
    dpkg --version | sed -n '1p'
    dpkg-deb --version | sed -n '1p'
    /usr/bin/busybox | sed -n '1p'
} > "$results_dir/environment.txt"

(
    cd "$fixture_dir"
    find . -type f -print0 | sort -z | xargs -0 sha256sum
) > "$results_dir/fixture.sha256"

sh -n "$fixture_dir/DEBIAN/postinst"
sh -n "$script_dir/run-probe.sh"

dpkg-deb --build --root-owner-group "$package_dir" "$package_deb" >"$results_dir/build.log" 2>&1

copy_binary_with_libs() {
    binary=$1
    root=$2
    destination="$root$binary"
    mkdir -p "$(dirname "$destination")"
    cp -L "$binary" "$destination"
    ldd "$binary" | awk '
        /=> \// { print $3; next }
        /\/lib.*ld-linux/ { for (i = 1; i <= NF; i++) if ($i ~ /^\//) print $i }
    ' | while IFS= read -r library; do
        [ -n "$library" ] || continue
        mkdir -p "$root$(dirname "$library")"
        cp -L "$library" "$root$library"
    done
}

make_root() {
    root=$1
    rm -rf "$root"
    mkdir -p \
        "$root/bin" \
        "$root/etc" \
        "$root/run/$package_name" \
        "$root/tmp" \
        "$root/usr/local/bin" \
        "$root/usr/share" \
        "$root/var/cache" \
        "$root/var/lib/dpkg/info" \
        "$root/var/lib/dpkg/updates" \
        "$root/var/lib/dpkg/triggers"

    : > "$root/etc/passwd"
    : > "$root/etc/group"
    : > "$root/var/lib/dpkg/status"
    : > "$root/var/lib/dpkg/available"

    copy_binary_with_libs /usr/bin/busybox "$root"
    for applet in sh cat grep kill ln mkdir mv rm; do
        ln -s /usr/bin/busybox "$root/bin/$applet"
    done
}

run_dpkg() {
    root=$1
    shift
    dpkg --root="$root" --admindir="$root/var/lib/dpkg" "$@"
}

snapshot() {
    root=$1
    output=$2
    {
        echo '[package-state]'
        awk -v package="$package_name" '
            $1 == "Package:" && $2 == package { in_package=1 }
            in_package && ($1 == "Package:" || $1 == "Status:" || $1 == "Version:" || $1 == "Architecture:") { print }
            in_package && NF == 0 { exit }
        ' "$root/var/lib/dpkg/status"

        echo '[filesystem]'
        for path in \
            "var/lib/$package_name/state" \
            "var/lib/$package_name/registry" \
            "etc/$package_name/generated.conf" \
            "usr/local/bin/$package_name-current" \
            "usr/share/$package_name/payload.txt"
        do
            full="$root/$path"
            if [ -L "$full" ]; then
                printf '%s|symlink|%s\n' "$path" "$(readlink "$full")"
            elif [ -f "$full" ]; then
                printf '%s|file|mode=%s|sha256=%s\n' \
                    "$path" \
                    "$(stat -c '%a' "$full")" \
                    "$(sha256sum "$full" | awk '{print $1}')"
                sed 's/^/  /' "$full"
            else
                printf '%s|absent\n' "$path"
            fi
        done

        echo '[users-groups]'
        printf 'etc/passwd|sha256=%s\n' "$(sha256sum "$root/etc/passwd" | awk '{print $1}')"
        printf 'etc/group|sha256=%s\n' "$(sha256sum "$root/etc/group" | awk '{print $1}')"

        echo '[services]'
        service_entries=$(find "$root/etc/systemd" "$root/lib/systemd" -mindepth 1 -print 2>/dev/null | sort || true)
        if [ -n "$service_entries" ]; then printf '%s\n' "$service_entries"; else echo 'none'; fi

        echo '[alternatives]'
        alternative_entries=$(find "$root/etc/alternatives" "$root/var/lib/dpkg/alternatives" -mindepth 1 -print 2>/dev/null | sort || true)
        if [ -n "$alternative_entries" ]; then printf '%s\n' "$alternative_entries"; else echo 'none'; fi

        echo '[caches]'
        cache_entries=$(find "$root/var/cache" -mindepth 1 -print 2>/dev/null | sort || true)
        if [ -n "$cache_entries" ]; then printf '%s\n' "$cache_entries"; else echo 'none'; fi
    } > "$output"
}

clean_root="$work_dir/root-clean"
make_root "$clean_root"
set +e
run_dpkg "$clean_root" --install "$package_deb" >"$results_dir/clean-install.log" 2>&1
clean_rc=$?
set -e
snapshot "$clean_root" "$results_dir/clean.snapshot"
clean_status=$(package_status "$clean_root")
clean_registry_lines=$(registry_line_count "$clean_root")
assert_equal 'clean.install_rc' '0' "$clean_rc"
assert_equal 'clean.final_status' 'install ok installed' "$clean_status"
assert_equal 'clean.registry_lines' '1' "$clean_registry_lines"

printf 'point\tfirst_rc\tpre_recovery_status\trecovery_rc\tfinal_status\tfinal_comparison\tregistry_lines\tassertions\n' > "$results_dir/summary.tsv"

for point in after-state after-registry after-config; do
    case "$point" in
        after-state)
            expected_comparison=converged
            expected_registry_lines=1
            ;;
        after-registry|after-config)
            expected_comparison=diverged
            expected_registry_lines=2
            ;;
    esac

    failures_before=$assertion_failures
    root="$work_dir/root-$point"
    make_root "$root"
    printf '%s\n' "$point" > "$root/run/$package_name/interrupt-after"

    set +e
    run_dpkg "$root" --install "$package_deb" >"$results_dir/$point.interrupted.log" 2>&1
    first_rc=$?
    set -e

    pre_status=$(package_status "$root")
    printf '%s\n' "$pre_status" > "$results_dir/$point.pre-recovery-status.txt"

    set +e
    run_dpkg "$root" --configure "$package_name" >"$results_dir/$point.recovery.log" 2>&1
    recovery_rc=$?
    set -e
    final_status=$(package_status "$root")
    snapshot "$root" "$results_dir/$point.snapshot"

    if diff -u --label clean.snapshot --label "$point.snapshot" "$results_dir/clean.snapshot" "$results_dir/$point.snapshot" > "$results_dir/$point.diff"; then
        comparison=converged
    else
        comparison=diverged
    fi

    registry_lines=$(registry_line_count "$root")

    assert_equal "$point.interrupted_install_rc" '1' "$first_rc"
    assert_equal "$point.pre_recovery_status" 'install ok half-configured' "$pre_status"
    assert_equal "$point.recovery_rc" '0' "$recovery_rc"
    assert_equal "$point.final_status" 'install ok installed' "$final_status"
    assert_equal "$point.comparison" "$expected_comparison" "$comparison"
    assert_equal "$point.registry_lines" "$expected_registry_lines" "$registry_lines"

    if [ "$assertion_failures" -eq "$failures_before" ]; then
        point_assertions=passed
    else
        point_assertions=failed
    fi

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$point" "$first_rc" "$pre_status" "$recovery_rc" "$final_status" \
        "$comparison" "$registry_lines" "$point_assertions" \
        >> "$results_dir/summary.tsv"
done

for log in "$results_dir"/*.log; do
    sed "s#$work_dir#<work-dir>#g" "$log" > "$log.tmp"
    mv "$log.tmp" "$log"
done

cat "$results_dir/summary.tsv"

if [ "$assertion_failures" -ne 0 ]; then
    printf '%s assertion(s) failed; see %s\n' "$assertion_failures" "$assertions_file" >&2
    exit 1
fi

printf 'all assertions passed\n'
