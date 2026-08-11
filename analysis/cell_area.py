#!/usr/bin/env python3
"""Step 2: 单元面积/几何 —— 需要 tech.lef + macro.lef"""

import sys, os, datalens
from collections import Counter

if len(sys.argv) < 4:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> <tech.lef> <macro.lef> [...]")
    sys.exit(1)

design_file = sys.argv[1]
lef_files = sys.argv[2:]

datalens.exchange.load_lef(lef_files)
if design_file.endswith('.v') or design_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([design_file])
else:
    datalens.exchange.load_def(design_file)

top = datalens.design.present_project().present_module()
insts = top.insts
ref_counter = Counter(i.ref_name for i in insts)

tech = None
try:    tech = datalens.phylib.present_tech()
except: tech = top.tech()

total_area = 0.0
area_by_ref = {}
for inst in insts:
    ref = inst.ref_name
    if ref not in area_by_ref:
        try:
            macro = tech.macro(ref) if tech else None
            area_by_ref[ref] = macro.area() if macro else 0
        except:
            area_by_ref[ref] = 0
    total_area += area_by_ref[ref]

known = sum(1 for v in area_by_ref.values() if v > 0)
print("=" * 60)
print("单元面积分析")
print("=" * 60)
print(f"  可用 Macro:  {known}/{len(ref_counter)} 种")
print(f"  总面积:      {total_area:.2f} µm²  ({total_area/len(insts):.2f} /个)" if insts else "0")
print("=" * 60)

area_top = sorted(((r, a, ref_counter[r]) for r, a in area_by_ref.items() if a > 0),
                   key=lambda x: -x[1]*x[2])[:10]
if area_top:
    print(f"\n  {'Cell':<24} {'面积(µm²)':>10} {'数量':>6} {'总面积':>10}")
    print("  " + "-" * 52)
    for ref, area, cnt in area_top:
        print(f"  {ref:<24} {area:>10.3f} {cnt:>6} {area*cnt:>10.2f}")
