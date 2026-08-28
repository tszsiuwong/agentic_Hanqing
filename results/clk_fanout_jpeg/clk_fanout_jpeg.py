#!/usr/bin/env python3.11
"""clk 端口 all_fanout 分析 —— jpeg_sky130hd (datalens/dizo)

抓取 top module `clk` 端口的全部 fanout，统计时钟 sink 点与时钟树结构。

用法:
  cd ~/agentic_Hanqing && source datalens_env.sh
  python3.11 ~/clk_fanout_jpeg/clk_fanout_jpeg.py

只读输入: /home/zixiao/agentic_Hanqing/test/jpeg_sky130hd.v
"""

import datalens
from collections import Counter

NETLIST = "/home/zixiao/agentic_Hanqing/test/jpeg_sky130hd.v"
UINT32_MAX = 4294967295

TYPE_NAME = lambda o: type(o).__name__


def cat_types(objs):
    """按对象类型分类计数: {type_name: count}"""
    return Counter(TYPE_NAME(o) for o in objs)


def ref_dist_of_pins(pins):
    """按所属实例 ref_name 统计 pin 分布"""
    return Counter(p.inst.ref_name for p in pins)


def main():
    datalens.exchange.load_netlist([NETLIST])
    proj = datalens.design.present_project()
    proj.make_unique()
    top = proj.present_module()
    print("=" * 72)
    print(f"设计信息: top={top.name}  netlist={NETLIST}")
    print("=" * 72)

    # ── 全设计规模 ─────────────────────────────────────
    all_insts = [i for m in datalens.design.module_iter() for i in m.inst_iter(False)]
    total_inst = len(all_insts)
    print(f"全设计实例总数: {total_inst}")

    dff_refs = [k for k, v in Counter(i.ref_name for i in all_insts).items()
                if any(s in k for s in ('dfrtp', 'edfxtp', 'dfstp', 'dfrtn', 'dfxtp', 'dfstp'))]
    clkbuf_refs = [k for k, v in Counter(i.ref_name for i in all_insts).items()
                   if 'clkbuf' in k or 'clkinv' in k]

    # ── 定位 clk 端口 ──────────────────────────────────
    clk = top.get_ports('clk')[0]
    clk_net = clk.net()
    print(f"\n[定位] clk 端口: name={clk.name}  net={clk_net.name}")

    # ── 1. 全量 all_fanout ─────────────────────────────
    r_all = clk.all_fanout()
    print(f"\n[1] all_fanout() 全量:")
    print(f"    对象总数: {len(r_all)}")
    print(f"    类型分布: {dict(cat_types(r_all))}")

    pins = [o for o in r_all if TYPE_NAME(o) == 'pin']
    ports = [o for o in r_all if TYPE_NAME(o) == 'port']
    nets = [o for o in r_all if TYPE_NAME(o) == 'net']
    print(f"    pin={len(pins)}  port={len(ports)}  net={len(nets)}")
    print(f"    pin 名分布: {dict(Counter(p.name for p in pins))}")

    # ── 2. only_cell ──────────────────────────────────
    r_cell = clk.all_fanout(only_cell=True)
    print(f"\n[2] all_fanout(only_cell=True) 单元:")
    print(f"    实例总数: {len(r_cell)}  (类型: {dict(cat_types(r_cell))})")
    ref_cell = Counter(o.ref_name for o in r_cell)
    print(f"    ref_name 分布:")
    for k, v in ref_cell.most_common():
        print(f"      {k:<32} {v:>6}")

    # ── 3. only_end ───────────────────────────────────
    r_end = clk.all_fanout(only_end=True)
    print(f"\n[3] all_fanout(only_end=True) 时序端点:")
    print(f"    端点总数: {len(r_end)}  (类型: {dict(cat_types(r_end))})")
    ref_end = ref_dist_of_pins(r_end)
    for k, v in ref_end.most_common():
        print(f"      {k:<32} {v:>6}")

    # ── 4. flatten + only_end ─────────────────────────
    r_flat_end = clk.all_fanout(is_flatten_view=True, only_end=True)
    print(f"\n[4] all_fanout(is_flatten_view=True, only_end=True):")
    print(f"    展平端点总数: {len(r_flat_end)}")
    print(f"    ref_name 分布: {dict(ref_dist_of_pins(r_flat_end))}")

    # ── 5. 其他参数组合 ────────────────────────────────
    print(f"\n[5] 参数矩阵对照:")
    combos = [
        ("should_has_time_arc=False", clk.all_fanout(should_has_time_arc=False)),
        ("is_flatten_view=True", clk.all_fanout(is_flatten_view=True)),
        ("is_flatten_view=True, only_cell=True", clk.all_fanout(is_flatten_view=True, only_cell=True)),
        ("only_end=True, only_cell=True", clk.all_fanout(only_end=True, only_cell=True)),
        ("level=1", clk.all_fanout(level=1)),
        ("level=2", clk.all_fanout(level=2)),
        ("level=3", clk.all_fanout(level=3)),
    ]
    for label, objs in combos:
        print(f"    {label:<44} total={len(objs):<6} {dict(cat_types(objs))}")

    # ── 6. clk net 直接连接 ────────────────────────────
    net_pins = list(clk_net.pin_iter())
    print(f"\n[6] clk net 直接连接 (pin_iter):")
    print(f"    net 上 pin 总数: {len(net_pins)}")
    net_ref = Counter()
    for npin in net_pins:
        inst = npin.inst
        net_ref[inst.ref_name if inst is not None else '<port>'] += 1
    for k, v in net_ref.most_common():
        print(f"      {k:<32} {v:>6}")

    # ── 7. 874 CLKBUF/CLKINV 的用途核查 ────────────────
    print(f"\n[7] 时钟 buffer 单元 (CLKBUF/CLKINV) 用途核查:")
    bufs = [i for i in all_insts if 'clkbuf' in i.ref_name or 'clkinv' in i.ref_name]
    print(f"    设计中 CLKBUF/CLKINV 总数: {len(bufs)}")
    print(f"    ref_name 分布: {dict(Counter(b.ref_name for b in bufs))}")
    buf_input_net = Counter()
    for b in bufs:
        for pin in b.pin_iter():
            n = pin.net
            if n is None:
                continue
            if pin.name in ('A', 'I', 'IN'):
                buf_input_net[n.name] += 1
    print(f"    CLKBUF 输入 net 前10 (共享同一 net 的 buffer 数):")
    for k, v in buf_input_net.most_common(10):
        print(f"      {k:<24} {v:>4}")
    print(f"    clk 网是否出现在 CLKBUF 输入: {'是' if buf_input_net.get('clk') else '否 (0)'}")

    # ── 8. 结论 ───────────────────────────────────────
    n_end = len(r_end)
    n_cell = len(r_cell)
    print(f"\n[8] 交叉验证:")
    print(f"    only_end 端点(叶子 DFF) = {n_end}")
    print(f"    only_cell 单元(DFF)     = {n_cell}")
    print(f"    预期 DFF 数             = 4384")
    print(f"    匹配: {'通过' if n_end == 4384 and n_cell == 4384 else '不通过'}")
    print(f"    时钟树缓冲层: {'有 (CLKBUF 在 clk 路径上)' if buf_input_net.get('clk') else '无 (clk 直连 DFF, 无缓冲)'}")

    proj.destroy()
    print("\nDone.")


if __name__ == "__main__":
    main()
