#!/usr/bin/env python3
"""Apply the non-mutating Vulkan instance-create callback filter candidate.

Experimental Fieldwork helper. Tested base shape:
  c011366706eaf65a00380003989b3a10811212b6

The candidate:
- suppresses temporary VK_EXT_debug_report and VK_EXT_debug_utils guest callbacks;
- removes consecutive callback-bearing pNext nodes safely; and
- restores every temporarily modified pNext link in reverse order immediately
  after native vkCreateInstance returns.

This script is internal investigation machinery, not an upstream submission artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", default=".")
    args = parser.parse_args()

    path = Path(args.source) / "ThunkLibs/libvulkan/Host.cpp"
    text = path.read_text()

    marker = "std::vector<PNextRestore> pnext_restore;"
    if marker in text and "VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT" in text:
        print(f"restoration candidate already present: {path}")
        return 0

    fn = text.index("FEXFN_IMPL(vkCreateInstance)")
    start = text.index("  const VkInstanceCreateInfo* vk_struct_base = a_0;", fn)
    end = text.index("\n\n  VkInstance out;", start)

    old_region = text[start:end]
    if "VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT" not in old_region:
        raise SystemExit("expected debug-report instance-create filter not found")

    new_region = """  struct PNextRestore {
    VkBaseInStructure* Structure;
    const VkBaseInStructure* PNext;
  };

  std::vector<PNextRestore> pnext_restore;
  const VkInstanceCreateInfo* vk_struct_base = a_0;
  for (const VkBaseInStructure* vk_struct = reinterpret_cast<const VkBaseInStructure*>(vk_struct_base); vk_struct->pNext;) {
    const auto next_type = vk_struct->pNext->sType;
    // Ignore guest callbacks installed for temporary debug callbacks during instance creation.
    if (next_type == VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT ||
        next_type == VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT) {
      // Temporarily splice the callback-bearing node out. Re-check the same predecessor
      // so consecutive callback nodes are all removed.
      auto* mutable_struct = const_cast<VkBaseInStructure*>(vk_struct);
      pnext_restore.push_back({mutable_struct, mutable_struct->pNext});
      mutable_struct->pNext = mutable_struct->pNext->pNext;
      continue;
    }
    vk_struct = vk_struct->pNext;
  }"""

    text = text[:start] + new_region + text[end:]

    call = "auto ret = LDR_PTR(vkCreateInstance)(vk_struct_base, nullptr, &out);"
    call_pos = text.index(call, fn)
    insert_at = call_pos + len(call)
    restore = """

  for (auto it = pnext_restore.rbegin(); it != pnext_restore.rend(); ++it) {
    it->Structure->pNext = it->PNext;
  }"""
    text = text[:insert_at] + restore + text[insert_at:]

    path.write_text(text)
    print(f"applied non-mutating instance pNext callback candidate: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
