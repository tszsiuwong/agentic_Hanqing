#!/usr/bin/env python3
"""Step 1: 纯网表基础统计 —— .v 或 .def 均可"""

import sys, os, datalens
from collections import Counter

if len(sys.argv) < 2:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> [tech.lef macro.lef ...]")
    sys.exit(1)

main_file = sys.argv[1]

if main_file.endswith('.v') or main_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([main_file])
else:
    lef_files = sys.argv[2:] if len(sys.argv) > 2 else []
    if lef_files: datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(main_file)

top = datalens.design.present_project().present_module()
insts = top.insts
ref_counter = Counter(i.ref_name for i in insts)

total = len(insts)
print("=" * 50)
print("基础统计")
print("=" * 50)
print(f"  Instance:   {total}")
print(f"  Cell 类型:  {len(ref_counter)}")
print(f"  Port:       {top.port_count()}")
print(f"  Net:        {top.net_count()}")
print("=" * 50)
