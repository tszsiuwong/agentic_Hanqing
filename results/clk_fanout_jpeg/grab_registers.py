#!/usr/bin/env python3.11
"""按单元类型 (ref_name) 抓取 jpeg_sky130hd 全部 Register (DFF/锁存器) —— datalens/dizo

不依赖时钟网，直接用 ref_name 识别所有时序单元（Register），并与之
clk 端口 all_fanout 抓到的 4384 个 DFF 做交叉验证。

用法:
  cd ~/agentic_Hanqing && source datalens_env.sh
  python3.11 ~/clk_fanout_jpeg/grab_registers.py

只读输入: /home/zixiao/agentic_Hanqing/test/jpeg_sky130hd.v
"""

import re
from collections import Counter, defaultdict

import datalens

NETLIST = "/home/zixiao/agentic_Hanqing/test/jpeg_sky130hd.v"
LIB_PREFIX = "sky130_fd_sc_hd__"

# ─────────────────────────────────────────────────────────────
# Register 识别规则 (sky130 fd_sc_hd 命名)
#   时序单元功能名均以 'd' (data) 开头，后跟 'f'(flip-flop) 或 'l'(latch)：
#     df*   D 触发器      (dfxtp/dfrtp/dfstp/dfxbp/dfbbp/...)
#     dl*   D 锁存器      (dlxtp/dlrtp/dlytp/...)
#     edf*  带使能 DFF    (edfxtp/...)
#     edl*  带使能 DLAT
#     sdf*  扫描 DFF      (sdfxtp/sdfrtp/sdfstp/...)
#     sdl*  扫描 DLAT
#   因此判定规则 = 功能名包含 "df" 或 "dl"（组合单元名如 and/or/nand/nor/
#   a2*/o2*/mux/fa/ha/inv/buf/clkbuf 等均不含 df/dl，不会误判）。
# ─────────────────────────────────────────────────────────────
SEQ_BASE_RE = re.compile(r"^(?:edf|sdf|sdl|edl|df|dl)")
DF_RE = re.compile(r"^(?:edf|sdf|df)")      # 触发器类 (DFF)
DLAT_RE = re.compile(r"^(?:edl|sdl|dl)")    # 锁存器类 (DLAT)


def cell_base(ref_name):
    """剥离库前缀 + 驱动强度后缀，返回功能名 (如 'edfxtp')。"""
    body = ref_name[len(LIB_PREFIX):] if ref_name.startswith(LIB_PREFIX) else ref_name
    m = re.match(r"([A-Za-z0-9]+?)(?:_\d+)?$", body)
    return m.group(1) if m else body


def is_register(ref_name):
    """判定实例是否为时序单元 (Register)。"""
    return bool(SEQ_BASE_RE.match(cell_base(ref_name)))


def is_latch(ref_name):
    """判定是否为锁存器 (DLAT，区别于 DFF)。"""
    return bool(DLAT_RE.match(cell_base(ref_name)))


def main():
    datalens.exchange.load_netlist([NETLIST])
    proj = datalens.design.present_project()
    proj.make_unique()
    top = proj.present_module()

    # ── 1. 全设计实例遍历 ────────────────────────────────
    all_insts = [i for m in datalens.design.module_iter()
                 for i in m.inst_iter(False)]
    total = len(all_insts)
    print("=" * 78)
    print(f"top module : {top.name}")
    print(f"全设计实例总数 : {total}")
    print("=" * 78)

    # ── 2. 按 ref_name 前缀分类统计 (供人工挑出时序单元名) ──
    ref_count = Counter(i.ref_name for i in all_insts)
    print(f"\n[1] 全设计唯一 ref_name 数: {len(ref_count)}")

    seq_insts = [i for i in all_insts if is_register(i.ref_name)]
    print(f"\n[2] 按 ref_name 识别出的 Register 总数: {len(seq_insts)}")
    print(f"     其中 DFF: {sum(1 for i in seq_insts if not is_latch(i.ref_name))}")
    print(f"     其中 DLAT(锁存器): {sum(1 for i in seq_insts if is_latch(i.ref_name))}")

    # ── 3. Register 按 ref_name 分布 ──────────────────────
    seq_ref = Counter(i.ref_name for i in seq_insts)
    print(f"\n[3] Register 按 ref_name 分布:")
    for k, v in seq_ref.most_common():
        flag = "DLAT" if is_latch(k) else "DFF "
        base = cell_base(k)
        print(f"      {k:<32} {v:>6}   ({flag} / {base})")

    # ── 4. 所有 ref_name 中疑似时序类的全量前缀 (校验无遗漏) ──
    print(f"\n[4] 全设计 ref_name 中匹配 'df'/'dl' 的单元名 (应全被 [3] 覆盖):")
    dfdl = [k for k in ref_count if "df" in cell_base(k) or "dl" in cell_base(k)]
    for k in sorted(dfdl):
        print(f"      {k:<32} {ref_count[k]:>6}")

    # ── 5. 代表性实例清单 ─────────────────────────────────
    print(f"\n[5] 代表性 Register 实例 (每种 ref_name 前 5 个):")
    by_ref = defaultdict(list)
    for i in seq_insts:
        by_ref[i.ref_name].append(i)
    for k, lst in sorted(by_ref.items()):
        print(f"    {k}  (共 {len(lst)} 个)")
        for inst in lst[:5]:
            pins = [p.name for p in inst.pin_iter()]
            print(f"        - {inst.full_name}   pins={pins}")

    # ── 6. 与 clk all_fanout 交叉验证 ─────────────────────
    clk = top.get_ports("clk")[0]
    clk_cells = clk.all_fanout(only_cell=True)
    clk_count = len(clk_cells)
    clk_ref = Counter(o.ref_name for o in clk_cells)
    print(f"\n[6] 交叉验证 vs clk all_fanout(only_cell=True):")
    print(f"      clk all_fanout 抓到 DFF 数: {clk_count}")
    print(f"      按类型抓到 Register 数:     {len(seq_insts)}")
    print(f"      clk 分布: {dict(clk_ref)}")
    print(f"      类型分布: {dict(seq_ref)}")

    # 差集分析
    clk_names = {o.name for o in clk_cells}
    seq_names = {i.name for i in seq_insts}
    only_clk = clk_names - seq_names          # 挂在 clk 但没被类型规则识别
    only_seq = seq_names - clk_names          # 被识别为 Register 但不在 clk 上
    print(f"\n      挂在 clk 但类型规则未识别: {len(only_clk)} 个")
    print(f"      类型规则识别到但不在 clk 网: {len(only_seq)} 个")
    if only_seq:
        for i in seq_insts:
            if i.name in only_seq:
                print(f"         不在 clk 上: {i.full_name}  ref={i.ref_name}")
    if only_clk:
        for o in clk_cells:
            if o.name in only_clk:
                print(f"         类型未识别: {o.full_name}  ref={o.ref_name}")

    # ── 7. 结论 ──────────────────────────────────────────
    print(f"\n[7] 结论:")
    print(f"      Register 总数 (按类型) = {len(seq_insts)}")
    print(f"      clk all_fanout DFF 数  = {clk_count}")
    print(f"      二者相等: {len(seq_insts) == clk_count}")
    print(f"      锁存器(DLAT)数量 = {sum(1 for i in seq_insts if is_latch(i.ref_name))}")


if __name__ == "__main__":
    main()
