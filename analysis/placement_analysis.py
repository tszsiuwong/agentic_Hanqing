#!/usr/bin/env python3
"""Step 4: 物理 placement 分析 —— 需要 DEF + tech.lef + macro.lef"""

import sys, os, datalens
from collections import Counter

if len(sys.argv) < 4:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.def> <tech.lef> <macro.lef> [...]")
    sys.exit(1)

def_file = sys.argv[1]
lef_files = sys.argv[2:]

datalens.exchange.load_lef(lef_files)
datalens.exchange.load_def(def_file)

top = datalens.design.present_project().present_module()
insts = []
for module in datalens.design.module_iter():
    for inst in module.inst_iter(False):
        insts.append(inst)

# placement 状态
placed = unplaced = fixed = 0
for inst in insts:
    try:
        ps = str(inst.place_status())
    except:
        ps = 'UNKNOWN'
    if ps == 'FIXED' or ps == 'COVER':
        fixed += 1
    elif ps == 'UNPLACED':
        unplaced += 1
    else:
        placed += 1

print("=" * 50)
print("Placement 分析")
print("=" * 50)
print(f"  Instance:   {len(insts)}")
print(f"  Placed:     {placed}")
print(f"  Fixed:      {fixed}")
print(f"  Unplaced:   {unplaced}")

# Row 信息
try:
    rows = list(top.site_array_iter())
    print(f"  Rows:       {len(rows)}")
    if rows:
        r = rows[0]
        print(f"  Site:       {r.site_name()}")
        print(f"  Site size:  {r.site_width()} × {r.site_height()}")
except Exception:
    print(f"  Rows:       N/A")

# 面积/利用率
try:
    tech = datalens.phylib.present_tech()
except:
    tech = top.tech()

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

if total_area > 0:
    try:
        bbox = top.bbox()
        die_w = (bbox.xh() - bbox.xl()) / 2000
        die_h = (bbox.yh() - bbox.yl()) / 2000
        die_area = die_w * die_h
        util = total_area / die_area * 100
        print(f"  Die:        {die_w:.0f} × {die_h:.0f} = {die_area:.0f} µm²")
        print(f"  Cell area:  {total_area:.0f} µm²")
        print(f"  利用率:     {util:.1f}%")
    except:
        print(f"  Cell area:  {total_area:.0f} µm²")
print("=" * 50)
