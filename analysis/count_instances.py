#!/usr/bin/env python3
"""Step 1: 纯网表基础统计 —— .v 或 .def 均可"""

import sys, os, re, datalens
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans'], 'axes.unicode_minus': False})

if len(sys.argv) < 2:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> [tech.lef macro.lef ...] [--png <dir>]")
    sys.exit(1)

# 解析参数
main_file = sys.argv[1]
args = sys.argv[2:]
png_dir = "."
lef_files = []
i = 0
while i < len(args):
    if args[i] == '--png' and i + 1 < len(args):
        png_dir = args[i + 1]; i += 2
    else:
        lef_files.append(args[i]); i += 1

if main_file.endswith('.v') or main_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([main_file])
else:
    if lef_files: datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(main_file)

top = datalens.design.present_project().present_module()
insts = []
for module in datalens.design.module_iter():
    for inst in module.inst_iter(False):
        insts.append(inst)
nets = top.nets

ref_counter = Counter(i.ref_name for i in insts)
sorted_cells = ref_counter.most_common()
total_insts = len(insts)

# 功能分类（按前缀提取：INV, DFF, AOI22, NAND2...）
def func_name(ref):
    m = re.match(r'([A-Z]+[0-9]*)', ref)
    return m.group(1) if m else ref
func_agg = Counter()
for ref, cnt in ref_counter.items():
    func_agg[func_name(ref)] += cnt

# Port 方向统计
ports = top.ports
in_cnt = sum(1 for p in ports if str(p.dir) == 'INPUT')
out_cnt = sum(1 for p in ports if str(p.dir) == 'OUTPUT')
inout_cnt = sum(1 for p in ports if str(p.dir) == 'INOUT')

# ── 打印 ──
SEP = "=" * 64
print(SEP)
print("  纯网表基础统计")
print(SEP)
print(f"  总 Instance:   {total_insts}")
print(f"  Cell 类型:     {len(ref_counter)} 种")
print(f"  Port:          {len(ports)}  (IN:{in_cnt}  OUT:{out_cnt}  INOUT:{inout_cnt})")
print(f"  Net:           {len(nets)}")
print()

# Cell 分布 Top 10
print(f"  {'Cell':<24} {'数量':>6} {'占比':>8}")
print(f"  {'-'*38}")
for ref, cnt in sorted_cells[:15]:
    print(f"  {ref:<24} {cnt:>6} {cnt/total_insts*100:>7.1f}%")

top3 = sorted_cells[:3]
if top3:
    top3_total = sum(c for _, c in top3)
    print(f"\n  Top 3 ({', '.join(n for n,_ in top3)}) = {top3_total} ({top3_total/total_insts*100:.0f}%)\n")

# 功能类别 Top 10
print(f"  {'功能类别':<16} {'数量':>6} {'占比':>8}")
print(f"  {'-'*30}")
for fn, cnt in func_agg.most_common(10):
    print(f"  {fn:<16} {cnt:>6} {cnt/total_insts*100:>7.1f}%")
print(SEP)

# ── 图表 ──
# 默认生成图，--png 指定输出目录
if png_dir != "." or '--png' in sys.argv:
    os.makedirs(png_dir, exist_ok=True)

    # Cell 分布图
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
    print(f"\nSaved: {os.path.join(png_dir, 'cells.png')}")

    # 功能类别 Top 10 图
    top10 = func_agg.most_common(10)
    fnames, fcounts = [f for f,_ in top10], [c for _,c in top10]
    colors_bar = ['#FF5722' if ('DFF' in f or 'SDFF' in f) else '#2196F3' for f in fnames]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(range(len(fnames)), fcounts, color=colors_bar)
    ax.set_yticks(range(len(fnames)))
    ax.set_yticklabels(fnames)
    ax.invert_yaxis()
    ax.set_xlabel('Count')
    ax.set_title('Top Cell Functions')
    plt.tight_layout()
    plt.savefig(os.path.join(png_dir, 'cell_functions.png'), dpi=150)
    plt.close()
    print(f"Saved: {os.path.join(png_dir, 'cell_functions.png')}")
