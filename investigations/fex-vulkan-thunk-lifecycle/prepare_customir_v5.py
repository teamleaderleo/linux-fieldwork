#!/usr/bin/env python3
from pathlib import Path
import glob
import json
import os
import shutil
import subprocess

ROOT = Path.cwd()
FEX = ROOT / "fex-selfpin"
INSTALL = ROOT / "fex-selfpin-install"
ROOTFS = ROOT / "rootfs-selfpin"
VULKANINFO_ROOTFS = ROOT / "rootfs-vulkaninfo"
EVIDENCE = Path("/tmp/fex-vulkan-combined-evidence")
EVIDENCE.mkdir(parents=True, exist_ok=True)


def run(args, **kwargs):
    print("+", " ".join(map(str, args)))
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


# The self-pin differential intentionally disabled Vulkan's X11 callback setup.
# Restore the real constructor and add only the proven debug-report routes.
run(["git", "-C", FEX, "checkout", "HEAD", "--", "ThunkLibs/libvulkan/Guest.cpp"])
host = FEX / "ThunkLibs/libvulkan/Host.cpp"
s = host.read_text()
old = '''  } else if (a_1 == "vkFreeMemory"sv) {\n    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkFreeMemory;\n  } else if (a_1 == "vkAcquireXlibDisplayEXT"sv) {\n'''
new = '''  } else if (a_1 == "vkFreeMemory"sv) {\n    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkFreeMemory;\n  } else if (a_1 == "vkCreateDebugReportCallbackEXT"sv) {\n    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkCreateDebugReportCallbackEXT;\n  } else if (a_1 == "vkDestroyDebugReportCallbackEXT"sv) {\n    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_vkDestroyDebugReportCallbackEXT;\n  } else if (a_1 == "vkAcquireXlibDisplayEXT"sv) {\n'''
if s.count(old) != 1:
    raise SystemExit(f"expected one debug-report routing anchor, found {s.count(old)}")
host.write_text(s.replace(old, new, 1))
run(["git", "-C", FEX, "diff", "--check"])
with (EVIDENCE / "combined-candidate.diff").open("w") as out:
    run(["git", "-C", FEX, "diff"], stdout=out)

run(["cmake", "--build", FEX / "build", f"-j{os.cpu_count() or 2}"])
run(["cmake", "--install", FEX / "build"])
run(["x86_64-linux-gnu-gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
     "investigations/fex-vulkan-thunk-lifecycle/fex_vulkan_combined_probe.c", "-ldl", "-o", "/tmp/fex-vulkan-combined-probe"])
run(["x86_64-linux-gnu-gcc", "-shared", "-fPIC", "-O2", "-Wall", "-Wextra", "-Werror",
     "investigations/fex-vulkan-thunk-lifecycle/fex_x11_stub.c", "-Wl,-soname,libX11.so.6", "-o", "/tmp/libX11.so.6"])

run(["sudo", "cp", "/tmp/fex-vulkan-combined-probe", ROOTFS / "tmp/fex-vulkan-combined-probe"])
run(["sudo", "cp", "/tmp/libX11.so.6", ROOTFS / "usr/lib/x86_64-linux-gnu/libX11.so.6"])
guest_vk = next(INSTALL.rglob("libvulkan-guest.so"))
run(["sudo", "cp", guest_vk, ROOTFS / "usr/lib/x86_64-linux-gnu/libvulkan.so.1"])

fex_bin = next(p for p in INSTALL.rglob("FEX") if os.access(p, os.X_OK))
thunk_config = next(INSTALL.rglob("ThunksDB.json"))
host_vk = INSTALL / "lib/fex-emu/HostThunks/libvulkan-host.so"
icd = Path(glob.glob("/usr/share/vulkan/icd.d/lvp_icd*.json")[0])
env = os.environ.copy()
env["VK_DRIVER_FILES"] = str(icd)
env["FEX_THUNKHOSTLIBS"] = str(host_vk.parent)
log = EVIDENCE / "combined.log"
with log.open("w") as out:
    result = subprocess.run(["timeout", "45s", str(fex_bin), "/tmp/fex-vulkan-combined-probe"], env=env, stdout=out, stderr=subprocess.STDOUT)
(EVIDENCE / "combined.status").write_text(f"{result.returncode}\n")
text = log.read_text()
print(text)
required = [
    "COMBINED debug-report-created result=0",
    "COMBINED debug-report-destroyed",
    "COMBINED instance-destroyed",
    "COMBINED after-app-close retained=1",
    "COMBINED post-close-version result=0",
    "COMBINED PASS",
]
if result.returncode != 0 or any(marker not in text for marker in required):
    raise SystemExit(f"combined Vulkan gate failed with status {result.returncode}")
print("Combined Vulkan routing + guest-thunk lifetime gate passed")

# Application-level gate: run the real distro vulkaninfo binary that historically
# enumerated successfully and then died during teardown. Keep this in a separate
# amd64 rootfs so the small focused lifetime fixture remains unchanged.
#
# The ARM Actions runner does not have amd64 binfmt/QEMU registration, so an
# amd64 Docker container cannot be started there. Build the filesystem without
# executing any guest binaries: export an unstarted amd64 Ubuntu container, use
# the host apt solver in an isolated amd64 package state, then dpkg-deb -x the
# downloaded packages into the exported rootfs.
if VULKANINFO_ROOTFS.exists():
    run(["sudo", "rm", "-rf", VULKANINFO_ROOTFS])
