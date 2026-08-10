#!/usr/bin/env python3
"""GCD 逻辑分析: 时序/组合比 + 高扇出"""
import sys, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter, defaultdict
from dizo_utils import load_netlist, classify_seq_comb, get_net_fanouts, get_top_fanout_nets, get_cell_categories

netlist = sys.argv[1] if len(sys.argv) > 1 else "/home/shared/benchmarks/nangate45_3D/gcd/2_2_floorplan_io.v"
project, top = load_netlist(netlist)

seq_cells, comb_cells = classify_seq_comb(top)
net_fanouts = get_net_fanouts(top)
high_fo = get_top_fanout_nets(top, 10)
cats = get_cell_categories(top, 8)

seq_n, comb_n = len(seq_cells), len(comb_cells)
total = seq_n + comb_n

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Seq vs Comb
ax = axes[0, 0]
ax.pie([comb_n, seq_n], labels=[f'Comb ({comb_n})', f'Seq ({seq_n})'],
       colors=['#5B9BD5', '#ED7D31'], autopct='%1.1f%%', startangle=90, explode=(0, 0.05))
ax.set_title('Sequential vs Combinational')

# 2. High fanout nets
ax = axes[0, 1]
fo_names = [n[0][:20] for n in high_fo]; fo_cnt = [n[1] for n in high_fo]
ax.barh(range(len(fo_names)), fo_cnt, color='coral')
ax.set_yticks(range(len(fo_names))); ax.set_yticklabels(fo_names, fontsize=8); ax.invert_yaxis()
ax.set_xlabel('Fanout'); ax.set_title(f'Top 10 High Fanout Nets')

# 3. Cell categories
ax = axes[1, 0]
items = list(cats.items())
ax.barh(range(len(items)), [c[1] for c in items], color='teal')
ax.set_yticks(range(len(items))); ax.set_yticklabels([c[0] for c in items]); ax.invert_yaxis()
ax.set_title('Cell Function Categories')

# 4. Summary
ax = axes[1, 1]; ax.axis('off')
ax.text(0.05, 0.95,
    f"Design: {top.name}\n\nSeq: {seq_n} ({seq_n/total*100:.1f}%)\nComb: {comb_n} ({comb_n/total*100:.1f}%)\nC/S ratio: {comb_n/max(seq_n,1):.1f}:1\n\nFanout: μ={np.mean(net_fanouts):.1f} max={max(net_fanouts)}\nTotal nets: {len(net_fanouts)}\n\nTop: {', '.join(f'{c[0]}({c[1]})' for c in list(cats.items())[:5])}",
    transform=ax.transAxes, fontsize=9, verticalalignment='top',
    fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightyellow'))

fig.suptitle('GCD Logic Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()
out = os.path.expanduser('~/gcd_logic_analysis.png')
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f'Saved: {out}\nSeq: {seq_n} Comb: {comb_n} Ratio: {comb_n/max(seq_n,1):.1f}:1')
project.destroy()
