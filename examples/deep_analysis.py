#!/usr/bin/env python3
"""GCD 深度网表分析: Degree 分布 + Net Fanout + 连线复杂度"""
import sys, os
import datalens
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter

netlist = sys.argv[1] if len(sys.argv) > 1 else "/home/shared/benchmarks/nangate45_3D/gcd/2_2_floorplan_io.v"

datalens.exchange.load_netlist([netlist])
project = datalens.design.present_project()
project.make_unique()
top = project.present_module()

# === 1. Instance Degree (Pin count) ===
inst_degrees = []
for inst in top.inst_iter():
    degree = sum(1 for _ in inst.pin_iter())
    inst_degrees.append(degree)

degree_counter = Counter(inst_degrees)

# === 2. Net Fanout ===
net_fanouts = []
for net in top.net_iter():
    fanout = sum(1 for _ in net.pin_iter())
    net_fanouts.append(fanout)

fanout_counter = Counter(net_fanouts)

# === 3. Cell-level degree stats by type ===
cell_degree = {}
for inst in top.inst_iter():
    ref = inst.ref_name
    d = sum(1 for _ in inst.pin_iter())
    if ref not in cell_degree:
        cell_degree[ref] = []
    cell_degree[ref].append(d)

# === Plot ===
fig, axes = plt.subplots(2, 3, figsize=(18, 10))

# 1. Instance Degree Distribution (bar)
ax = axes[0, 0]
deg_sorted = sorted(degree_counter.items())
deg_x, deg_y = zip(*deg_sorted)
ax.bar(deg_x, deg_y, color='steelblue', edgecolor='white')
ax.set_xlabel('Pin Count (Degree)')
ax.set_ylabel('# Instances')
ax.set_title(f'Instance Degree Distribution\nMean={np.mean(inst_degrees):.1f}, Median={np.median(inst_degrees):.0f}')
for x, y in zip(deg_x, deg_y):
    if y > 5:
        ax.text(x, y + 2, str(y), ha='center', fontsize=8)

# 2. Net Fanout Distribution
ax = axes[0, 1]
fo_sorted = sorted(fanout_counter.items())
fo_x, fo_y = zip(*fo_sorted)
ax.bar(fo_x, fo_y, color='coral', edgecolor='white')
ax.set_xlabel('Fanout')
ax.set_ylabel('# Nets')
ax.set_title(f'Net Fanout Distribution\nTotal nets={len(net_fanouts)}, Max FO={max(net_fanouts)}')

# 3. Cumulative degree
ax = axes[0, 2]
sorted_deg = sorted(inst_degrees)
y_cum = np.arange(1, len(sorted_deg) + 1) / len(sorted_deg) * 100
ax.plot(sorted_deg, y_cum, 'b-', linewidth=2)
ax.set_xlabel('Degree')
ax.set_ylabel('Cumulative %')
ax.set_title('Degree CDF')
ax.grid(True, alpha=0.3)
ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
ax.axhline(y=90, color='gray', linestyle='--', alpha=0.5)

# 4. Cell type average degree (top 12)
ax = axes[1, 0]
type_order = sorted(cell_degree.items(), key=lambda x: -np.mean(x[1]))
top_types = type_order[:12]
names = [t[0] for t in top_types]
means = [np.mean(t[1]) for t in top_types]
ax.barh(range(len(names)), means, color='teal')
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names)
ax.invert_yaxis()
ax.set_xlabel('Avg Pin Count')
ax.set_title('Avg Degree by Cell Type (Top 12)')
for i, m in enumerate(means):
    ax.text(m + 0.1, i, f'{m:.1f}', va='center', fontsize=8)

# 5. Gate count vs terminal count (Rent's Rule data)
ax = axes[1, 1]
# Sort instances by degree
deg_arr = np.array(sorted(inst_degrees))
cum_gates = np.arange(1, len(deg_arr) + 1)
cum_pins = np.cumsum(deg_arr)
ax.loglog(cum_gates, cum_pins, 'b-', linewidth=1.5, alpha=0.7, label='Data')

# Fit Rent's rule: log(T) = log(k) + p * log(G)
log_g = np.log10(cum_gates[len(cum_gates)//4:])  # skip first few points
log_t = np.log10(cum_pins[len(cum_pins)//4:])
p, log_k = np.polyfit(log_g, log_t, 1)
k = 10**log_k

# Plot fit
g_fit = np.logspace(0, np.log10(max(cum_gates)), 100)
t_fit = k * g_fit**p
ax.loglog(g_fit, t_fit, 'r--', linewidth=2, label=f'Rent fit: T={k:.1f}·G^{p:.3f}')
ax.set_xlabel('# Gates')
ax.set_ylabel('# Terminals')
ax.set_title(f"Rent's Rule (flat)\np = {p:.3f}, k = {k:.1f}")
ax.legend()
ax.grid(True, alpha=0.3)

# 6. Summary text
ax = axes[1, 2]
ax.axis('off')
max_fo = max(net_fanouts)
high_fo = sum(1 for f in net_fanouts if f > 4)
total_nets = len(net_fanouts)

summary = f"""Design: {top.name}

Instances:   {len(inst_degrees)}
Cell Types:  {len(cell_degree)}
Ports:       {top.port_count()}
Nets:        {total_nets}

--- Degree ---
Min/Max:     {min(inst_degrees)} / {max(inst_degrees)}
Mean/Median: {np.mean(inst_degrees):.1f} / {np.median(inst_degrees):.0f}
Std:         {np.std(inst_degrees):.1f}

--- Fanout ---
Max Fanout:  {max_fo}
FO > 4 nets: {high_fo} ({high_fo/total_nets*100:.1f}%)
Avg Fanout:  {np.mean(net_fanouts):.1f}

--- Rent ---
p = {p:.3f}
k = {k:.1f}
"""
ax.text(0.05, 0.95, summary, transform=ax.transAxes, fontsize=10,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

fig.suptitle(f'GCD Netlist Deep Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()

outfile = os.path.expanduser('~/gcd_deep_analysis.png')
plt.savefig(outfile, dpi=150, bbox_inches='tight')
print(f'Saved: {outfile}')
print(f'Rent p={p:.3f}, k={k:.1f}')
print(f'Degree: mean={np.mean(inst_degrees):.1f}, max={max(inst_degrees)}')
print(f'Fanout: mean={np.mean(net_fanouts):.1f}, max={max_fo}')

project.destroy()