VULKANINFO_ROOTFS.mkdir(parents=True)

cid_result = subprocess.run([
    "sudo", "docker", "create", "--platform", "linux/amd64", "ubuntu:24.04", "/bin/true",
], check=True, text=True, capture_output=True)
cid = cid_result.stdout.strip()
if not cid:
    raise SystemExit("docker create returned no container id for vulkaninfo rootfs")
try:
    export = subprocess.Popen(["sudo", "docker", "export", cid], stdout=subprocess.PIPE)
    try:
        run(["sudo", "tar", "-C", VULKANINFO_ROOTFS, "-xf", "-"], stdin=export.stdout)
    finally:
        if export.stdout is not None:
            export.stdout.close()
    export_status = export.wait()
    if export_status != 0:
        raise SystemExit(f"docker export failed with status {export_status}")
finally:
    subprocess.run(["sudo", "docker", "rm", "-f", cid], check=False)

apt_root = Path("/tmp/fex-amd64-apt")
if apt_root.exists():
    shutil.rmtree(apt_root)
for rel in (
    "etc/apt/sources.list.d",
    "var/lib/apt/lists/partial",
    "var/cache/apt/archives/partial",
    "var/lib/dpkg",
    "var/log/apt",
):
    (apt_root / rel).mkdir(parents=True, exist_ok=True)
(apt_root / "var/lib/dpkg/status").write_text("")
(apt_root / "etc/apt/sources.list.d/ubuntu.sources").write_text(
    "Types: deb\n"
    "URIs: http://archive.ubuntu.com/ubuntu/\n"
    "Suites: noble noble-updates\n"
    "Components: main universe\n"
    "Architectures: amd64\n"
    "Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n\n"
    "Types: deb\n"
    "URIs: http://security.ubuntu.com/ubuntu/\n"
    "Suites: noble-security\n"
    "Components: main universe\n"
    "Architectures: amd64\n"
    "Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n"
)
apt_opts = [
    "-o", f"Dir={apt_root}",
    "-o", "APT::Architecture=amd64",
    "-o", "APT::Architectures=amd64",
    "-o", "Acquire::Languages=none",
]
run(["sudo", "apt-get", *apt_opts, "update"])
run([
    "sudo", "apt-get", *apt_opts, "--download-only", "-y", "--no-install-recommends",
    "install", "vulkan-tools", "libx11-6",
])

debs = sorted((apt_root / "var/cache/apt/archives").glob("*.deb"))
if not debs:
    raise SystemExit("isolated amd64 apt state downloaded no packages")
(EVIDENCE / "vulkaninfo-amd64-packages.txt").write_text(
    "\n".join(deb.name for deb in debs) + "\n"
)
for deb in debs:
    run(["sudo", "dpkg-deb", "-x", deb, VULKANINFO_ROOTFS])

vulkaninfo = VULKANINFO_ROOTFS / "usr/bin/vulkaninfo"
if not vulkaninfo.exists():
    raise SystemExit("vulkan-tools rootfs does not contain /usr/bin/vulkaninfo")
run(["file", vulkaninfo])

# The distro package installs its native x86 Vulkan loader at this path. Replace
# only that loader with the rebuilt FEX guest wrapper; the rest of the packaged
# userspace remains untouched.
run(["sudo", "cp", guest_vk, VULKANINFO_ROOTFS / "usr/lib/x86_64-linux-gnu/libvulkan.so.1"])

config_path = Path.home() / ".fex-emu/Config.json"
config = {
    "Config": {
        "RootFS": str(VULKANINFO_ROOTFS),
        "ThunkConfig": str(thunk_config),
    },
    "ThunksDB": {
        "Vulkan": 1,
    },
}
config_path.write_text(json.dumps(config, indent=2) + "\n")

app_env = os.environ.copy()
app_env["VK_DRIVER_FILES"] = str(icd)
app_env["FEX_THUNKHOSTLIBS"] = str(host_vk.parent)
# Remove implicit-layer variability. vulkaninfo's own VK_EXT_debug_report path
# still executes and therefore continues to exercise the routing repair.
app_env["VK_LOADER_LAYERS_DISABLE"] = "~all~"

statuses = []
for attempt in (1, 2):
    app_log = EVIDENCE / f"vulkaninfo-llvmpipe-attempt-{attempt}.log"
    with app_log.open("w") as out:
        app_result = subprocess.run(
            ["timeout", "90s", str(fex_bin), "/usr/bin/vulkaninfo", "--summary"],
            env=app_env,
            stdout=out,
            stderr=subprocess.STDOUT,
        )
    statuses.append(app_result.returncode)
    (EVIDENCE / f"vulkaninfo-llvmpipe-attempt-{attempt}.status").write_text(f"{app_result.returncode}\n")
    app_text = app_log.read_text(errors="replace")
    print(f"===== vulkaninfo llvmpipe attempt {attempt}: status={app_result.returncode} =====")
    print(app_text)

(EVIDENCE / "vulkaninfo-llvmpipe-status-matrix.txt").write_text(
    "\n".join(f"attempt-{idx}={status}" for idx, status in enumerate(statuses, 1)) + "\n"
)

if statuses != [0, 0]:
    raise SystemExit(f"real vulkaninfo llvmpipe gate failed: statuses={statuses}")

print("Real vulkaninfo llvmpipe teardown gate passed twice without preload pinning")