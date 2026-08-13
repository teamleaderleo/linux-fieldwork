#!/usr/bin/env python3
from pathlib import Path
import glob
import os
import subprocess

ROOT = Path.cwd()
FEX = ROOT / "fex-selfpin"
INSTALL = ROOT / "fex-selfpin-install"
ROOTFS = ROOT / "rootfs-selfpin"
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
