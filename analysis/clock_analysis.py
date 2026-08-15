#!/usr/bin/env python3
"""时钟结构分析 —— 时钟域 / 时序单元 / 时钟门控 / 时钟树拓扑

独立于 netlist_profiler.py（网表结构分析）。

用法:
  clock_analysis.py <design.v|design.def> [tech.lef macro.lef ...] [--out <dir>]
"""

import sys, os, re, csv, datalens
from collections import Counter, defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans'], 'axes.unicode_minus': False})

if len(sys.argv) < 2:
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> [tech.lef macro.lef ...] [--out <dir>]")
    sys.exit(1)

# 解析 --out
args = sys.argv[1:]
out_dir = "out"
if '--out' in args:
    i = args.index('--out')
    if i + 1 < len(args):
        out_dir = args[i + 1]
        args = args[:i] + args[i+2:]

design_file = args[0]
lef_files = args[1:] if len(args) > 1 else []

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

SEP = "=" * 64

# ── 单元分类 ──────────────────────────────────────────
SEQ_PREFIXES = ['DFF', 'SDFF', 'LATCH', 'DLATCH', 'RSLATCH', 'DFFR', 'DFFS', 'DFFT', 'EDFF']
ICG_PREFIXES = ['ICG', 'CLKGATE', 'CKLNQ', 'LATCG', 'CLKAND', 'CLKMUX', 'CGL']
CLKBUF_PREFIXES = ['CLKBUF', 'CLKINV', 'CKBD', 'BUFCK', 'CLKXOR']
CLK_PIN_NAMES = {'CK', 'CLK', 'CP', 'G', 'GN', 'C', 'CLKN', 'CLOCK', 'PH1', 'PH2'}
RST_PIN_NAMES = {'RN', 'RST', 'RSTN', 'R', 'SN', 'SET', 'SETN', 'S', 'CDN', 'SDN'}
EN_PIN_NAMES = {'SE', 'SI', 'E', 'EN', 'CE', 'TE'}

seq_cells = []     # 时序单元 (inst)
icg_cells = []     # 时钟门控 (inst)
clkbuf_cells = []  # 时钟 buffer (inst)
comb_cells = []    # 组合逻辑 (inst)

for inst in insts:
    ref = inst.ref_name.upper()
    if any(ref.startswith(p) for p in SEQ_PREFIXES):
        seq_cells.append(inst)
    elif any(ref.startswith(p) for p in ICG_PREFIXES):
        icg_cells.append(inst)
    elif any(ref.startswith(p) for p in CLKBUF_PREFIXES):
        clkbuf_cells.append(inst)
    else:
        comb_cells.append(inst)

# ── 提取时序单元时钟引脚 ──────────────────────────────
# ff 名字 -> (时钟 net, 复位 net, 使能 net)
ff_clock_net = {}
ff_reset_nets = {}
ff_enable_nets = {}

for inst in seq_cells:
    for pin in inst.pins:
        pname = pin.name.upper()
        net = pin.net
        netname = net.name if net is not None else None
        if pname in CLK_PIN_NAMES and netname:
            ff_clock_net[inst.name] = netname
        elif pname in RST_PIN_NAMES and netname:
            ff_reset_nets.setdefault(inst.name, []).append(netname)
        elif pname in EN_PIN_NAMES and netname:
            ff_enable_nets.setdefault(inst.name, []).append(netname)

# ── 时钟域聚类：追 fanin 到根 ─────────────────────────
BUFFER_INPUT_PINS = {'A', 'I', 'IN', 'CK', 'CLK'}
BUFFER_OUTPUT_PINS = {'Z', 'ZN', 'Y', 'Q', 'QN', 'OUT'}

def trace_clock_root(netname, max_depth=50):
    """从叶子时钟网向上追溯到时钟根（顶层 port 或非 buffer 驱动）"""
    seen = set()
    cur = netname
    for _ in range(max_depth):
        if cur is None or cur in seen:
            break
        seen.add(cur)
        # 通过名字找到 net 对象
        net_obj = None
        for n in nets:
            if n.name == cur:
                net_obj = n
                break
        if net_obj is None:
            break
        try:
            fins = net_obj.fanin_pins(datalens.design.PinMode.ALL, True)
        except Exception:
            fins = []
        if not fins:
            break
        fin = fins[0]
        inst = fin.inst
        if inst is None:
            break  # 顶层 port
        ref = inst.ref_name.upper()
        if any(ref.startswith(p) for p in CLKBUF_PREFIXES):
            # 时钟 buffer → 追输入 pin（A/I 等）
            nxt = None
            for p2 in inst.pins:
                if p2.name.upper() in BUFFER_INPUT_PINS:
                    nn = p2.net
                    nxt = nn.name if nn else None
                    break
            cur = nxt
        elif any(ref.startswith(p) for p in ICG_PREFIXES):
            # ICG → 追 ICG 的时钟输入
            nxt = None
            for p2 in inst.pins:
                if p2.name.upper() in CLK_PIN_NAMES:
                    nn = p2.net
                    nxt = nn.name if nn else None
                    break
            cur = nxt
        else:
            # 其他逻辑驱动 → 视为 generated clock 根
            break
    return cur

# 聚类：每个时序单元的时钟网 -> 时钟根
clock_domains = defaultdict(list)  # 根 net -> [ff inst name]
ff_domain = {}
for ff_name, clk_net in ff_clock_net.items():
    root = trace_clock_root(clk_net)
    clock_domains[root].append(ff_name)
    ff_domain[ff_name] = root

# ── 打印 ──────────────────────────────────────────────
print(f"\n{SEP}")
print(f"  时钟结构分析  —  {top.name}")
print(SEP)

