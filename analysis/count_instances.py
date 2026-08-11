#!/usr/bin/env python3
"""网表基础统计 —— Instance / Cell / Port / Net 数量"""

import sys, datalens

if len(sys.argv) < 4:
    print(f"Usage: {sys.argv[0]} <tech.lef> <macro.lef> <design.def>")
    sys.exit(1)

tech_lef, macro_lef, def_file = sys.argv[1], sys.argv[2], sys.argv[3]

datalens.exchange.load_lef([tech_lef, macro_lef])
datalens.exchange.load_def(def_file)

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
