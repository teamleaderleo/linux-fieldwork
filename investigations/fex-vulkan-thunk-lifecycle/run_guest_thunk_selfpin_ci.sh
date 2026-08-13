#!/usr/bin/env bash
set -euxo pipefail

FEX_SHA=e869aa644a16e4332cdc15c1ea0b4d13d482385d
ROOT="$PWD"
FEX="$ROOT/fex-selfpin"
INSTALL="$ROOT/fex-selfpin-install"
ROOTFS="$ROOT/rootfs-selfpin"
EVIDENCE=/tmp/fex-selfpin-evidence
mkdir -p "$EVIDENCE"
ulimit -c 0

sudo apt-get update
sudo apt-get install -y \
  build-essential cmake ninja-build clang lld clang-tools libclang-dev llvm-dev pkg-config git ccache \
  gcc-x86-64-linux-gnu g++-x86-64-linux-gnu gcc-i686-linux-gnu g++-i686-linux-gnu libc6-dev-i386-cross \
  libcap-dev libglfw3-dev libepoxy-dev python3-dev libsdl2-dev \
  libasound2-dev libdrm-dev libwayland-dev libx11-dev libx11-xcb-dev libxcb1-dev libxrandr-dev libxrender-dev \
  libgl-dev libegl-dev libvulkan-dev mesa-vulkan-drivers

git clone --recurse-submodules https://github.com/teamleaderleo/FEX.git "$FEX"
git -C "$FEX" checkout "$FEX_SHA"
git -C "$FEX" submodule update --init --recursive

# Keep the dynamic-PFN lifetime test independent from the separate Vulkan X11
# host->guest callback-routing problem.
python3 - <<'PY'
from pathlib import Path
p = Path('fex-selfpin/ThunkLibs/libvulkan/Guest.cpp')
s = p.read_text()
start = s.find('void OnInit() {')
marker = '\n}\n\nLOAD_LIB_INIT(libvulkan, OnInit)'
end = s.find(marker, start)
if start < 0 or end < 0:
    raise SystemExit('Vulkan OnInit anchors not found')
s = s[:start] + 'void OnInit() {}\n\nLOAD_LIB_INIT(libvulkan, OnInit)' + s[end + len(marker):]
p.write_text(s)
PY

git -C "$FEX" diff --check
git -C "$FEX" diff -- ThunkLibs/libvulkan/Guest.cpp > "$EVIDENCE/vulkan-callback-isolation.diff"

configure_build_install() {
  rm -rf "$FEX/build" "$INSTALL"
  CC=clang CXX=clang++ cmake -S "$FEX" -B "$FEX/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_PREFIX="$INSTALL" \
    -DUSE_LINKER=lld \
    -DENABLE_LTO=False \
    -DENABLE_ASSERTIONS=True \
    -DBUILD_TESTING=False \
    -DBUILD_THUNKS=True \
    -DBUILD_FEXCONFIG=False \
    -DENABLE_CLANG_THUNKS=True \
    -DRANGES_NATIVE=OFF
  cmake --build "$FEX/build" -j"$(nproc)"
  cmake --install "$FEX/build"
}

configure_build_install

x86_64-linux-gnu-gcc -std=c11 -O2 -Wall -Wextra -Werror \
  investigations/fex-vulkan-thunk-lifecycle/fex_vulkan_guest_selfpin_probe.c \
  -ldl -o /tmp/selfpin-probe-x86_64

sudo systemctl start docker || true
sudo docker pull --platform linux/amd64 ubuntu:24.04
cid=$(sudo docker create --platform linux/amd64 ubuntu:24.04)
mkdir -p "$ROOTFS"
sudo docker export "$cid" | sudo tar -C "$ROOTFS" -xf -
sudo docker rm "$cid"
sudo mkdir -p "$ROOTFS/tmp" "$ROOTFS/usr/lib/x86_64-linux-gnu"
sudo cp /tmp/selfpin-probe-x86_64 "$ROOTFS/tmp/selfpin-probe-x86_64"
sudo chmod 0755 "$ROOTFS/tmp/selfpin-probe-x86_64"

