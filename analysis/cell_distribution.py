#!/usr/bin/env python3
"""单元分布分析 + 柱状图 —— 支持 DEF 或 Verilog"""

import sys, datalens
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans'], 'axes.unicode_minus': False})

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <design.def|design.v> <output.png> [tech.lef macro.lef ...]")
    sys.exit(1)

main_file, out_png = sys.argv[1], sys.argv[2]

if main_file.endswith('.v') or main_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([main_file])
elif main_file.endswith('.def'):
    lef_files = sys.argv[3:] if len(sys.argv) > 3 else []
    datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(main_file)
else:
    print(f"Unknown format: {main_file}")
    sys.exit(1)

top = datalens.design.present_project().present_module()
counter = Counter(i.ref_name for i in top.insts)
sorted_cells = counter.most_common()
total = sum(c for _, c in sorted_cells)

print("=" * 60)
print(f"{'Cell 类型':<28} {'数量':>6} {'占比':>8}")
print("-" * 60)
for name, count in sorted_cells:
    print(f"{name:<28} {count:>6} {count/total*100:>7.1f}%")
print("=" * 60)
print(f"{'总计':<28} {total:>6}")

top3 = sorted_cells[:3]
if top3:
    print(f"\nTop 3 ({', '.join(n for n,_ in top3)}) = {sum(c for _,c in top3)/total*100:.0f}%")

names = [n for n, _ in sorted_cells]
counts = [c for _, c in sorted_cells]
colors = ['#FF5722' if i < 3 else '#2196F3' for i in range(len(names))]

plt.figure(figsize=(max(12, len(names)*0.35), 5))
bars = plt.bar(range(len(names)), counts, color=colors)
plt.xticks(range(len(names)), names, rotation=45, ha='right', fontsize=8)
plt.ylabel('Count')
plt.title('Cell Distribution')
for bar, c in zip(bars, counts):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(counts)*0.005,
             str(c), ha='center', va='bottom', fontsize=6)
plt.tight_layout()
plt.savefig(out_png, dpi=150)
print(f"Saved: {out_png}")
