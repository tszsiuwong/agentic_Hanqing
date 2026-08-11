#!/usr/bin/env python3
"""纯网表一键分析 —— 加载一次，全量输出"""

import sys, os, re, math, datalens
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans'], 'axes.unicode_minus': False})

if len(sys.argv) < 2:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> [tech.lef macro.lef ...]")
    sys.exit(1)

design_file = sys.argv[1]
lef_files = sys.argv[2:] if len(sys.argv) > 2 else []

if design_file.endswith('.v') or design_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([design_file])
else:
    if lef_files: datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(design_file)

top = datalens.design.present_project().present_module()
insts = []
for module in datalens.design.module_iter():
    for inst in module.inst_iter(False):
        insts.append(inst)
nets = top.nets
ports = top.ports

ref_counter = Counter(i.ref_name for i in insts)
sorted_cells = ref_counter.most_common()
total = len(insts)

def func_name(ref):
    m = re.match(r'([A-Z]+[0-9]*)', ref)
    return m.group(1) if m else ref
func_agg = Counter()
for ref, cnt in ref_counter.items():
    func_agg[func_name(ref)] += cnt

in_cnt = sum(1 for p in ports if p.is_input())
out_cnt = sum(1 for p in ports if p.is_output())
inout_cnt = sum(1 for p in ports if p.is_inout())

SEP = "=" * 60

# ════════════ 基础统计 ════════════
print(f"\n{SEP}")
print("  基础统计")
print(SEP)
print(f"  Instance:  {total}")
print(f"  Cell 类型: {len(ref_counter)}")
print(f"  Port:      {len(ports)}  (IN:{in_cnt}  OUT:{out_cnt}  INOUT:{inout_cnt})")
print(f"  Net:       {len(nets)}")

# ════════════ 单元分布 ════════════
print(f"\n{SEP}")
print("  单元分布")
print(SEP)
print(f"  {'Cell':<28} {'数量':>6} {'占比':>8}")
print(f"  {'-'*42}")
for ref, cnt in sorted_cells[:15]:
    print(f"  {ref:<28} {cnt:>6} {cnt/total*100:>7.1f}%")
if len(sorted_cells) > 15:
    print(f"  ... (共 {len(sorted_cells)} 种)")

top3 = sorted_cells[:3]
if top3:
    top3_total = sum(c for _, c in top3)
    print(f"\n  Top 3 ({', '.join(n for n,_ in top3)}) = {top3_total} ({top3_total/total*100:.0f}%)")

# ════════════ 功能分类 ════════════
print(f"\n{SEP}")
print("  功能分类")
print(SEP)
for fn, cnt in func_agg.most_common(15):
    print(f"  {fn:<16} {cnt:>6}  ({cnt/total*100:.1f}%)")

# ════════════ 连接度 ════════════
# Degree: 每个 inst 连接了多少条 net
inst_nets = {i: set() for i in insts}
for net in nets:
    for pin in net.pins(datalens.design.HierFilterType.ALL, True):
        try:
            inst = pin.inst
            if inst is not None: inst_nets[inst].add(net.name)
        except: pass
degrees = [len(inst_nets[i]) for i in insts]
fanouts = [n.fanout_leaf_pin_count(is_flatten_view=False, include_inout=True) for n in nets]
avg_f = sum(fanouts)/len(fanouts) if fanouts else 0
mx_f = max(fanouts) if fanouts else 0

print(f"\n{SEP}")
print("  连接度")
print(SEP)
if max(degrees) > 0:
    avg_d = sum(degrees)/len(degrees)
    print(f"  Degree:    均值 {avg_d:.1f}  范围 {min(degrees)}–{max(degrees)}")
else:
    print(f"  Degree:    N/A (需要 MACRO LEF 或 Verilog 网表)")
print(f"  Fanout:    均值 {avg_f:.1f}  最大 {mx_f}")

# ════════════ Rent's Rule ════════════
if max(degrees) > 0:
    n_groups = 10
    gs = [total//n_groups]*n_groups
    for i in range(total - sum(gs)): gs[i%n_groups] += 1
    pts_c, pts_t, idx = [], [], 0
    for g in gs:
        grp = insts[idx:idx+g]; idx += g
        if not grp: continue
        nets_used = set()
        for gi in grp:
            nets_used |= inst_nets.get(gi, set())
        if len(grp) > 0 and len(nets_used) > 0:
            pts_c.append(math.log10(len(grp)))
            pts_t.append(math.log10(len(nets_used)))
    import numpy as np
    rent_p, logk = 0, 0
    if len(pts_c) >= 2:
        A = np.vstack([np.ones_like(pts_c), pts_c]).T
        logk, rent_p = np.linalg.lstsq(A, pts_t, rcond=None)[0]
    print(f"  Rent  p:   {rent_p:.3f}    k: {10**logk:.2f}")
else:
    print(f"  Rent:      N/A")

# ════════════ 图表 ════════════
os.makedirs("out", exist_ok=True)

# 单元分布图
names = [n for n, _ in sorted_cells]
counts = [c for _, c in sorted_cells]
colors = ['#FF5722' if i < 3 else '#2196F3' for i in range(len(names))]
fig, ax = plt.subplots(figsize=(max(12, len(names)*0.32), 5))
ax.bar(range(len(names)), counts, color=colors)
ax.set_xticks(range(len(names)))
ax.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
ax.set_ylabel('Count'); ax.set_title('Cell Distribution')
plt.tight_layout()
plt.savefig("out/cells.png", dpi=150); plt.close()

# 功能分类图
top10f = func_agg.most_common(10)
fnames, fcounts = [f for f,_ in top10f], [c for _,c in top10f]
colors_bar = ['#FF5722' if ('DFF' in f or 'SDFF' in f) else '#2196F3' for f in fnames]
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(range(len(fnames)), fcounts, color=colors_bar)
ax.set_yticks(range(len(fnames))); ax.set_yticklabels(fnames); ax.invert_yaxis()
ax.set_xlabel('Count'); ax.set_title('Top Cell Functions')
plt.tight_layout()
plt.savefig("out/cell_functions.png", dpi=150); plt.close()

# 连接度图
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
plt.savefig("out/connectivity.png", dpi=150); plt.close()

print(f"\n{SEP}")
print("  Done — 图表 → out/")
print(SEP)