LIBSTDCPP=$(x86_64-linux-gnu-g++ -print-file-name=libstdc++.so.6)
LIBGCC=$(x86_64-linux-gnu-gcc -print-file-name=libgcc_s.so.1)
sudo cp -L "$LIBSTDCPP" "$ROOTFS/usr/lib/x86_64-linux-gnu/libstdc++.so.6"
sudo cp -L "$LIBGCC" "$ROOTFS/usr/lib/x86_64-linux-gnu/libgcc_s.so.1"

install_runtime_guest_thunk() {
  GUEST_VK=$(find "$INSTALL" -type f -name libvulkan-guest.so | head -1)
  test -n "$GUEST_VK"
  readelf -d "$GUEST_VK" | grep NEEDED | tee "$EVIDENCE/$1-guest-vulkan-needed.txt"
  sudo cp "$GUEST_VK" "$ROOTFS/usr/lib/x86_64-linux-gnu/libvulkan.so.1"
}

FEX_BIN=$(find "$INSTALL" -type f -name FEX -perm -111 | head -1)
THUNK_CONFIG=$(find "$INSTALL" -type f -name ThunksDB.json | head -1)
HOST_VK="$INSTALL/lib/fex-emu/HostThunks/libvulkan-host.so"
ICD=$(find /usr/share/vulkan/icd.d -maxdepth 1 -type f -name 'lvp_icd*.json' | head -1)
test -x "$FEX_BIN"
test -f "$THUNK_CONFIG"
test -f "$HOST_VK"
test -f "$ICD"
HOST_LIB_DIR=$(dirname "$HOST_VK")

mkdir -p "$HOME/.fex-emu"
cat > "$HOME/.fex-emu/Config.json" <<JSON
{
  "Config": {
    "RootFS": "$ROOTFS",
    "ThunkConfig": "$THUNK_CONFIG"
  },
  "ThunksDB": {
    "Vulkan": 1
  }
}
JSON

run_probe() {
  phase=$1
  install_runtime_guest_thunk "$phase"
  set +e
  timeout 30s env \
    VK_DRIVER_FILES="$ICD" \
    FEX_THUNKHOSTLIBS="$HOST_LIB_DIR" \
    "$FEX_BIN" /tmp/selfpin-probe-x86_64 >"$EVIDENCE/${phase}.log" 2>&1
  status=$?
  set -e
  printf '%s\n' "$status" >"$EVIDENCE/${phase}.status"
  echo "$phase status=$status"
  cat "$EVIDENCE/${phase}.log"
}

run_probe baseline

# Baseline should demonstrate that the final application handle really unloads
# the guest wrapper in this isolated setup. The probe returns 20 at that point
# without calling through the now-stale pointer.
test "$(cat "$EVIDENCE/baseline.status")" = 20
grep -q 'after-final-app-close.*retained=0' "$EVIDENCE/baseline.log"

python3 investigations/fex-vulkan-thunk-lifecycle/apply_guest_thunk_selfpin_probe.py "$FEX"
git -C "$FEX" diff --check
git -C "$FEX" diff > "$EVIDENCE/selfpin-candidate.diff"

configure_build_install
FEX_BIN=$(find "$INSTALL" -type f -name FEX -perm -111 | head -1)
THUNK_CONFIG=$(find "$INSTALL" -type f -name ThunksDB.json | head -1)
HOST_VK="$INSTALL/lib/fex-emu/HostThunks/libvulkan-host.so"
HOST_LIB_DIR=$(dirname "$HOST_VK")

run_probe candidate

test "$(cat "$EVIDENCE/candidate.status")" = 0
grep -q 'after-final-app-close.*retained=1' "$EVIDENCE/candidate.log"
grep -q 'old-pfn-after-app-close.*result=0' "$EVIDENCE/candidate.log"
grep -q 'new-pfn-after-reopen.*result=0' "$EVIDENCE/candidate.log"
grep -q 'after-second-close retained=1' "$EVIDENCE/candidate.log"

printf 'baseline=%s\ncandidate=%s\n' \
  "$(cat "$EVIDENCE/baseline.status")" \
  "$(cat "$EVIDENCE/candidate.status")" | tee "$EVIDENCE/status-matrix.txt"