print(f"\n[1] 单元分类")
print(f"  时序单元 (DFF/Latch):  {len(seq_cells)}")
print(f"  时钟门控 (ICG):        {len(icg_cells)}")
print(f"  时钟 buffer/inverter:  {len(clkbuf_cells)}")
print(f"  组合逻辑:              {len(comb_cells)}")

# 时序单元细分
seq_ref_counter = Counter(i.ref_name for i in seq_cells)
print(f"\n[2] 时序单元类型分布")
for ref, cnt in seq_ref_counter.most_common(20):
    print(f"  {ref:<24} {cnt:>6}")

print(f"\n[3] 时钟域（{len(clock_domains)} 个）")
for root, ffs in sorted(clock_domains.items(), key=lambda x: -len(x[1])):
    print(f"  时钟根 '{root}': {len(ffs)} 个寄存器")

# 时钟门控统计
print(f"\n[4] 时钟门控")
if icg_cells:
    icg_ref_counter = Counter(i.ref_name for i in icg_cells)
    for ref, cnt in icg_ref_counter.most_common(10):
        print(f"  {ref:<24} {cnt:>6}")
    # gated 寄存器 = ICG 输出驱动的寄存器
    gated_ff = set()
    for icg in icg_cells:
        for pin in icg.pins:
            if pin.is_output():
                nn = pin.net
                if nn:
                    for p2 in nn.fanout_pins(datalens.design.PinMode.ALL, True):
                        i2 = p2.inst
                        if i2 is not None and i2.name in ff_clock_net:
                            gated_ff.add(i2.name)
    print(f"  Gated 寄存器: {len(gated_ff)} / {len(seq_cells)} ({len(gated_ff)/max(len(seq_cells),1)*100:.1f}%)")
else:
    print(f"  无时钟门控单元（未插入 ICG）")

# 复位/使能统计
print(f"\n[5] 复位/使能")
n_ff_with_rst = sum(1 for f in seq_cells if f.name in ff_reset_nets)
n_ff_with_en = sum(1 for f in seq_cells if f.name in ff_enable_nets)
print(f"  带复位寄存器: {n_ff_with_rst} / {len(seq_cells)}")
print(f"  带使能/scan 寄存器: {n_ff_with_en} / {len(seq_cells)}")

# ── CSV 导出 ──────────────────────────────────────────
os.makedirs(out_dir, exist_ok=True)

with open(os.path.join(out_dir, "clock_summary.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["design", "seq_cells", "icg_cells", "clkbuf_cells", "comb_cells",
                "clock_domains", "ff_with_reset", "ff_with_enable"])
    w.writerow([top.name, len(seq_cells), len(icg_cells), len(clkbuf_cells), len(comb_cells),
                len(clock_domains), n_ff_with_rst, n_ff_with_en])

with open(os.path.join(out_dir, "clock_domains.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["clock_root", "ff_count"])
    for root, ffs in sorted(clock_domains.items(), key=lambda x: -len(x[1])):
        w.writerow([root, len(ffs)])

with open(os.path.join(out_dir, "seq_cells.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ref_name", "count"])
    for ref, cnt in seq_ref_counter.most_common():
        w.writerow([ref, cnt])

print(f"\n  CSV → {out_dir}/clock_summary.csv  clock_domains.csv  seq_cells.csv")

# ── 图表 ──────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(16, 10))

# 1. 单元分类饼图
ax = axes[0, 0]
cat_labels = ['Seq', 'ICG', 'ClkBuf', 'Comb']
cat_vals = [len(seq_cells), len(icg_cells), len(clkbuf_cells), len(comb_cells)]
ax.pie(cat_vals, labels=[f'{l} ({v})' for l, v in zip(cat_labels, cat_vals)],
       colors=['#FF5722', '#FF9800', '#4CAF50', '#2196F3'], startangle=90)
ax.set_title('Cell Category')

# 2. 时钟域分布
ax = axes[0, 1]
doms = sorted(clock_domains.items(), key=lambda x: -len(x[1]))[:15]
dnames = [f"{r[:20]}" for r, _ in doms]
dvals = [len(ffs) for _, ffs in doms]
ax.barh(range(len(dnames)), dvals, color='#9C27B0')
ax.set_yticks(range(len(dnames))); ax.set_yticklabels(dnames); ax.invert_yaxis()
ax.set_xlabel('Registers'); ax.set_title(f'Clock Domains ({len(clock_domains)})')

# 3. 时序单元类型 Top 15
ax = axes[1, 0]
top_seq = seq_ref_counter.most_common(15)
snames = [r for r, _ in top_seq]; svals = [c for _, c in top_seq]
ax.barh(range(len(snames)), svals, color='#FF5722')
ax.set_yticks(range(len(snames))); ax.set_yticklabels(snames); ax.invert_yaxis()
ax.set_xlabel('Count'); ax.set_title('Sequential Cell Types')

# 4. 摘要
ax = axes[1, 1]; ax.axis('off')
info = f"""Design: {top.name}
Seq cells:  {len(seq_cells):,}
ICG cells:  {len(icg_cells):,}
ClkBuf:     {len(clkbuf_cells):,}
Clock domains: {len(clock_domains)}

FF w/ reset:  {n_ff_with_rst:,}
FF w/ enable: {n_ff_with_en:,}
Gated ratio:  N/A"""
ax.text(0.05, 0.95, info, transform=ax.transAxes, fontsize=11,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow'))

fig.suptitle(f'{top.name}  Clock Structure Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, "clock_structure.png"), dpi=150, bbox_inches='tight')
plt.close()
print(f"  PNG → {out_dir}/clock_structure.png")

print(f"\n{SEP}")
print("  Done.")
print(SEP)
