#!/usr/bin/env python3
"""
递进式设计分析 —— 输入越多，输出越丰富

  Step 1: design.v                       → 基础统计
  Step 2: design.v + tlef + macro.lef    → + 面积/单元几何
  Step 3: design.v + tlef + macro.lef + lib → + 时序/功耗
  Step 4: design.def + tlef + macro.lef  → + 物理 placement
  Step 5: design.def + tlef + macro.lef + lib → 全量分析 + 图表
"""

import sys, os, re, math, datalens
from datalens.design import PinMode
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans'], 'axes.unicode_minus': False})

# ── CLI ──────────────────────────────────────────────
if len(sys.argv) < 2:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> [tlef ...] [macro.lef ...] [lib ...] [--png <dir>]")
    print(f"示例: {os.path.basename(sys.argv[0])} design.v")
    print(f"       {os.path.basename(sys.argv[0])} design.v tech.lef cells.lef")
    print(f"       {os.path.basename(sys.argv[0])} design.v tech.lef cells.lef timing.lib")
    print(f"       {os.path.basename(sys.argv[0])} design.def tech.lef cells.lef --png out/")
    print(f"       {os.path.basename(sys.argv[0])} design.def tech.lef cells.lef timing.lib --png out/")
    sys.exit(1)

# 解析参数
args = sys.argv[1:]
design_file = args[0]
lef_files, lib_files = [], []
png_dir = "."
i = 1
while i < len(args):
    if args[i] == '--png' and i + 1 < len(args):
        png_dir = args[i + 1]; i += 2
    elif args[i].endswith('.lib') or args[i].endswith('.lib.gz'):
        lib_files.append(args[i]); i += 1
    elif args[i].endswith('.lef') or args[i].endswith('.lef.gz'):
        lef_files.append(args[i]); i += 1
    else:
        i += 1

is_def = design_file.endswith('.def')

# ── 加载 ──────────────────────────────────────────────
loaded = []

if not is_def:
    datalens.exchange.load_netlist([design_file])
    loaded.append(f"Netlist: {design_file}")
elif is_def and lef_files:
    datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(design_file)
    loaded.append(f"DEF: {design_file}")
    loaded.append(f"LEF: {', '.join(lef_files)}")
elif is_def:
    datalens.exchange.load_def(design_file)
    loaded.append(f"DEF: {design_file}")

loaded_lib = False
if lib_files:
    datalens.exchange.load_lib(lib_files)
    loaded.append(f"LIB: {', '.join(lib_files)}")
    loaded_lib = True

top = datalens.design.present_project().present_module()
insts = top.insts
nets = top.nets

# ── 输出 ──────────────────────────────────────────────
SEP = "=" * 64

print(SEP)
print("  递进式设计分析")
print(SEP)
for e in loaded:
    print(f"  ✓ {e}")
print(SEP)

# ════════════ Level 1: 纯网表统计 ════════════
ref_counter = Counter(i.ref_name for i in insts)
cell_types = len(ref_counter)

total_insts = len(insts)
port_count = top.port_count()
net_count = top.net_count()

print(f"\n── Step 1: 基础统计 ──")
print(f"  Instance:   {total_insts}")
print(f"  Cell 类型:  {cell_types}")
print(f"  Port:       {port_count}")
print(f"  Net:        {net_count}")

# cell 分布 Top 10
print(f"\n  Cell Top 10:")
for ref, cnt in ref_counter.most_common(10):
    print(f"    {ref:<24} {cnt:>6}  ({cnt/total_insts*100:.1f}%)")

