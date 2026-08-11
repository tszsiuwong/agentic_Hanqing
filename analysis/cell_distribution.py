#!/usr/bin/env python3
"""网表单元分布可视化"""
import sys, os, time
t0 = time.time()
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from src.dizo_utils import load_netlist, count_by_ref

netlist = sys.argv[1] if len(sys.argv) > 1 else "/home/shared/benchmarks/nangate45_3D/gcd/2_2_floorplan_io.v"
project, top = load_netlist(netlist)

refs = count_by_ref(top)
sorted_refs = sorted(refs.items(), key=lambda x: -x[1])
labels = [r[0] for r in sorted_refs]
counts = [r[1] for r in sorted_refs]
total = sum(counts)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 左图: Top 15
top_n = 15
colors = plt.cm.Blues(np.linspace(0.4, 0.9, top_n))
ax1 = axes[0]
ax1.barh(range(top_n), counts[:top_n], color=colors)
ax1.set_yticks(range(top_n))
ax1.set_yticklabels(labels[:top_n])
ax1.invert_yaxis()
ax1.set_xlabel('Count')
ax1.set_title(f'{top.name}  Top {top_n} Cell Types')
for i, c in enumerate(counts[:top_n]):
    ax1.text(c + max(counts[:top_n])*0.01, i, str(c), fontsize=9, va='center')

# 右图: 饼图
ax2 = axes[1]
pie_labels, pie_sizes = [], []
other = 0
for name, cnt in sorted_refs:
    if cnt >= total * 0.005:  # >0.5%
        pie_labels.append(f'{name} ({cnt})')
        pie_sizes.append(cnt)
    else:
        other += cnt
if other > 0:
    pie_labels.append(f'Other ({other})')
    pie_sizes.append(other)
ax2.pie(pie_sizes, labels=pie_labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 7})
ax2.set_title(f'{top.name}  |  {total} inst  |  {len(refs)} types  |  {top.port_count()} ports  |  {top.net_count()} nets')

plt.tight_layout()
out = os.path.expanduser(f'~/{top.name}_cells.png')
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f'Saved: {out}  [{time.time()-t0:.1f}s]')
project.destroy()
