#!/usr/bin/env python3
"""GCD 逻辑分析: 时序/组合比 + 逻辑锥 + 大扇出网线"""
import sys, os
import datalens
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict, Counter

netlist = sys.argv[1] if len(sys.argv) > 1 else "/home/shared/benchmarks/nangate45_3D/gcd/2_2_floorplan_io.v"

datalens.exchange.load_netlist([netlist])
project = datalens.design.present_project()
project.make_unique()
top = project.present_module()

# === 1. 时序 vs 组合分类 ===
reg_prefixes = ('DFF', 'SDFF', 'DLAT', 'SEDFF', 'RSDFF')
seq_cells = []
comb_cells = []

for inst in top.inst_iter():
    ref = inst.ref_name
    is_seq = any(ref.startswith(p) for p in reg_prefixes)
    if is_seq:
        seq_cells.append(inst)
    else:
        comb_cells.append(inst)

seq_count = len(seq_cells)
comb_count = len(comb_cells)

# === 2. 高扇出网线分析 ===
net_fanout = {}
for net in top.net_iter():
    cnt = sum(1 for _ in net.pin_iter())
    net_fanout[net.name] = cnt

high_fo_nets = sorted(net_fanout.items(), key=lambda x: -x[1])[:10]

# === Plot ===
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Seq vs Comb pie
ax = axes[0, 0]
labels = [f'Comb ({comb_count})', f'Seq ({seq_count})']
sizes = [comb_count, seq_count]
colors = ['#5B9BD5', '#ED7D31']
ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, explode=(0, 0.05))
ax.set_title('Sequential vs Combinational')

# 2. High fanout nets
ax = axes[0, 1]
fo_names = [n[0][:20] for n in high_fo_nets]
fo_counts = [n[1] for n in high_fo_nets]
ax.barh(range(len(fo_names)), fo_counts, color='coral')
ax.set_yticks(range(len(fo_names)))
ax.set_yticklabels(fo_names, fontsize=8)
ax.invert_yaxis()
ax.set_xlabel('Fanout')
ax.set_title(f'Top 10 High Fanout Nets\nMax FO = {max(net_fanout.values())}')
for i, c in enumerate(fo_counts):
    ax.text(c + 0.5, i, str(c), va='center', fontsize=8)

# 3. Cell type by category
ax = axes[1, 0]
# Group by cell prefix category
categories = defaultdict(int)
for inst in top.inst_iter():
    ref = inst.ref_name
    # Extract base function
    base = ref.split('_')[0].split('X')[0]
    categories[base] += 1

top_cats = sorted(categories.items(), key=lambda x: -x[1])[:8]
ax.barh(range(len(top_cats)), [c[1] for c in top_cats], color='teal')
ax.set_yticks(range(len(top_cats)))
ax.set_yticklabels([c[0] for c in top_cats])
ax.invert_yaxis()
ax.set_xlabel('Count')
ax.set_title('Cell Function Categories')

# 4. Summary
ax = axes[1, 1]
ax.axis('off')
fpga_like = comb_count / max(seq_count, 1)
summary = f"""Design: {top.name}

=== Circuit Type ===
Comb:  {comb_count} ({comb_count/(comb_count+seq_count)*100:.1f}%)
Seq:   {seq_count} ({seq_count/(comb_count+seq_count)*100:.1f}%)
C/S ratio: {fpga_like:.1f}:1

=== Connectivity ===
Total nets:  {len(net_fanout)}
Max fanout:  {max(net_fanout.values())}
Avg fanout:  {np.mean(list(net_fanout.values())):.1f}

=== Top Cell Types ===
"""
for i, (cat, cnt) in enumerate(top_cats[:5]):
    summary += f"  {cat}: {cnt}\n"

ax.text(0.05, 0.95, summary, transform=ax.transAxes, fontsize=9,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

fig.suptitle('GCD Logic Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()

outfile = os.path.expanduser('~/gcd_logic_analysis.png')
plt.savefig(outfile, dpi=150, bbox_inches='tight')
print(f'Saved: {outfile}')
print(f'Seq: {seq_count}, Comb: {comb_count}, Ratio: {fpga_like:.1f}:1')
print(f'Top cells: {[(c[0], c[1]) for c in top_cats[:5]]}')

project.destroy()