# ════════════ Level 2: + LEF (面积/几何) ════════════
if lef_files:
    print(f"\n── Step 2: 单元面积/几何 ──")
    tech = None
    try:
        tech = datalens.phylib.present_tech()
    except Exception:
        tech = top.tech()

    total_area = 0.0
    area_by_ref = {}
    unknown = 0
    for inst in insts:
        ref = inst.ref_name
        if ref in area_by_ref:
            area = area_by_ref[ref]
        else:
            try:
                macro = tech.macro(ref) if tech else None
                area = macro.area() if macro else 0
            except Exception:
                area = 0
            area_by_ref[ref] = area
        if area == 0:
            unknown += 1
        else:
            total_area += area

    print(f"  可用 Macro 面积: {len([a for a in area_by_ref.values() if a > 0])}/{cell_types}")
    print(f"  总面积: {total_area:.2f} µm²  (平均 {total_area/total_insts:.2f})" if total_insts else "  总面积: 0")
    if unknown:
        print(f"  未找到 Macro: {unknown} 个实例")

    # Top 5 面积占比
    area_top = sorted([(r, a) for r, a in area_by_ref.items() if a > 0], key=lambda x: -x[1])[:5]
    if area_top:
        print(f"\n  面积 Top 5:")
        for ref, area in area_top:
            cnt = ref_counter.get(ref, 0)
            print(f"    {ref:<20} area={area:.2f} µm²  ×{cnt}  = {area*cnt:.2f} µm²")

# ════════════ Level 3: + LIB (时序/功耗) ════════════
if loaded_lib:
    print(f"\n── Step 3: 时序/功耗 ──")
    lib = datalens.timinglib.current_lib()
    seq_cells = set()
    comb_cells = set()
    if lib:
        for lc in lib.libcell_iter():
            is_seq = False
            try:
                for lp in lc.libpin_iter():
                    for t in lp.timing_iter():
                        is_seq = True
                        break
                    if is_seq: break
            except Exception:
                pass
            if is_seq:
                seq_cells.add(lc.name)
            else:
                comb_cells.add(lc.name)

    seq_cnt = sum(c for r, c in ref_counter.items() if r in seq_cells)
    comb_cnt = total_insts - seq_cnt
    print(f"  组合逻辑: {comb_cnt} ({comb_cnt/total_insts*100:.1f}%)")
    print(f"  时序逻辑: {seq_cnt} ({seq_cnt/total_insts*100:.1f}%)")

# ════════════ Level 4: + placement DEF ════════════
if is_def:
    print(f"\n── Step 4: 物理 Placement ──")

    # Rows
    from dm.design.physical.site_array import SiteArrayIter
    row_count = top.row_count() if hasattr(top, 'row_count') else 0
    try:
        rows = list(top.site_array_iter()) if hasattr(top, 'site_array_iter') else []
    except Exception:
        from datalens.design import SiteArrayIter as SAI
        # not exposed in Python API yet — fallback
        rows = []
    print(f"  Rows:       {row_count if row_count else 'N/A'}")

    # placed / unplaced / fixed
    placed = unplaced = fixed = 0
    for inst in insts:
        try:
            ps = inst.place_status()
        except Exception:
            ps = None
        if ps is None:
            unplaced += 1
        elif str(ps) == 'FIXED' or str(ps) == 'COVER':
            fixed += 1
        elif str(ps) == 'UNPLACED':
            unplaced += 1
        else:
            placed += 1
    print(f"  Placed:     {placed}  |  Fixed: {fixed}  |  Unplaced: {unplaced}")

    # 面积/利用率
    if lef_files and total_area > 0:
        try:
            bbox = top.bbox() if hasattr(top, 'bbox') else None
        except Exception:
            bbox = None
        if bbox:
            try:
                die_w = (bbox.xh() - bbox.xl()) / 2000  # DB units → µm
                die_h = (bbox.yh() - bbox.yl()) / 2000
                die_area = die_w * die_h
                util = total_area / die_area * 100
                print(f"  Die Area:   {die_w:.0f} × {die_h:.0f} = {die_area:.0f} µm²")
                print(f"  利用率:     {util:.1f}%")
            except Exception:
                pass

# ════════════ Level 5: 连接度 + Rent + 图表 ════════════
print(f"\n── Step 5: 连接度分析 ──")

