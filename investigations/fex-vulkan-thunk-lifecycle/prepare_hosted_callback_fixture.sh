#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_WORKSPACE:?}"

install="$GITHUB_WORKSPACE/fex-install"
rootfs="$GITHUB_WORKSPACE/rootfs"
base="$GITHUB_WORKSPACE/investigations/fex-vulkan-thunk-lifecycle"

fex_bin="$install/bin/FEX"
thunk_config="$install/share/fex-emu/ThunksDB.json"
guest_vk="$install/share/fex-emu/GuestThunks/libvulkan-guest.so"
host_vk="$install/lib/fex-emu/HostThunks/libvulkan-host.so"
host_vk_32="$install/lib/fex-emu/HostThunks_32/libvulkan-host.so"

for path in "$fex_bin" "$thunk_config" "$guest_vk" "$host_vk" "$host_vk_32"; do
  test -e "$path"
done

test "$host_vk" != "$host_vk_32"

x86_64-linux-gnu-gcc -shared -fPIC -nostdlib -Wl,-soname,libX11.so.6 \
  "$base/fex_probe_x11_stub.c" -o /tmp/libX11.so.6

readelf -Ws /tmp/libX11.so.6 | grep -q XSync
readelf -Ws /tmp/libX11.so.6 | grep -q XGetVisualInfo
readelf -Ws /tmp/libX11.so.6 | grep -q XDisplayString
if readelf -d /tmp/libX11.so.6 | grep -q NEEDED; then
  echo "headless X11 shim gained an unexpected runtime dependency" >&2
  exit 1
fi

sudo mkdir -p "$rootfs/usr/lib/x86_64-linux-gnu"
sudo cp /tmp/libX11.so.6 "$rootfs/usr/lib/x86_64-linux-gnu/libX11.so.6"
sudo cp "$guest_vk" "$rootfs/usr/lib/x86_64-linux-gnu/libvulkan.so.1"

mkdir -p "$GITHUB_WORKSPACE/host-report" "$GITHUB_WORKSPACE/host-family"
cp "$host_vk" "$GITHUB_WORKSPACE/host-report/libvulkan-host.so"

{
  echo "FEX_BIN=$fex_bin"
  echo "FEX_ROOTFS=$rootfs"
  echo "FEX_THUNKCONFIG=$thunk_config"
  echo "FEX_THUNKGUESTLIBS=$(dirname "$guest_vk")"
  echo "BASELINE_HOSTLIBS=$(dirname "$host_vk")"
} >> "$GITHUB_ENV"

printf '64-bit host thunk: %s\n' "$host_vk"
printf '32-bit host thunk excluded: %s\n' "$host_vk_32"
file /tmp/libX11.so.6 "$guest_vk" "$host_vk"
