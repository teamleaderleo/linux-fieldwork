#!/usr/bin/env python3
from pathlib import Path

transform = Path('investigations/fex-vulkan-thunk-lifecycle/apply_customir_retirement_probe.py')
s = transform.read_text()
old_anchor = '#include <unistd.h>\\n\\nnamespace FEX::HLE {\\n'
new_anchor = '#include <Linux/Utils/ELFParser.h>\\n\\nnamespace FEX::HLE {\\n'
if s.count(old_anchor) != 1:
    raise SystemExit(f'expected one stale include anchor, found {s.count(old_anchor)}')
s = s.replace(old_anchor, new_anchor, 1)
old_replacement = '#include <unistd.h>\\n\\nnamespace FEXCore::Context {\\n'
new_replacement = '#include <Linux/Utils/ELFParser.h>\\n\\nnamespace FEXCore::Context {\\n'
if s.count(old_replacement) != 1:
    raise SystemExit(f'expected one stale include replacement, found {s.count(old_replacement)}')
transform.write_text(s.replace(old_replacement, new_replacement, 1))

gate = Path('investigations/fex-vulkan-thunk-lifecycle/run_customir_retirement_ci.sh')
s = gate.read_text()
old_marker = "marker = '\\n}\\nLOAD_LIB_INIT(libvulkan, OnInit)'"
new_marker = "marker = '\\n}\\n\\nLOAD_LIB_INIT(libvulkan, OnInit)'"
if s.count(old_marker) != 1:
    raise SystemExit(f'expected one Vulkan OnInit marker, found {s.count(old_marker)}')
s = s.replace(old_marker, new_marker, 1)
old_host = 'HOST_VK=$(find "$INSTALL" -type f -name libvulkan-host.so | head -1)'
new_host = 'HOST_VK="$INSTALL/lib/fex-emu/HostThunks/libvulkan-host.so"'
if s.count(old_host) != 1:
    raise SystemExit(f'expected one host thunk selector, found {s.count(old_host)}')
gate.write_text(s.replace(old_host, new_host, 1))

print('Prepared corrected FEX-2608 CustomIR differential harness')