degrees = [i.pin_count() for i in insts]
fanouts = [n.fanout_leaf_pin_count(is_flatten_view=False, include_inout=True) for n in nets]
avg_d = sum(degrees)/len(degrees) if degrees else 0
avg_f = sum(fanouts)/len(fanouts) if fanouts else 0
mx_f = max(fanouts) if fanouts else 0

# Rent
n_groups = 10
gs = [total_insts//n_groups]*n_groups
for i2 in range(total_insts - sum(gs)):
    gs[i2%n_groups] += 1
pts_c, pts_t = [], []
idx = 0
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
if len(pts_c) >= 2:
    A = np.vstack([np.ones_like(pts_c), pts_c]).T
    logk, rent_p = np.linalg.lstsq(A, pts_t, rcond=None)[0]
else:
    rent_p, logk = 0, 0

print(f"  Degree 均值: {avg_d:.1f}  (范围 {min(degrees)}–{max(degrees)})")
print(f"  Fanout 均值: {avg_f:.1f}  (最大 {mx_f})")
print(f"  Rent p:      {rent_p:.3f}  k: {10**logk:.2f}")

# ── 图表 ──────────────────────────────────────────────
os.makedirs(png_dir, exist_ok=True)

# 图 1: Cell 分布
sorted_cells = ref_counter.most_common()
names = [n for n, _ in sorted_cells]
counts = [c for _, c in sorted_cells]
colors = ['#FF5722' if i < 3 else '#2196F3' for i in range(len(names))]
fig, ax = plt.subplots(figsize=(max(12, len(names)*0.35), 5))
bars = ax.bar(range(len(names)), counts, color=colors)
ax.set_xticks(range(len(names)))
ax.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
ax.set_ylabel('Count')
ax.set_title('Cell Distribution')
for bar, c in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(counts)*0.005,
            str(c), ha='center', va='bottom', fontsize=6)
plt.tight_layout()
plt.savefig(os.path.join(png_dir, 'cells.png'), dpi=150)
plt.close()
print(f"\n  Saved: {os.path.join(png_dir, 'cells.png')}")

# 图 2: 连接度
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
plt.savefig(os.path.join(png_dir, 'connectivity.png'), dpi=150)
plt.close()
print(f"  Saved: {os.path.join(png_dir, 'connectivity.png')}")

# 图 3: 时序/组合 (如有 lib)
if loaded_lib:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    ax1.pie([comb_cnt, seq_cnt], labels=[f'Comb ({comb_cnt})', f'Seq ({seq_cnt})'],
            colors=['#FF9800', '#4CAF50'], startangle=90, explode=(0, 0.05))
    ax1.set_title('Seq / Comb Ratio')

    def func_name(ref):
        m = re.match(r'([A-Z]+[0-9]*)', ref)
        return m.group(1) if m else ref
    func_agg = Counter()
    for ref, cnt in ref_counter.items():
        func_agg[func_name(ref)] += cnt
    top10 = func_agg.most_common(10)
    fnames, fcounts = [f for f,_ in top10], [c for _,c in top10]
    colors_bar = ['#FF5722' if ('DFF' in f or 'SDFF' in f) else '#2196F3' for f in fnames]
    ax2.barh(range(len(fnames)), fcounts, color=colors_bar)
    ax2.set_yticks(range(len(fnames)))
    ax2.set_yticklabels(fnames)
    ax2.set_xlabel('Count'); ax2.set_title('Top Cell Functions')
    ax2.invert_yaxis()
    plt.suptitle('Seq / Comb Analysis')
    plt.tight_layout()
    plt.savefig(os.path.join(png_dir, 'seq_comb.png'), dpi=150)
    plt.close()
    print(f"  Saved: {os.path.join(png_dir, 'seq_comb.png')}")

print(f"\n" + SEP)
print("  Done.")
print(SEP)
