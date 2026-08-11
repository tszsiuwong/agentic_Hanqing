#!/usr/bin/env python3
"""纯网表一键分析 —— 加载一次，全量输出"""

import sys, os, re, math, csv, datalens
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
inst_nets = {i.name: set() for i in insts}
for net in nets:
    for pin in net.pins(datalens.design.HierFilterType.ALL, True):
        try:
            inst = pin.inst
            if inst is not None: inst_nets[inst.name].add(net.name)
        except: pass
degrees = [len(inst_nets[i.name]) for i in insts]
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
rents = None
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
            nets_used |= inst_nets.get(gi.name, set())
        if len(grp) > 0 and len(nets_used) > 0:
            pts_c.append(math.log10(len(grp)))
            pts_t.append(math.log10(len(nets_used)))
    import numpy as np
    rent_p, logk = 0, 0
    if len(pts_c) >= 2:
        A = np.vstack([np.ones_like(pts_c), pts_c]).T
        logk, rent_p = np.linalg.lstsq(A, pts_t, rcond=None)[0]
        rents = np.column_stack([np.power(10, pts_c), np.power(10, pts_t)])  # actual values for plot
    print(f"  Rent  p:   {rent_p:.3f}    k: {10**logk:.2f}")
else:
    print(f"  Rent:      N/A")

# ════════════ CSV 导出 ════════════
os.makedirs("out", exist_ok=True)

# summary.csv
with open("out/summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["design", "instances", "cell_types", "ports_in", "ports_out", "ports_inout",
                "nets", "degree_mean", "degree_min", "degree_max",
                "fanout_mean", "fanout_max", "rent_p", "rent_k"])
    w.writerow([top.name, total, len(ref_counter), in_cnt, out_cnt, inout_cnt,
                len(nets), sum(degrees)/max(len(degrees),1) if degrees else 0,
                min(degrees) if degrees else 0, max(degrees) if degrees else 0,
                avg_f, mx_f, round(rent_p, 3), round(10**logk, 1) if logk else 0])

# cell_distribution.csv
with open("out/cell_distribution.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ref_name", "count", "percentage"])
    for ref, cnt in sorted_cells:
        w.writerow([ref, cnt, round(cnt/total*100, 2)])

# connectivity.csv (per-instance degree)
with open("out/connectivity.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["full_name", "ref_name", "degree"])
    for inst in insts:
        w.writerow([inst.full_name, inst.ref_name, len(inst_nets.get(inst.name, []))])

print(f"  CSV → out/summary.csv  cell_distribution.csv  connectivity.csv")

# ════════════ 图表 ════════════

names = [n for n, _ in sorted_cells]
counts = [c for _, c in sorted_cells]

# 单元分布图 (只画 Top 30)
show_n = min(30, len(names))
show_names = names[:show_n] + ['...'] * (len(names) > show_n)
show_counts = counts[:show_n] + [sum(counts[show_n:])]
colors = ['#FF5722' if i < 3 else '#2196F3' for i in range(len(show_names))]
colors[-1] = '#9E9E9E'  # Other in grey
fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(range(len(show_names)), show_counts, color=colors)
ax.set_xticks(range(len(show_names)))
ax.set_xticklabels(show_names, rotation=45, ha='right', fontsize=8)
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

# 连接度 + Rent 图
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))
# Degree
dc = Counter(degrees)
dx, dy = sorted(dc.keys()), [dc[d] for d in sorted(dc.keys())]
ax1.bar(dx, dy, color='#4CAF50', edgecolor='white')
ax1.set_xlabel('Degree'); ax1.set_ylabel('Instances'); ax1.set_title('Degree Distribution')
# Fanout
fo_vals = [f for f in fanouts if f > 0]
if fo_vals:
    ax2.hist(fo_vals, bins=min(30, max(fo_vals)), color='#FF9800', edgecolor='white')
ax2.set_xlabel('Fanout'); ax2.set_ylabel('Nets'); ax2.set_title('Fanout Distribution')
ax2.axvline(avg_f, color='red', linestyle='--', label=f'Mean={avg_f:.1f}')
ax2.legend(fontsize=7)
# Rent's Rule
if rents is not None and len(rents) > 0:
    if len(rents) > 5000:
        step = len(rents)//5000
        rents_s = rents[::step]
    else:
        rents_s = rents
    ax3.loglog(rents_s[:, 0], rents_s[:, 1], 'b.', ms=1, alpha=0.5, label='Data')
    ax3.loglog(rents_s[:, 0], (10**logk) * rents_s[:, 0]**rent_p, 'r--', lw=2,
               label=f'T={10**logk:.1f}·G^{rent_p:.3f}')
    ax3.set_xlabel('# Gates'); ax3.set_ylabel('# Terminals')
    ax3.set_title(f"Rent's Rule  p={rent_p:.3f}"); ax3.legend(fontsize=7); ax3.grid(True, alpha=0.3)
else:
    ax3.text(0.5, 0.5, 'N/A', ha='center', va='center', transform=ax3.transAxes, fontsize=14)
    ax3.set_title("Rent's Rule")
plt.suptitle('Connectivity & Rent')
plt.tight_layout()
plt.savefig("out/connectivity.png", dpi=150); plt.close()

print(f"\n{SEP}")
print("  Done — 图表 → out/")
print(SEP)
