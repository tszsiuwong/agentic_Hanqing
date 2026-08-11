#!/usr/bin/env python3
"""连接度分析: Degree / Fanout / Rent's Rule"""
import sys, os, time
t0 = time.time()
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
from src.dizo_utils import load_netlist, count_by_ref, get_inst_degrees_with_ref, get_net_fanouts

netlist = sys.argv[1] if len(sys.argv) > 1 else "/home/shared/benchmarks/nangate45_3D/gcd/2_2_floorplan_io.v"
project, top = load_netlist(netlist)

refs = count_by_ref(top)
inst_degrees, cell_degree = get_inst_degrees_with_ref(top)
net_fanouts = get_net_fanouts(top)

deg_mean = np.mean(inst_degrees)
deg_median = np.median(inst_degrees)
deg_std = np.std(inst_degrees)
fo_mean = np.mean(net_fanouts)
fo_max = max(net_fanouts)
fo_p99 = int(np.percentile(net_fanouts, 99))

# Rent's Rule
deg_arr = np.array(sorted(inst_degrees))
cg = np.arange(1, len(deg_arr)+1); cp = np.cumsum(deg_arr)
start = len(cg)//4
p, log_k = np.polyfit(np.log10(cg[start:]), np.log10(cp[start:]), 1)
k = 10**log_k

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Degree CDF
ax = axes[0, 0]
ax.plot(sorted(inst_degrees), np.arange(1, len(inst_degrees)+1)/len(inst_degrees)*100, 'b-', lw=2)
ax.set_xlabel('Degree'); ax.set_ylabel('Cumulative %')
ax.set_title(f'Degree CDF  (μ={deg_mean:.1f} σ={deg_std:.1f})')
ax.grid(True, alpha=0.3)

# 2. Fanout Distribution (top 99%)
ax = axes[0, 1]
fo_clipped = [f for f in net_fanouts if f <= fo_p99 * 2]
ax.hist(fo_clipped, bins=30, color='coral', edgecolor='white', alpha=0.8)
ax.set_xlabel('Fanout'); ax.set_ylabel('# Nets')
ax.set_title(f'Fanout Distribution  (μ={fo_mean:.1f} max={fo_max})')

# 3. Rent's Rule
ax = axes[1, 0]
ax.loglog(cg, cp, 'b-', lw=1.5, alpha=0.5, label='Data')
gf = np.logspace(0, np.log10(max(cg)), 100)
ax.loglog(gf, k*gf**p, 'r--', lw=2, label=f'T={k:.1f}·G^{p:.3f}')
ax.set_xlabel('# Gates'); ax.set_ylabel('# Terminals')
ax.set_title(f"Rent's Rule  (p={p:.3f} k={k:.1f})")
ax.legend(); ax.grid(True, alpha=0.3)

# 4. Summary + Top cells
ax = axes[1, 1]; ax.axis('off')
top_cells = sorted(cell_degree.items(), key=lambda x: -np.mean(x[1]))[:8]
cell_lines = '\n'.join(f'  {n:<20s} μ={np.mean(d):.1f}' for n, d in top_cells[:6])

info = f"""Design: {top.name}
Instances: {len(inst_degrees):,}   Cell Types: {len(refs)}
Ports: {top.port_count()}   Nets: {len(net_fanouts):,}

Degree:  μ={deg_mean:.1f}  σ={deg_std:.1f}
Fanout:  μ={fo_mean:.1f}  max={fo_max:,}
Rent:    p={p:.3f}  k={k:.1f}

Top Cells by Avg Degree:
{cell_lines}
"""
ax.text(0.05, 0.95, info, transform=ax.transAxes, fontsize=10,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow'))

fig.suptitle(f'{top.name}  Connectivity Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()
out = os.path.expanduser(f'~/{top.name}_connectivity.png')
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f'Saved: {out}\nRent p={p:.3f} k={k:.1f}  Degree μ={deg_mean:.1f}  Fanout μ={fo_mean:.1f}  [{time.time()-t0:.1f}s]')
project.destroy()
