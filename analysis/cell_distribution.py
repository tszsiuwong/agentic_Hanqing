#!/usr/bin/env python3
"""GCD 网表分析 + 可视化"""
import sys, os
import datalens
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

netlist = sys.argv[1] if len(sys.argv) > 1 else "/home/shared/benchmarks/nangate45_3D/gcd/2_2_floorplan_io.v"

datalens.exchange.load_netlist([netlist])
project = datalens.design.present_project()
project.make_unique()
top = project.present_module()

# 按 ref_name 统计
ref_count = {}
for inst in top.inst_iter():
    ref = inst.ref_name
    ref_count[ref] = ref_count.get(ref, 0) + 1

sorted_refs = sorted(ref_count.items(), key=lambda x: -x[1])
labels = [r[0] for r in sorted_refs]
counts = [r[1] for r in sorted_refs]

total = sum(counts)
total_leaf = top.inst_count(datalens.design.HierFilterType.LEAF)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 左图: 柱状图 top 15
top_n = 15
ax1 = axes[0]
colors = plt.cm.Blues(np.linspace(0.4, 0.9, top_n))
bars = ax1.barh(range(top_n), counts[:top_n], color=colors)
ax1.set_yticks(range(top_n))
ax1.set_yticklabels(labels[:top_n])
ax1.invert_yaxis()
ax1.set_xlabel('Count')
ax1.set_title(f'GCD Top {top_n} Cell Types')
for i, (bar, c) in enumerate(zip(bars, counts[:top_n])):
    ax1.text(bar.get_width() + 1, bar.get_y() + 0.3, str(c), fontsize=9)

# 右图: 饼图
ax2 = axes[1]
pie_labels = []
pie_sizes = []
other = 0
for name, cnt in sorted_refs:
    if cnt >= 3:
        pie_labels.append(f'{name} ({cnt})')
        pie_sizes.append(cnt)
    else:
        other += cnt
if other:
    pie_labels.append(f'Other ({other})')
    pie_sizes.append(other)

wedges, texts, autotexts = ax2.pie(
    pie_sizes, labels=pie_labels, autopct='%1.1f%%',
    startangle=90, textprops={'fontsize': 7}
)
ax2.set_title(f'GCD Cell Distribution\nTotal: {total} instances, {len(sorted_refs)} types')

fig.suptitle(f'Design: {top.name}  |  Leaf: {total_leaf}  |  Ports: {top.port_count()}  |  Nets: {top.net_count()}',
             fontsize=12, fontweight='bold')
plt.tight_layout()

outfile = os.path.expanduser('~/gcd_analysis.png')
plt.savefig(outfile, dpi=150, bbox_inches='tight')
print(f'Saved: {outfile}')
print(f'Total: {total} instances, {len(sorted_refs)} types, Ports: {top.port_count()}, Nets: {top.net_count()}')

project.destroy()
