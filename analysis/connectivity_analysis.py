#!/usr/bin/env python3
"""Step 5: 连接度分析 —— Degree / Fanout / Rent's Rule + 图表"""

import sys, os, math, datalens
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans'], 'axes.unicode_minus': False})

if len(sys.argv) < 3:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> <out_dir> [tech.lef macro.lef ...]")
    sys.exit(1)

main_file, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)

if main_file.endswith('.v') or main_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([main_file])
else:
    lef_files = sys.argv[3:] if len(sys.argv) > 3 else []
    if lef_files: datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(main_file)

top = datalens.design.present_project().present_module()
insts = top.insts
nets = top.nets

degrees = [i.pin_count() for i in insts]
fanouts = [n.fanout_leaf_pin_count(is_flatten_view=False, include_inout=True) for n in nets]
avg_d = sum(degrees)/len(degrees) if degrees else 0
avg_f = sum(fanouts)/len(fanouts) if fanouts else 0

# Rent
n_groups, total = 10, len(insts)
gs = [total//n_groups]*n_groups
for i in range(total - sum(gs)): gs[i%n_groups] += 1
pts_c, pts_t, idx = [], [], 0
for g in gs:
    grp = insts[idx:idx+g]; idx += g
    if not grp: continue
    nets_used = set()
    for gi in grp:
        for p in gi.pins:
            if p.net: nets_used.add(p.net.name)
    if len(grp) > 0 and len(nets_used) > 0:
        pts_c.append(math.log10(len(grp)))
        pts_t.append(math.log10(len(nets_used)))
import numpy as np
rent_p, logk = 0, 0
if len(pts_c) >= 2:
    A = np.vstack([np.ones_like(pts_c), pts_c]).T
    logk, rent_p = np.linalg.lstsq(A, pts_t, rcond=None)[0]

print("=" * 50)
print("连接度分析")
print("=" * 50)
print(f"  Degree 均值: {avg_d:.1f}  (范围 {min(degrees)}–{max(degrees)})")
print(f"  Fanout 均值: {avg_f:.1f}  (最大 {max(fanouts)})")
print(f"  Rent p:      {rent_p:.3f}  k: {10**logk:.2f}")
print("=" * 50)

# 图
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
dc = Counter(degrees)
dx, dy = sorted(dc.keys()), [dc[d] for d in sorted(dc.keys())]
ax1.bar(dx, dy, color='#4CAF50', edgecolor='white')
ax1.set_xlabel('Degree'); ax1.set_ylabel('Instances'); ax1.set_title('Degree Distribution')
fo_vals = [f for f in fanouts if f > 0]
if fo_vals:
    ax2.hist(fo_vals, bins=min(30, max(fo_vals)), color='#FF9800', edgecolor='white')
ax2.set_xlabel('Fanout'); ax2.set_ylabel('Nets'); ax2.set_title('Fanout Distribution')
ax2.axvline(avg_f, color='red', linestyle='--', label=f'Mean={avg_f:.1f}')
ax2.legend()
plt.suptitle('Connectivity Analysis')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'connectivity.png'), dpi=150)
plt.close()
print(f"\nSaved: {os.path.join(out_dir, 'connectivity.png')}")
