#!/usr/bin/env python3
"""时序/组合比分析 + 功能类别图"""

import sys, re, datalens
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans'], 'axes.unicode_minus': False})

if len(sys.argv) < 6:
    print(f"Usage: {sys.argv[0]} <tech.lef> <macro.lef> <design.def> <timing.lib> <output.png>")
    sys.exit(1)

tech_lef, macro_lef, def_file, lib_file, out_png = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]

datalens.exchange.load_lef([tech_lef, macro_lef])
datalens.exchange.load_def(def_file)
datalens.exchange.load_lib([lib_file])

top = datalens.design.present_project().present_module()
insts = top.insts

# 从 LIB 读哪些 cell 是 sequential
lib = datalens.timinglib.current_lib()
seq_cells = set()
if lib:
    for lc in lib.libcell_iter():
        for lp in lc.libpin_iter():
            for t in lp.timing_iter():
                for rp in t.related_pin_iter():
                    seq_cells.add(lc.name)
                    break
                break
            if lc.name in seq_cells:
                break

seq_cnt, comb_cnt = 0, 0
func_agg = Counter()

def func_name(ref):
    m = re.match(r'([A-Z]+[0-9]*)', ref)
    return m.group(1) if m else ref

ref_counter = Counter(i.ref_name for i in insts)
for ref, cnt in ref_counter.items():
    if ref in seq_cells:
        seq_cnt += cnt
    else:
        comb_cnt += cnt
    func_agg[func_name(ref)] += cnt

total = seq_cnt + comb_cnt

print("=" * 60)
print("时序/组合分析")
print("=" * 60)
print(f"{'组合逻辑':<20} {comb_cnt:>6}  ({comb_cnt/total*100:.1f}%)")
print(f"{'时序逻辑':<20} {seq_cnt:>6}  ({seq_cnt/total*100:.1f}%)")
if seq_cnt:
    print(f"{'组合/时序比':<20} {comb_cnt/seq_cnt:.1f} : 1")
print("-" * 60)
for fn, cnt in func_agg.most_common(10):
    print(f"  {fn:<16} {cnt:>6}")
print("=" * 60)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.pie([comb_cnt, seq_cnt], labels=[f'Comb ({comb_cnt})', f'Seq ({seq_cnt})'],
        colors=['#FF9800', '#4CAF50'], startangle=90, explode=(0, 0.05))
ax1.set_title('Seq / Comb Ratio')

top10 = func_agg.most_common(10)
fnames, fcounts = [f for f,_ in top10], [c for _,c in top10]
colors = ['#FF5722' if 'DFF' in f or 'SDFF' in f else '#2196F3' for f in fnames]
ax2.barh(range(len(fnames)), fcounts, color=colors)
ax2.set_yticks(range(len(fnames)))
ax2.set_yticklabels(fnames)
ax2.set_xlabel('Count'); ax2.set_title('Top Cell Functions')
ax2.invert_yaxis()

plt.suptitle('Seq / Comb Analysis')
plt.tight_layout()
plt.savefig(out_png, dpi=150)
print(f"Saved: {out_png}")
