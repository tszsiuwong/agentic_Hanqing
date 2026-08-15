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
    print(f"用法: {os.path.basename(sys.argv[0])} <design.v|design.def> [tech.lef macro.lef ...] [--lib <file>] [--sdc <file>] [--out <dir>]")
    sys.exit(1)

# 解析 --out / --lib / --sdc
args = sys.argv[1:]
out_dir = "out"
lib_file = None
sdc_file = None
i = 0
while i < len(args):
    if args[i] == '--out' and i + 1 < len(args):
        out_dir = args[i + 1]
        args = args[:i] + args[i+2:]
    elif args[i] == '--lib' and i + 1 < len(args):
        lib_file = args[i + 1]
        args = args[:i] + args[i+2:]
    elif args[i] == '--sdc' and i + 1 < len(args):
        sdc_file = args[i + 1]
        args = args[:i] + args[i+2:]
    else:
        i += 1

design_file = args[0]
lef_files = args[1:] if len(args) > 1 else []

# ── 解析 SDC（create_clock / create_generated_clock）──
sdc_clocks = {}   # port -> {name, period, generated, source, divide_by}
if sdc_file:
    try:
        with open(sdc_file) as f:
            for line in f:
                line = line.strip()
                if not (line.startswith('create_clock') or line.startswith('create_generated_clock')):
                    continue
                is_gen = line.startswith('create_generated_clock')
                m_port = re.search(r'get_ports\s+\[?\{?(\w+)', line)
                port = m_port.group(1) if m_port else None
                m_name = re.search(r'-name\s+(\S+)', line)
                name = m_name.group(1) if m_name else port
                m_period = re.search(r'-period\s+([\d.]+)', line)
                period = float(m_period.group(1)) if m_period else None
                m_src = re.search(r'-source\s+\[get_ports\s+\[?\{?(\w+)', line)
                source = m_src.group(1) if m_src else None
                m_div = re.search(r'-divide_by\s+(\d+)', line)
                div = int(m_div.group(1)) if m_div else None
                if port:
                    sdc_clocks[port] = {'name': name, 'period': period, 'generated': is_gen, 'source': source, 'divide_by': div}
        print(f"[进度] SDC 解析：{len(sdc_clocks)} 个时钟定义")
    except Exception as e:
        print(f"[警告] SDC 解析失败：{e}")

if design_file.endswith('.v') or design_file.endswith('.v.gz'):
    datalens.exchange.load_netlist([design_file])
else:
    if lef_files: datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(design_file)

# 可选：加载 Liberty，用 is_clock 精确识别（回退启发式）
lib_clock_pins = {}   # ref_name -> {pin_name: 'clock'/'reset'/'enable'/'gate_*'}
lib_seq_refs = set()  # 有 clock pin 的 cell（时序单元）
if lib_file:
    try:
        datalens.exchange.load_lib([lib_file])
        lib = datalens.timinglib.current_lib()
        if lib:
            for lc in lib.libcell_iter():
                pins = {}
                has_clock = False
                for lp in lc.libpin_iter():
                    role = None
                    if lp.is_clock:
                        has_clock = True
                        role = 'clock'
                    elif lp.is_clock_gate_clock_pin:
                        role = 'gate_clock'
                    elif lp.is_clock_gate_enable_pin:
                        role = 'gate_enable'
                    elif lp.is_clock_gate_out_pin:
                        role = 'gate_out'
                    if role:
                        pins[lp.name] = role
                if pins:
                    lib_clock_pins[lc.name] = pins
                if has_clock:
                    lib_seq_refs.add(lc.name)
        print(f"[进度] LIB 加载：{len(lib_clock_pins)} 个 cell 有引脚角色，{len(lib_seq_refs)} 个时序单元")
    except Exception as e:
        print(f"[警告] LIB 加载失败，回退启发式：{e}")
        lib_file = None

top = datalens.design.present_project().present_module()
print(f"[进度] 读取模块实例 ...")
insts = []
for module in datalens.design.module_iter():
    for inst in module.inst_iter(False):
        if not inst.is_hier():
            insts.append(inst)
nets = top.nets
ports = top.ports
net_by_name = {n.name: n for n in nets}
print(f"[进度] 实例 {len(insts)}，网 {len(nets)}")

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
    if inst.ref_name in lib_seq_refs:          # lib 优先：有 clock pin 的 cell 是时序单元
        seq_cells.append(inst)
    elif any(ref.startswith(p) for p in SEQ_PREFIXES):  # 回退启发式
        seq_cells.append(inst)
    elif any(ref.startswith(p) for p in ICG_PREFIXES):
        icg_cells.append(inst)
    elif any(ref.startswith(p) for p in CLKBUF_PREFIXES):
        clkbuf_cells.append(inst)
    else:
        comb_cells.append(inst)
