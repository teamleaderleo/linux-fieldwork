#!/usr/bin/env python3
"""Apply the hosted-tested instance-create callback-suppression candidate to FEX.

Internal investigation helper only. This script intentionally applies one narrow
change to ThunkLibs/libvulkan/Host.cpp:

- suppress VK_EXT_debug_utils temporary instance-create callbacks in the same
  way FEX already suppresses VK_EXT_debug_report callbacks; and
- re-check the same pNext predecessor after removal so consecutive callback
  nodes are all filtered.

Tested base:
  c011366706eaf65a00380003989b3a10811212b6

Passing hosted receipt:
  Actions run 31791153300
  artifact 9215745861
  SHA-256 62bf88eda859a8612bce0b86894809b681485224fd977baa37cb50836e78bc33

This is experimental Fieldwork machinery, not an upstream submission artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path


OLD = """  const VkInstanceCreateInfo* vk_struct_base = a_0;
  for (const VkBaseInStructure* vk_struct = reinterpret_cast<const VkBaseInStructure*>(vk_struct_base); vk_struct->pNext;
       vk_struct = vk_struct->pNext) {
    // Override guest callbacks used for VK_EXT_debug_report
    if (reinterpret_cast<const VkBaseInStructure*>(vk_struct->pNext)->sType == VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT) {
      // Overwrite the pNext pointer, ignoring its const-qualifier
      const_cast<VkBaseInStructure*>(vk_struct)->pNext = vk_struct->pNext->pNext;

      // If we copied over a nullptr for pNext then early exit
      if (!vk_struct->pNext) {
        break;
      }
    }
  }
"""

NEW = """  const VkInstanceCreateInfo* vk_struct_base = a_0;
  for (const VkBaseInStructure* vk_struct = reinterpret_cast<const VkBaseInStructure*>(vk_struct_base); vk_struct->pNext;) {
    const auto next_type = vk_struct->pNext->sType;
    // Ignore guest callbacks installed for temporary debug callbacks during instance creation.
    if (next_type == VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT ||
        next_type == VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT) {
      // Overwrite the pNext pointer, ignoring its const-qualifier. Re-check the same
      // predecessor so consecutive callback-bearing nodes are all removed.
      const_cast<VkBaseInStructure*>(vk_struct)->pNext = vk_struct->pNext->pNext;
      continue;
    }
    vk_struct = vk_struct->pNext;
  }
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        nargs="?",
        default=".",
        help="FEX source tree root (default: current directory)",
    )
    args = parser.parse_args()

    path = Path(args.source) / "ThunkLibs/libvulkan/Host.cpp"
    text = path.read_text()

    if NEW in text:
        print(f"candidate already present: {path}")
        return 0

    if OLD not in text:
        raise SystemExit(
            "expected c0113667-era vkCreateInstance callback filter not found; "
            "refusing to apply against an unknown source shape"
        )

    path.write_text(text.replace(OLD, NEW, 1))
    print(f"applied instance pNext callback-suppression candidate: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
