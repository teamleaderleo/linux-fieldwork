#!/usr/bin/env bash
set -euxo pipefail

FEX_SHA=e869aa644a16e4332cdc15c1ea0b4d13d482385d
ROOT="$PWD"
FEX="$ROOT/fex"
INSTALL="$ROOT/fex-install"
ROOTFS="$ROOT/rootfs"
EVIDENCE=/tmp/fex-customir-evidence
mkdir -p "$EVIDENCE"
ulimit -c 0

sudo apt-get update
sudo apt-get install -y \
  build-essential cmake ninja-build clang lld clang-tools libclang-dev llvm-dev pkg-config git ccache \
  gcc-x86-64-linux-gnu g++-x86-64-linux-gnu \
  libcap-dev libglfw3-dev libepoxy-dev python3-dev libsdl2-dev \
  libasound2-dev libdrm-dev libwayland-dev libx11-dev libx11-xcb-dev libxcb1-dev libxrandr-dev libxrender-dev \
  libgl-dev libegl-dev libvulkan-dev mesa-vulkan-drivers

git clone --recurse-submodules https://github.com/teamleaderleo/FEX.git "$FEX"
git -C "$FEX" checkout "$FEX_SHA"
git -C "$FEX" submodule update --init --recursive

# Isolate the guest->host dynamic-PFN path from the separate Vulkan X11
# host->guest callback registrations. Both baseline and candidate use this
# identical isolation edit.
python3 - <<'PY'
from pathlib import Path
p = Path('fex/ThunkLibs/libvulkan/Guest.cpp')
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

x86_64-linux-gnu-gcc -std=c11 -O2 -Wall -Wextra -Werror \
  investigations/fex-vulkan-thunk-lifecycle/fex_vulkan_pfn_unload_probe.c \
  -ldl -o /tmp/probe-x86_64

sudo systemctl start docker || true
sudo docker info
sudo docker pull --platform linux/amd64 ubuntu:24.04
cid=$(sudo docker create --platform linux/amd64 ubuntu:24.04)
mkdir -p "$ROOTFS"
sudo docker export "$cid" | sudo tar -C "$ROOTFS" -xf -
sudo docker rm "$cid"
sudo mkdir -p "$ROOTFS/tmp"
sudo cp /tmp/probe-x86_64 "$ROOTFS/tmp/probe-x86_64"
sudo chmod 0755 "$ROOTFS/tmp/probe-x86_64"

FEX_BIN=$(find "$INSTALL" -type f -name FEX -perm -111 | head -1)
THUNK_CONFIG="$FEX/Data/CI/VulkanThunks.json"
GUEST_VK=$(find "$INSTALL" -type f -name libvulkan-guest.so | head -1)
HOST_VK=$(find "$INSTALL" -type f -name libvulkan-host.so | head -1)
ICD=$(find /usr/share/vulkan/icd.d -maxdepth 1 -type f -name 'lvp_icd*.json' | head -1)
test -n "$FEX_BIN"
test -f "$THUNK_CONFIG"
test -n "$GUEST_VK"
test -n "$HOST_VK"
test -n "$ICD"

sudo mkdir -p "$ROOTFS/usr/lib/x86_64-linux-gnu"
sudo cp "$GUEST_VK" "$ROOTFS/usr/lib/x86_64-linux-gnu/libvulkan.so.1"
HOST_LIB_DIR=$(dirname "$HOST_VK")
GUEST_LIB_DIR=$(dirname "$GUEST_VK")
mkdir -p "$HOME/.fex-emu"
cat > "$HOME/.fex-emu/Config.json" <<JSON
{
  "Config": {
    "RootFS": "$ROOTFS",
    "ThunkConfig": "$THUNK_CONFIG"
  }
}
JSON
cat "$HOME/.fex-emu/Config.json"
cat "$THUNK_CONFIG"

