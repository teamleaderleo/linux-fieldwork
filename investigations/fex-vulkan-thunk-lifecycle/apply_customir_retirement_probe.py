#!/usr/bin/env python3
"""Apply the narrow FEX-2608 CustomIR unload diagnostic.

This is research code for the owned teamleaderleo/FEX fork. It deliberately
answers one question only: can a thunk-created CustomIR H->T bridge survive
past removal of the guest mapping that contains T?

The transformation:
  * records newly-created thunk CustomIR mappings as (Context, H, T);
  * logs thunk CustomIR compilation/hits;
  * exposes a translation-unit-local retirement entrypoint;
  * before GuestMunmap physically unmaps a range, retires every recorded H
    whose T overlaps that range by calling the existing RemoveCustomIREntrypoint(H).

It does not claim to solve host->guest callback trampolines, DSO generations,
alias ownership, or an already-selected H->T transition racing with unmap.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_core(path: Path) -> None:
    text = path.read_text()

    hit_old = """    if (Handler != CustomIRHandlers.end()) {\n      TotalInstructions = 1;\n      TotalInstructionsLength = 1;\n      Handler->second.Handler(GuestRIP, Thread->OpDispatcher.get());\n"""
    hit_new = """    if (Handler != CustomIRHandlers.end()) {\n      if (Handler->second.Creator == ThunkHandler) {\n        LogMan::Msg::IFmt(\"THUNK_LIFETIME CUSTOMIR_HIT H={:#x} T={}\", GuestRIP, fmt::ptr(Handler->second.Data));\n      }\n      TotalInstructions = 1;\n      TotalInstructionsLength = 1;\n      Handler->second.Handler(GuestRIP, Thread->OpDispatcher.get());\n"""
    text = replace_once(text, hit_old, hit_new, "CustomIR hit instrumentation")

    add_anchor = "void ContextImpl::AddThunkTrampolineIRHandler(uintptr_t Entrypoint, uintptr_t GuestThunkEntrypoint) {\n"
    registry = """struct ThunkTrampolineRegistration {\n  ContextImpl* Owner;\n  uintptr_t HostEntrypoint;\n  uintptr_t GuestTarget;\n};\n\nstatic std::mutex ThunkTrampolineRegistrationMutex;\nstatic fextl::vector<ThunkTrampolineRegistration> ThunkTrampolineRegistrations;\n\n""" + add_anchor
    text = replace_once(text, add_anchor, registry, "registration registry")

    result_anchor = """    ThunkHandler, (void*)GuestThunkEntrypoint);\n\n  if (Result.has_value()) {\n"""
    result_replacement = """    ThunkHandler, (void*)GuestThunkEntrypoint);\n\n  if (!Result.has_value()) {\n    std::scoped_lock lk(ThunkTrampolineRegistrationMutex);\n    ThunkTrampolineRegistrations.push_back({this, Entrypoint, GuestThunkEntrypoint});\n    LogMan::Msg::IFmt(\"THUNK_LIFETIME REGISTER H={:#x} T={:#x}\", Entrypoint, GuestThunkEntrypoint);\n  }\n\n  if (Result.has_value()) {\n"""
    text = replace_once(text, result_anchor, result_replacement, "registration capture")

    retirement_anchor = "void ContextImpl::AddForceTSOInformation(const IntervalList<uint64_t>& ValidRanges, fextl::set<uint64_t>&& Instructions) {\n"
    retirement = """void RemoveThunkTrampolineIRHandlersInRange(FEXCore::Context::Context* CTX, FEXCore::Core::InternalThreadState* Thread,\n                                                  uintptr_t Start, uintptr_t Length) {\n  if (!CTX || !Thread || Length == 0) {\n    return;\n  }\n\n  auto Impl = static_cast<ContextImpl*>(CTX);\n  fextl::vector<uintptr_t> EntrypointsToRetire;\n\n  {\n    std::scoped_lock lk(ThunkTrampolineRegistrationMutex);\n    auto It = ThunkTrampolineRegistrations.begin();\n    while (It != ThunkTrampolineRegistrations.end()) {\n      const bool SameContext = It->Owner == Impl;\n      const bool TargetInRange = It->GuestTarget >= Start && It->GuestTarget - Start < Length;\n      if (SameContext && TargetInRange) {\n        LogMan::Msg::IFmt(\"THUNK_LIFETIME RETIRE H={:#x} T={:#x} range={:#x}+{:#x}\",\n                          It->HostEntrypoint, It->GuestTarget, Start, Length);\n        EntrypointsToRetire.push_back(It->HostEntrypoint);\n        It = ThunkTrampolineRegistrations.erase(It);\n      } else {\n        ++It;\n      }\n    }\n  }\n\n  for (const auto Entrypoint : EntrypointsToRetire) {\n    Impl->RemoveCustomIREntrypoint(Thread, Entrypoint);\n  }\n}\n\n""" + retirement_anchor
    text = replace_once(text, retirement_anchor, retirement, "pre-unmap retirement function")

    path.write_text(text)


def patch_munmap(path: Path) -> None:
    text = path.read_text()

    include_anchor = "#include <unistd.h>\n\nnamespace FEX::HLE {\n"
    include_replacement = """#include <unistd.h>\n\nnamespace FEXCore::Context {\nvoid RemoveThunkTrampolineIRHandlersInRange(FEXCore::Context::Context* CTX, FEXCore::Core::InternalThreadState* Thread,\n                                             uintptr_t Start, uintptr_t Length);\n}\n\nnamespace FEX::HLE {\n"""
    text = replace_once(text, include_anchor, include_replacement, "retirement forward declaration")

    munmap_anchor = """  uint64_t Result;\n  uint64_t Size = FEXCore::AlignUp(length, FEXCore::Utils::FEX_PAGE_SIZE);\n  bool PendingResourceDeletion;\n\n  {\n"""
    munmap_replacement = """  uint64_t Result;\n  uint64_t Size = FEXCore::AlignUp(length, FEXCore::Utils::FEX_PAGE_SIZE);\n  bool PendingResourceDeletion;\n\n  // Retire host-keyed thunk bridges while the guest target is still mapped.\n  if (Thread && Size) {\n    FEXCore::Context::RemoveThunkTrampolineIRHandlersInRange(\n      CTX, Thread, reinterpret_cast<uintptr_t>(addr), Size);\n  }\n\n  {\n"""
    text = replace_once(text, munmap_anchor, munmap_replacement, "GuestMunmap pre-unmap hook")
    path.write_text(text)


def patch_vulkan_guest(path: Path) -> None:
    text = path.read_text()
    start = text.find("void OnInit() {")
    if start < 0:
        raise SystemExit("Vulkan Guest.cpp: OnInit start not found")
    end_marker = "\n}\nLOAD_LIB_INIT(libvulkan, OnInit)"
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit("Vulkan Guest.cpp: OnInit end not found")
    replacement = "void OnInit() {}" + end_marker[len("\n}"):]
    text = text[:start] + replacement + text[end + len(end_marker):]
    path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fex_root", type=Path)
    parser.add_argument("--isolate-vulkan-callbacks", action="store_true")
    args = parser.parse_args()

    root = args.fex_root.resolve()
    patch_core(root / "FEXCore/Source/Interface/Core/Core.cpp")
    patch_munmap(root / "Source/Tools/LinuxEmulation/LinuxSyscalls/SyscallsSMCTracking.cpp")
    if args.isolate_vulkan_callbacks:
        patch_vulkan_guest(root / "ThunkLibs/libvulkan/Guest.cpp")

    print("Applied narrow CustomIR pre-unmap retirement diagnostic")


if __name__ == "__main__":
    main()
