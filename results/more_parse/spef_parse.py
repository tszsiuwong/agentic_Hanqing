#!/usr/bin/env python3
"""SPEF 寄生参数解析。

用 datalens.exchange.load_spef + datalens.parasitic 解析 gcd.spef（有匹配 lef+def），
提取单位/scale、dnet 数量、每网总电容、节点/电阻/耦合电容统计。
对 top.spef（无匹配 design）则做文本级解析作为对照。

用法:
  spef_parse.py
"""

import os
import re

import datalens


GCD_DIR = "/home/zixiao/dizo/tests/ut/dm/design/data/gcd"
TOP_SPEF = "/home/zixiao/dizo/tests/ut/dm/design/data/top.spef"


def parse_gcd():
    e = datalens.exchange
    d = datalens.design
    e.load_lef([os.path.join(GCD_DIR, "Nangate45.lef")])
    e.load_def(os.path.join(GCD_DIR, "gcd.def"))
    rc = e.load_spef([os.path.join(GCD_DIR, "gcd.spef")])
    proj = d.present_project()
    proj.make_unique()
    top = proj.present_module()
    dp = top.parasitic()

    nets = []
    total_cap = 0.0
    total_res = 0.0
    total_nodes = 0
    total_xcap = 0
    for dn in dp.dnet_iter():
        cap = dn.total_cap
        total_cap += cap
        rsum = 0.0
        nnodes = dn.node_count()
        nxcap = dn.xcap_count()
        for e in dn.extract_res_iter():
            rsum += e.value
        total_res += rsum
        total_nodes += nnodes
        total_xcap += nxcap
        nets.append({
            "name": dn.net.name,
            "total_cap": cap,
            "res_sum": rsum,
            "nodes": nnodes,
            "pins": dn.pin_count(),
            "res_count": dn.res_count(),
            "xcap": nxcap,
        })

    L = []
    L.append("=" * 70)
    L.append("  SPEF 解析 (datalens.parasitic)  —  gcd.spef")
    L.append("=" * 70)
    L.append(f"\n  load_rc        = {rc}")
    L.append(f"  corner_name    = {dp.corner_name}")
    L.append(f"  time_unit      = {dp.time_unit}   scale={dp.time_scale}")
    L.append(f"  cap_unit       = {dp.cap_unit}    scale={dp.cap_scale}")
    L.append(f"  res_unit       = {dp.res_unit}    scale={dp.res_scale}")
    L.append(f"  induct_unit    = {dp.induct_unit} scale={dp.induct_scale}")
    L.append(f"\n  dnet 数量      = {len(nets)}")
    L.append(f"  总电容         = {total_cap:.6f}")
    L.append(f"  总电阻         = {total_res:.6f}")
    L.append(f"  总节点         = {total_nodes}")
    L.append(f"  总耦合电容     = {total_xcap}")

    L.append("\n  [网] 电容 Top 10")
    for n in sorted(nets, key=lambda x: -x["total_cap"])[:10]:
        L.append(f"    {n['name']:<20} cap={n['total_cap']:.6f} "
                 f"res={n['res_sum']:.6f} nodes={n['nodes']} "
                 f"pins={n['pins']} xcap={n['xcap']}")

    L.append("\n  [网] 电阻 Top 10")
    for n in sorted(nets, key=lambda x: -x["res_sum"])[:10]:
        L.append(f"    {n['name']:<20} res={n['res_sum']:.6f} cap={n['total_cap']:.6f}")

    # VDD 电源网详情（gcd.spef 中唯一带完整 RC 的网）
    try:
        vdd = dp.dnet("VDD")
        if vdd is not None:
            gsum = sum(en.ground_cap for en in vdd.extract_extend_node_iter())
            rvals = [edge.value for edge in vdd.extract_res_iter()]
            L.append("\n  [VDD 电源网详情]")
            L.append(f"    nodes={vdd.node_count()}  pins={vdd.pin_count()} "
                     f"res={vdd.res_count()}  xcap={vdd.xcap_count()}")
            L.append(f"    电阻: count={len(rvals)} min={min(rvals):.6g} "
                     f"max={max(rvals):.6g} sum={sum(rvals):.6f}")
            L.append(f"    对地电容合计 = {gsum:.6f}")
    except Exception as ex:
        L.append(f"  [VDD 详情] 读取失败: {ex}")

    return "\n".join(L)


def parse_top_spef_text():
    """文本级解析 top.spef（无匹配 design，API 无法直接读）。"""
    txt = open(TOP_SPEF).read()
    units = {}
    for key, pat in [("time", r"\*T_UNIT\s+([\d.]+)\s+(\w+)"),
                     ("cap", r"\*C_UNIT\s+([\d.]+)\s+(\w+)"),
                     ("res", r"\*R_UNIT\s+([\d.]+)\s+(\w+)"),
                     ("induct", r"\*L_UNIT\s+([\d.]+)\s+(\w+)")]:
        m = re.search(pat, txt)
        if m:
            units[key] = (float(m.group(1)), m.group(2))

    design = re.search(r"\*DESIGN\s+\"([^\"]+)\"", txt)
    dnets = re.findall(r"\*D_NET\s+(\*\d+)\s+([\d.eE+-]+)", txt)
    caps = re.findall(r"^\s*\d+\s+\*\d+:\d+\s+([\d.eE+-]+)", txt, re.M)
    res = re.findall(r"^\s*\d+\s+(\*\d+|\*\d+:\d+|\*[A-Z]+\w*)\s+(\*\d+:\d+|\*\d+)\s+([\d.eE+-]+)", txt, re.M)

    L = []
    L.append("\n" + "=" * 70)
    L.append("  SPEF 文本解析 (对照)  —  top.spef")
    L.append("=" * 70)
    L.append(f"\n  design          = {design.group(1) if design else '?'}")
    L.append(f"  load_spef(API)  = 失败(rc=-1): Design 'TopCell' 不在 DB 中, 无匹配 netlist/def")
    for k, (v, u) in units.items():
        L.append(f"  {k}_unit         = {v} {u}")
    L.append(f"\n  D_NET 数量      = {len(dnets)}")
    if dnets:
        L.append(f"  net 总电容值     = {[float(x[1]) for x in dnets]}")
    L.append(f"  节点电容条目     = {len(caps)}  (值范围 {min(map(float, caps)) if caps else '-'} ~ {max(map(float, caps)) if caps else '-'})")
    L.append(f"  电阻条目         = {len(res)}")
    return "\n".join(L)


def main():
    print(parse_gcd())
    print(parse_top_spef_text())


if __name__ == "__main__":
    main()
