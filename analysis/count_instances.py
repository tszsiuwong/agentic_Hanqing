#!/usr/bin/env python3
"""网表基础统计 —— 支持 DEF 或 Verilog 输入"""

import sys, datalens

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <design.def> [tech.lef macro.lef ...]")
    print(f"   or: {sys.argv[0]} <design.v>")
    sys.exit(1)

main_file = sys.argv[1]

if main_file.endswith('.v') or main_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([main_file])
elif main_file.endswith('.def'):
    lef_files = sys.argv[2:] if len(sys.argv) > 2 else []
    datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(main_file)
else:
    print(f"Unknown format: {main_file}")
    sys.exit(1)

top = datalens.design.present_project().present_module()

all_insts = top.insts
cell_types = set(i.ref_name for i in all_insts)

print("=" * 50)
print("网表基础统计")
print("=" * 50)
print(f"{'总 Instance':<16} {len(all_insts):>6}")
print(f"{'Cell 类型':<16} {len(cell_types):>6}")
print(f"{'Port':<16} {top.port_count():>6}")
print(f"{'Net':<16} {top.net_count():>6}")
print("=" * 50)
