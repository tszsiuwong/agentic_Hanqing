#!/usr/bin/env python3
"""Step 3: 时序/组合分析 —— 需要 .lib"""

import sys, os, re, datalens
from collections import Counter

if len(sys.argv) < 5:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> <tech.lef> <macro.lef> <timing.lib>")
    sys.exit(1)

design_file, tlef, mlef, lib_file = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

datalens.exchange.load_lef([tlef, mlef])
if design_file.endswith('.v') or design_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([design_file])
else:
    datalens.exchange.load_def(design_file)
datalens.exchange.load_lib([lib_file])

top = datalens.design.present_project().present_module()
ref_counter = Counter(i.ref_name for i in top.insts)
total = len(top.insts)

# 从 LIB 判断 sequential
lib = datalens.timinglib.current_lib()
seq_cells = set()
if lib:
    for lc in lib.libcell_iter():
        is_seq = False
        try:
            for lp in lc.libpin_iter():
                for t in lp.timing_iter():
                    is_seq = True
                    break
                if is_seq: break
        except: pass
        if is_seq:
            seq_cells.add(lc.name)

seq_cnt = sum(c for r, c in ref_counter.items() if r in seq_cells)
comb_cnt = total - seq_cnt

# 功能分组
def func_name(ref):
    m = re.match(r'([A-Z]+[0-9]*)', ref)
    return m.group(1) if m else ref
func_agg = Counter()
for ref, cnt in ref_counter.items():
    func_agg[func_name(ref)] += cnt

print("=" * 50)
print("时序/组合分析")
print("=" * 50)
print(f"  组合逻辑:  {comb_cnt}  ({comb_cnt/total*100:.1f}%)")
print(f"  时序逻辑:  {seq_cnt}  ({seq_cnt/total*100:.1f}%)")
if seq_cnt:
    print(f"  组合/时序比: {comb_cnt/seq_cnt:.1f} : 1")
print("-" * 50)
print(f"  {'功能类别':<20} {'数量':>6}")
print("-" * 50)
for fn, cnt in func_agg.most_common():
    print(f"  {fn:<20} {cnt:>6}")
print("=" * 50)