print(f"[进度] 分类完成：seq={len(seq_cells)} icg={len(icg_cells)} clkbuf={len(clkbuf_cells)} comb={len(comb_cells)}")

# ── 提取时序单元时钟引脚 ──────────────────────────────
# ff 名字 -> (时钟 net, 复位 net, 使能 net)
ff_clock_net = {}
ff_reset_nets = {}
ff_enable_nets = {}

for inst in seq_cells:
    # lib 优先：用 lib 记录的 clock pin 名字；回退启发式 pin 名
    lib_pin_roles = lib_clock_pins.get(inst.ref_name, {})
    for pin in inst.pins:
        pname = pin.name.upper()
        net = pin.net
        netname = net.name if net is not None else None
        role = lib_pin_roles.get(pin.name)
        if role in ('clock', 'gate_clock') and netname:
            ff_clock_net[inst.name] = netname
        elif role == 'gate_enable' and netname:
            ff_enable_nets.setdefault(inst.name, []).append(netname)
        elif role is None and pname in CLK_PIN_NAMES and netname:  # 回退启发式
            ff_clock_net[inst.name] = netname
        elif role is None and pname in RST_PIN_NAMES and netname:
            ff_reset_nets.setdefault(inst.name, []).append(netname)
        elif role is None and pname in EN_PIN_NAMES and netname:
            ff_enable_nets.setdefault(inst.name, []).append(netname)
print(f"[进度] 时钟引脚提取完成：{len(ff_clock_net)} 个寄存器有时钟引脚")

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
        net_obj = net_by_name.get(cur)
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

# 聚类：每个时序单元的时钟网 -> 时钟根（trace 结果缓存，避免重复追）
clock_domains = defaultdict(list)  # 根 net -> [ff inst name]
ff_domain = {}
root_cache = {}
for ff_name, clk_net in ff_clock_net.items():
    if clk_net not in root_cache:
        root_cache[clk_net] = trace_clock_root(clk_net)
    root = root_cache[clk_net]
    clock_domains[root].append(ff_name)
    ff_domain[ff_name] = root
print(f"[进度] 时钟域聚类完成：{len(clock_domains)} 个时钟域")

# ── 时钟树拓扑 BFS ────────────────────────────────────
def analyze_clock_tree(root_net_name):
    """从时钟根 BFS 遍历，统计每层 buffer 数、叶子数、深度"""
    from collections import deque
    queue = deque([(root_net_name, 0)])
    visited_nets = set()
    level_buffers = defaultdict(int)   # depth -> buffer 数
    level_leaves = defaultdict(int)    # depth -> 寄存器数
    level_other = defaultdict(int)     # depth -> 其他（ICG/异常）
    max_depth = 0

    while queue:
        net_name, depth = queue.popleft()
        if net_name in visited_nets:
            continue
        visited_nets.add(net_name)
        net_obj = net_by_name.get(net_name)
        if net_obj is None:
            continue
        max_depth = max(max_depth, depth)
        try:
            fanout_pins = net_obj.fanout_pins(datalens.design.PinMode.ALL, True)
        except Exception:
            continue
        for pin in fanout_pins:
            inst = pin.inst
            if inst is None:
                continue  # 顶层 port
            ref = inst.ref_name.upper()
            if any(ref.startswith(p) for p in CLKBUF_PREFIXES):
                level_buffers[depth] += 1
                # 找输出 pin，输出 net 加入下一层
                for p2 in inst.pins:
                    if p2.name.upper() in BUFFER_OUTPUT_PINS:
                        nn = p2.net
                        if nn:
                            queue.append((nn.name, depth + 1))
                        break
            elif any(ref.startswith(p) for p in ICG_PREFIXES):
                level_other[depth] += 1
                # ICG 输出继续向下
                for p2 in inst.pins:
                    if p2.name.upper() in ICG_OUTPUT_PINS:
                        nn = p2.net
                        if nn:
                            queue.append((nn.name, depth + 1))
                        break
            elif any(ref.startswith(p) for p in SEQ_PREFIXES):
                level_leaves[depth] += 1
            else:
                level_other[depth] += 1
    return level_buffers, level_leaves, level_other, max_depth

