#!/usr/bin/env python3
"""连接度分析: Degree / Fanout / Rent's Rule"""
import sys, os, time
t0 = time.time()
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
from src.dizo_utils import load_netlist, count_by_ref, get_inst_degrees, get_net_fanouts, get_cell_categories

netlist = sys.argv[1] if len(sys.argv) > 1 else "/home/shared/benchmarks/nangate45_3D/gcd/2_2_floorplan_io.v"
project, top = load_netlist(netlist)

refs = count_by_ref(top)
inst_degrees = get_inst_degrees(top)
net_fanouts = get_net_fanouts(top)
cell_cats = get_cell_categories(top, 12)

degree_counter = Counter(inst_degrees)
fanout_counter = Counter(net_fanouts)

fig, axes = plt.subplots(2, 3, figsize=(18, 10))

# 1. Instance Degree Distribution
ax = axes[0, 0]
deg_sorted = sorted(degree_counter.items())
ax.bar(*zip(*deg_sorted), color='steelblue', edgecolor='white')
ax.set_xlabel('Pin Count (Degree)'); ax.set_ylabel('# Instances')
ax.set_title(f'Instance Degree\nMean={np.mean(inst_degrees):.1f}, Median={np.median(inst_degrees):.0f}')

# 2. Net Fanout
ax = axes[0, 1]
fo_sorted = sorted(fanout_counter.items())
ax.bar(*zip(*fo_sorted), color='coral', edgecolor='white')
ax.set_xlabel('Fanout'); ax.set_ylabel('# Nets')
ax.set_title(f'Net Fanout\nTotal={len(net_fanouts)}, Max FO={max(net_fanouts)}')

# 3. Degree CDF
ax = axes[0, 2]
sorted_deg = sorted(inst_degrees)
ax.plot(sorted_deg, np.arange(1, len(sorted_deg)+1)/len(sorted_deg)*100, 'b-', lw=2)
ax.set_xlabel('Degree'); ax.set_ylabel('Cumulative %')
ax.set_title('Degree CDF'); ax.grid(True, alpha=0.3)

# 4. Cell type avg degree
ax = axes[1, 0]
cell_degree = {}
for inst in top.inst_iter():
    d = sum(1 for _ in inst.pin_iter())
    cell_degree.setdefault(inst.ref_name, []).append(d)
top12 = sorted(cell_degree.items(), key=lambda x: -np.mean(x[1]))[:12]
ax.barh(range(12), [np.mean(t[1]) for t in top12], color='teal')
ax.set_yticks(range(12)); ax.set_yticklabels([t[0] for t in top12]); ax.invert_yaxis()
ax.set_xlabel('Avg Pin Count'); ax.set_title('Avg Degree by Cell Type')

# 5. Rent's Rule
ax = axes[1, 1]
deg_arr = np.array(sorted(inst_degrees))
cg = np.arange(1, len(deg_arr)+1); cp = np.cumsum(deg_arr)
ax.loglog(cg, cp, 'b-', lw=1.5, alpha=0.7, label='Data')
start = len(cg)//4
p, log_k = np.polyfit(np.log10(cg[start:]), np.log10(cp[start:]), 1)
k = 10**log_k
gf = np.logspace(0, np.log10(max(cg)), 100)
ax.loglog(gf, k*gf**p, 'r--', lw=2, label=f'Rent fit: T={k:.1f}·G^{p:.3f}')
ax.set_xlabel('# Gates'); ax.set_ylabel('# Terminals')
ax.set_title(f"Rent's Rule  p={p:.3f}, k={k:.1f}"); ax.legend(); ax.grid(True, alpha=0.3)

# 6. Summary
ax = axes[1, 2]; ax.axis('off')
info = f"""Design: {top.name}
Instances: {len(inst_degrees)}
Cell Types: {len(refs)}
Ports: {top.port_count()}  Nets: {len(net_fanouts)}

Degree: [{min(inst_degrees)}, {max(inst_degrees)}]  μ={np.mean(inst_degrees):.1f}  σ={np.std(inst_degrees):.1f}
Fanout:  [{min(net_fanouts)}, {max(net_fanouts)}]  μ={np.mean(net_fanouts):.1f}

Rent: p={p:.3f}  k={k:.1f}"""
ax.text(0.05, 0.95, info, transform=ax.transAxes, fontsize=10, verticalalignment='top',
        fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightyellow'))

fig.suptitle(f'{top.name} Deep Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()
out = os.path.expanduser(f'~/{top.name}_connectivity.png')
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f'Saved: {out}\nRent p={p:.3f} k={k:.1f}  Degree μ={np.mean(inst_degrees):.1f}  Fanout μ={np.mean(net_fanouts):.1f}  [{time.time()-t0:.1f}s]')
project.destroy()
