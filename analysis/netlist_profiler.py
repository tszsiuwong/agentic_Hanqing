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
        if not inst.is_hier():
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

# ════════════ Rent's Rule (standard cumulative method) ════════════
rents = None; rent_p, logk = 0, 0
if max(degrees) > 0:
    import numpy as np
    deg_arr = np.array(sorted(degrees))
    cg = np.arange(1, len(deg_arr)+1); cp = np.cumsum(deg_arr)
    start = len(cg)//4
    if len(cg) > start and cp[start] > 0:
        p, lk = np.polyfit(np.log10(cg[start:]), np.log10(cp[start:]), 1)
        rent_p, logk = p, lk
        rents = np.column_stack([cg, cp])
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
show_names = names[:show_n]
show_counts = counts[:show_n]
colors = ['#FF5722' if i < 3 else '#2196F3' for i in range(len(show_names))]
fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(range(len(show_names)), show_counts, color=colors)
ax.set_xticks(range(len(show_names)))
ax.set_xticklabels(show_names, rotation=45, ha='right', fontsize=8)
ax.set_ylabel('Count'); ax.set_title(f'Cell Distribution (Top {show_n} of {len(names)} types)')
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

# 连接度 + Rent 图 (6-panel)
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
d_mean = sum(degrees)/max(len(degrees),1); d_std = (sum((x-d_mean)**2 for x in degrees)/max(len(degrees),1))**0.5 if degrees else 0
f_mean = avg_f; f_max = mx_f
deg_arr = sorted(degrees); fo_vals = [f for f in fanouts if f > 0]
unique_deg = len(set(degrees)); unique_fo = len(set(fo_vals))
is_large = len(degrees) > 100000

# 1. Degree Distribution
ax = axes[0, 0]
if unique_deg <= 30 and not is_large:
    dc = sorted(Counter(degrees).items())
    ax.bar(*zip(*dc), color='steelblue', edgecolor='white')
else:
    ax.hist(degrees, bins=min(20, unique_deg), color='steelblue', edgecolor='white')
ax.set_xlabel('Pin Count'); ax.set_title(f'Degree  μ={d_mean:.1f}  σ={d_std:.1f}')

# 2. Fanout Distribution
ax = axes[0, 1]
if unique_fo <= 30 and not is_large:
    fc = sorted(Counter(fo_vals).items())
    ax.bar(*zip(*fc), color='coral', edgecolor='white')
else:
    p98 = np.percentile(fo_vals, 98) if fo_vals else 0
    clipped = [f for f in fo_vals if f <= p98 * 2]
    ax.hist(clipped, bins=30, color='coral', edgecolor='white', alpha=0.8)
ax.set_xlabel('Fanout'); ax.set_title(f'Fanout  μ={f_mean:.1f}  max={f_max}')

# 3. Degree CDF
ax = axes[0, 2]
sample = deg_arr[::max(1, len(deg_arr)//5000)]
ax.plot(sample, np.linspace(0, 100, len(sample)), 'b-', lw=2)
ax.set_xlabel('Degree'); ax.set_ylabel('Cumulative %')
ax.set_title('Degree CDF'); ax.grid(True, alpha=0.3)

# 4. Cell Type Avg Degree
ax = axes[1, 0]
cell_deg = {}
for inst in insts:
    cell_deg.setdefault(inst.ref_name, []).append(len(inst_nets.get(inst.name, [])))
top12 = sorted(cell_deg.items(), key=lambda x: -sum(x[1])/max(len(x[1]),1))[:12]
n_bar = len(top12)
ax.barh(range(n_bar), [sum(t[1])/max(len(t[1]),1) for t in top12], color='teal')
ax.set_yticks(range(n_bar)); ax.set_yticklabels([t[0] for t in top12]); ax.invert_yaxis()
ax.set_xlabel('Avg Pin Count'); ax.set_title('Avg Degree by Cell Type')

# 5. Rent's Rule
ax = axes[1, 1]
import numpy as np
darr = np.array(deg_arr); cg = np.arange(1, len(darr)+1); cp = np.cumsum(darr)
step = max(1, len(cg)//5000); start = len(cg)//4
if len(cg) > start:
    p, lk = np.polyfit(np.log10(cg[start:]), np.log10(cp[start:]), 1); k = 10**lk
    ax.loglog(cg[::step], cp[::step], 'b.', ms=1, alpha=0.5, label='Data')
    gf = np.logspace(0, np.log10(max(cg)), 100)
    ax.loglog(gf, k*gf**p, 'r--', lw=2, label=f'T={k:.1f}·G^{p:.3f}')
    ax.legend()
    rp_text = f'p={p:.3f} k={k:.1f}'
else: rp_text = 'N/A'
ax.set_xlabel('# Gates'); ax.set_ylabel('# Terminals')
ax.set_title(f"Rent's Rule  {rp_text}"); ax.grid(True, alpha=0.3)

# 6. Summary
ax = axes[1, 2]; ax.axis('off')
info = f"""Design: {top.name}
Instances: {total:,}
Cell Types: {len(ref_counter)}
Ports: {len(ports)}  Nets: {len(nets)}

Degree:  [{min(degrees) if degrees else 0}, {max(degrees) if degrees else 0}]
  μ={d_mean:.1f}  σ={d_std:.1f}
Fanout:  μ={f_mean:.1f}  max={f_max:,}
Rent:    {rp_text}"""
ax.text(0.05, 0.95, info, transform=ax.transAxes, fontsize=10,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow'))

fig.suptitle(f'{top.name}  Connectivity Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig("out/connectivity.png", dpi=150, bbox_inches='tight'); plt.close()

print(f"\n{SEP}")
print("  Done — 图表 → out/")
print(SEP)