# 对每个时钟域做拓扑分析
clock_tree_stats = {}
for root, ffs in clock_domains.items():
    lb, ll, lo, md = analyze_clock_tree(root)
    clock_tree_stats[root] = (lb, ll, lo, md)

# ── 打印 ──────────────────────────────────────────────
print(f"\n{SEP}")
print(f"  时钟结构分析  —  {top.name}")
print(SEP)

print(f"\n[1] 单元分类")
print(f"  时序单元 (DFF/Latch):  {len(seq_cells)}")
print(f"  CLKBUF/CLKINV 命名单元: {len(clkbuf_cells)}  (未必在时钟路径，见 [6] 拓扑)")
print(f"  时钟门控 (ICG 命名):   {len(icg_cells)}")
print(f"  组合逻辑:              {len(comb_cells)}")

# 时序单元细分
seq_ref_counter = Counter(i.ref_name for i in seq_cells)
print(f"\n[2] 时序单元类型分布")
for ref, cnt in seq_ref_counter.most_common(20):
    print(f"  {ref:<24} {cnt:>6}")

print(f"\n[3] 时钟域（{len(clock_domains)} 个）")
for root, ffs in sorted(clock_domains.items(), key=lambda x: -len(x[1])):
    sdc = sdc_clocks.get(root)
    if sdc and sdc.get('period'):
        period = sdc['period']       # 单位 ns
        freq = 1000.0 / period       # MHz
        extra = ""
        if sdc.get('generated'):
            extra = f" | generated from '{sdc.get('source')}' /{sdc.get('divide_by')}"
        print(f"  时钟根 '{root}': {len(ffs)} 个寄存器 | period={period}ns ({freq:.0f} MHz){extra}")
    else:
        print(f"  时钟根 '{root}': {len(ffs)} 个寄存器  (SDC 无定义)")

ICG_OUTPUT_PINS = {'Q', 'Z', 'ECK', 'GCLK', 'GCK', 'Y', 'OUT', 'ZN'}

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
            if pin.name.upper() in ICG_OUTPUT_PINS:
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

# 时钟树拓扑
print(f"\n[6] 时钟树拓扑")
for root, (lb, ll, lo, md) in sorted(clock_tree_stats.items(), key=lambda x: -len(clock_domains[x[0]])):
    total_buf = sum(lb.values())
    total_leaf = sum(ll.values())
    print(f"  时钟域 '{root}':")
    print(f"    深度 {md} 层 | buffer {total_buf} 个 | 寄存器叶子 {total_leaf} 个 | 其他 {sum(lo.values())} 个")
    for depth in sorted(set(list(lb.keys()) + list(ll.keys()) + list(lo.keys()))):
        b = lb.get(depth, 0)
        l = ll.get(depth, 0)
        o = lo.get(depth, 0)
        fanout = (l + b + o) / b if b > 0 else 0
        print(f"    L{depth}: buffer={b:<4} 叶子={l:<5} 其他={o:<3}  (buffer 平均扇出 {fanout:.1f})")

# ── CSV 导出 ──────────────────────────────────────────
os.makedirs(out_dir, exist_ok=True)

with open(os.path.join(out_dir, "clock_summary.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["design", "seq_cells", "icg_cells", "clkbuf_cells", "comb_cells",
                "clock_domains", "ff_with_reset", "ff_with_enable"])
    w.writerow([top.name, len(seq_cells), len(icg_cells), len(clkbuf_cells), len(comb_cells),
                len(clock_domains), n_ff_with_rst, n_ff_with_en])

# clock_tree.csv (每层拓扑)
with open(os.path.join(out_dir, "clock_tree.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["clock_root", "depth", "buffers", "leaves", "other"])
    for root, (lb, ll, lo, md) in clock_tree_stats.items():
        for depth in range(md + 1):
            w.writerow([root, depth, lb.get(depth, 0), ll.get(depth, 0), lo.get(depth, 0)])

with open(os.path.join(out_dir, "clock_domains.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["clock_root", "ff_count", "period_ns", "freq_mhz", "generated", "source", "divide_by"])
    for root, ffs in sorted(clock_domains.items(), key=lambda x: -len(x[1])):
        sdc = sdc_clocks.get(root, {})
        period = sdc.get('period')
        freq = round(1000.0 / period, 1) if period else ""
        w.writerow([root, len(ffs), period or "", freq,
                    sdc.get('generated', False), sdc.get('source', ""), sdc.get('divide_by', "")])

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
