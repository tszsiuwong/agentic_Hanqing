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

deg_mean = np.mean(inst_degrees); deg_median = np.median(inst_degrees); deg_std = np.std(inst_degrees)
fo_mean = np.mean(net_fanouts); fo_max = max(net_fanouts)
unique_deg = len(set(inst_degrees)); unique_fo = len(set(net_fanouts))
is_large = len(inst_degrees) > 100000

fig, axes = plt.subplots(2, 3, figsize=(18, 10))

# 1. Degree Distribution
ax = axes[0, 0]
if unique_deg <= 30 and not is_large:
    dc = sorted(Counter(inst_degrees).items())
    ax.bar(*zip(*dc), color='steelblue', edgecolor='white')
else:
    ax.hist(inst_degrees, bins=min(20, unique_deg), color='steelblue', edgecolor='white')
ax.set_xlabel('Pin Count'); ax.set_title(f'Degree  μ={deg_mean:.1f}  σ={deg_std:.1f}')

# 2. Fanout Distribution
ax = axes[0, 1]
if unique_fo <= 30 and not is_large:
    fc = sorted(Counter(net_fanouts).items())
    ax.bar(*zip(*fc), color='coral', edgecolor='white')
else:
    p98 = np.percentile(net_fanouts, 98)
    clipped = [f for f in net_fanouts if f <= p98 * 2]
    ax.hist(clipped, bins=30, color='coral', edgecolor='white', alpha=0.8)
ax.set_xlabel('Fanout'); ax.set_title(f'Fanout  μ={fo_mean:.1f}  max={fo_max}')

# 3. Degree CDF (sample for large designs)
ax = axes[0, 2]
sample = sorted_deg[::max(1, len(sorted_deg)//5000)]
ax.plot(sample, np.linspace(0, 100, len(sample)), 'b-', lw=2)
ax.set_xlabel('Degree'); ax.set_ylabel('Cumulative %')
ax.set_title('Degree CDF'); ax.grid(True, alpha=0.3)

# 4. Cell Type Avg Degree
ax = axes[1, 0]
top12 = sorted(cell_degree.items(), key=lambda x: -np.mean(x[1]))[:12]
ax.barh(range(12), [np.mean(t[1]) for t in top12], color='teal')
ax.set_yticks(range(12)); ax.set_yticklabels([t[0] for t in top12]); ax.invert_yaxis()
ax.set_xlabel('Avg Pin Count'); ax.set_title('Avg Degree by Cell Type')

# 5. Rent's Rule
ax = axes[1, 1]
deg_arr = np.array(sorted(inst_degrees))
cg = np.arange(1, len(deg_arr)+1); cp = np.cumsum(deg_arr)
step = max(1, len(cg)//5000)
start = len(cg)//4
p, log_k = np.polyfit(np.log10(cg[start:]), np.log10(cp[start:]), 1)
k = 10**log_k
ax.loglog(cg[::step], cp[::step], 'b.', ms=1, alpha=0.5, label='Data')
gf = np.logspace(0, np.log10(max(cg)), 100)
ax.loglog(gf, k*gf**p, 'r--', lw=2, label=f'T={k:.1f}·G^{p:.3f}')
ax.set_xlabel('# Gates'); ax.set_ylabel('# Terminals')
ax.set_title(f"Rent's Rule  p={p:.3f}  k={k:.1f}")
ax.legend(); ax.grid(True, alpha=0.3)

# 6. Summary
ax = axes[1, 2]; ax.axis('off')
info = f"""Design: {top.name}
Instances: {len(inst_degrees):,}
Cell Types: {len(refs)}
Ports: {top.port_count()}  Nets: {len(net_fanouts):,}

Degree:  [{min(inst_degrees)}, {max(inst_degrees)}]
  μ={deg_mean:.1f}  σ={deg_std:.1f}
Fanout:  μ={fo_mean:.1f}  max={fo_max:,}
Rent:    p={p:.3f}  k={k:.1f}"""
ax.text(0.05, 0.95, info, transform=ax.transAxes, fontsize=10,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow'))

fig.suptitle(f'{top.name}  Connectivity Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()
out = f'{top.name}_connectivity.png'
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f'Saved: {out}\nRent p={p:.3f} k={k:.1f}  Degree μ={deg_mean:.1f}  Fanout μ={fo_mean:.1f}  [{time.time()-t0:.1f}s]')
project.destroy()