run_case() {
  phase=$1
  mode=$2
  set +e
  timeout 30s env \
    VK_DRIVER_FILES="$ICD" \
    FEX_THUNKCONFIG="$THUNK_CONFIG" \
    FEX_THUNKHOSTLIBS="$HOST_LIB_DIR" \
    FEX_THUNKGUESTLIBS="$GUEST_LIB_DIR" \
    "$FEX_BIN" /tmp/probe-x86_64 "$mode" >"$EVIDENCE/${phase}-${mode}.log" 2>&1
  status=$?
  set -e
  printf '%s\n' "$status" >"$EVIDENCE/${phase}-${mode}.status"
  echo "$phase-$mode status=$status"
  cat "$EVIDENCE/${phase}-${mode}.log"
}

run_case baseline hold
run_case baseline reload
run_case baseline close

python3 investigations/fex-vulkan-thunk-lifecycle/apply_customir_retirement_probe.py "$FEX"

# Keep these two compile-only refinements disposable until runtime evidence
# selects the design. The retained transformer stays close to the source-level
# hypothesis and the final Fieldwork record will say exactly which bytes ran.
python3 - <<'PY'
from pathlib import Path
core = Path('fex/FEXCore/Source/Interface/Core/Core.cpp')
s = core.read_text()
s = s.replace(
    'LogMan::Msg::IFmt("THUNK_LIFETIME CUSTOMIR_HIT H={:#x} T={}", GuestRIP, fmt::ptr(Handler->second.Data));',
    'LogMan::Msg::IFmt("THUNK_LIFETIME CUSTOMIR_HIT H={:#x} T={:#x}", GuestRIP, reinterpret_cast<uintptr_t>(Handler->second.Data));')
s = s.replace(
    'void RemoveThunkTrampolineIRHandlersInRange(FEXCore::Context::Context* CTX, FEXCore::Core::InternalThreadState* Thread,',
    'FEX_DEFAULT_VISIBILITY void RemoveThunkTrampolineIRHandlersInRange(FEXCore::Context::Context* CTX, FEXCore::Core::InternalThreadState* Thread,')
core.write_text(s)
smc = Path('fex/Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsSMCTracking.cpp')
s = smc.read_text().replace(
    'void RemoveThunkTrampolineIRHandlersInRange(FEXCore::Context::Context* CTX, FEXCore::Core::InternalThreadState* Thread,',
    'FEX_DEFAULT_VISIBILITY void RemoveThunkTrampolineIRHandlersInRange(FEXCore::Context::Context* CTX, FEXCore::Core::InternalThreadState* Thread,')
smc.write_text(s)
PY

git -C "$FEX" diff --check
git -C "$FEX" diff > "$EVIDENCE/customir-candidate.diff"
grep -R "THUNK_LIFETIME" -n "$FEX/FEXCore/Source/Interface/Core/Core.cpp" | tee "$EVIDENCE/instrumentation-sites.txt"

cmake --build "$FEX/build" -j"$(nproc)"
cmake --install "$FEX/build"
GUEST_VK=$(find "$INSTALL" -type f -name libvulkan-guest.so | head -1)
sudo cp "$GUEST_VK" "$ROOTFS/usr/lib/x86_64-linux-gnu/libvulkan.so.1"

run_case candidate hold
run_case candidate reload
run_case candidate close

for f in "$EVIDENCE"/*.status; do
  printf '%s=%s\n' "$(basename "$f" .status)" "$(cat "$f")"
done | sort | tee "$EVIDENCE/status-matrix.txt"

# A valid retained owner must survive a non-final close. A fresh generation
# must also work when its old guest mappings are forcibly reserved.
test "$(cat "$EVIDENCE/baseline-hold.status")" = 0
test "$(cat "$EVIDENCE/candidate-hold.status")" = 0
test "$(cat "$EVIDENCE/candidate-reload.status")" = 0
grep -q "PROBE reserved-old-generation-ranges=" "$EVIDENCE/candidate-reload.log"
grep -q "THUNK_LIFETIME REGISTER" "$EVIDENCE/candidate-reload.log"
grep -q "THUNK_LIFETIME RETIRE" "$EVIDENCE/candidate-reload.log"
