#!/usr/bin/env python3
"""Liberty 时序库解析（datalens.exchange.load_lib + datalens.timinglib）。

提取库级信息 + 每个 libcell 的面积/引脚/时序属性，统计时序单元 vs 组合单元、
时钟 pin 分布、timing arc 数量、引脚 direction 分布。

用法:
  lib_parse.py <lib_file> [--top N]
"""

import os
import re
import sys
from collections import Counter

import datalens


def parse_lib_header_units(path):
    """文本补充解析 .lib 头部单位属性（API 未暴露时用）。"""
    units = {}
    keys = ["time_unit", "voltage_unit", "current_unit", "pulling_resistance_unit",
            "leakage_power_unit", "capacitive_load_unit", "nom_process", "nom_voltage",
            "nom_temperature"]
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(200000)
        for k in keys:
            m = re.search(r"%s\s*\(\s*([^;]*?)\)" % re.escape(k), head, re.I)
            if m:
                units[k] = m.group(1).strip()
            else:
                m = re.search(r"%s\s*:\s*\"?([^;\"\n]*)" % re.escape(k), head, re.I)
                if m:
                    units[k] = m.group(1).strip()
    except Exception as e:
        units["_error"] = str(e)
    return units


def analyze_lib(lib_file, top_n=15):
    rc = datalens.exchange.load_lib([lib_file])
    lib = datalens.timinglib.current_lib()

    out = {}
    out["load_rc"] = rc
    out["lib_name"] = lib.name
    out["lib_props"] = {}
    for p in lib.list_properties():
        try:
            out["lib_props"][p] = lib.get_property(p)
        except Exception:
            out["lib_props"][p] = None
    out["header_units"] = parse_lib_header_units(lib_file)

    cells = list(lib.libcell_iter())
    out["cell_total"] = len(cells)

    dir_counter = Counter()
    seq_cells = []
    comb_cells = []
    clock_gating_cells = []
    other_cells = []
    arc_counter = Counter()      # cell -> arc count
    clk_pin_counter = Counter()  # cell -> number of clock pins
    area_total = 0.0
    total_pins = 0

    per_cell = []  # (name, area, npins, nclk, narcs, kind)

    for c in cells:
        name = c.name
        area = c.get_property("area") or 0.0
        npins = c.get_property("number_of_pins") or 0
        area_total += area
        total_pins += npins

        is_seq = bool(c.get_property("is_sequential"))
        is_comb = bool(c.get_property("is_combinational"))
        is_cg = bool(c.get_property("is_clock_gating_cell")) or bool(c.get_property("is_icg_cell"))

        nclk = 0
        narcs = 0
        for p in c.libpin_iter():
            d = p.get_property("direction")
            dir_counter[d] += 1
            if p.get_property("is_clock_pin"):
                nclk += 1
            narcs += len(list(p.timing_iter()))

        if is_seq:
            seq_cells.append(name)
        elif is_comb:
            comb_cells.append(name)
        else:
            other_cells.append(name)
        if is_cg:
            clock_gating_cells.append(name)

        arc_counter[name] = narcs
        clk_pin_counter[name] = nclk
        per_cell.append((name, area, npins, nclk, narcs,
                         "seq" if is_seq else ("comb" if is_comb else "other")))

    out["n_seq"] = len(seq_cells)
    out["n_comb"] = len(comb_cells)
    out["n_other"] = len(other_cells)
    out["n_clock_gating"] = len(clock_gating_cells)
    out["cells_with_clock_pin"] = sum(1 for c, v in clk_pin_counter.items() if v > 0)
    out["pin_direction_dist"] = dict(dir_counter)
    out["total_area"] = area_total
    out["total_pins"] = total_pins
    out["total_arcs"] = sum(arc_counter.values())
    out["cells_with_arcs"] = sum(1 for v in arc_counter.values() if v > 0)

    out["top_arcs"] = arc_counter.most_common(top_n)
    out["seq_sample"] = seq_cells[:top_n]
    out["comb_sample"] = comb_cells[:top_n]

    # 面积 top 与引脚数 top
    by_area = sorted(per_cell, key=lambda x: -x[1])[:top_n]
    by_pin = sorted(per_cell, key=lambda x: -x[2])[:top_n]
    out["top_area"] = [(n, a) for n, a, *_ in by_area]
    out["top_pins"] = [(n, p) for n, _, p, *_ in by_pin]

    return out


def report(res, top_n=15):
    L = []
    L.append("=" * 70)
    L.append(f"  Liberty 解析  —  {res['lib_name']}")
    L.append("=" * 70)

    L.append("\n[1] 库级信息")
    L.append(f"  name          = {res['lib_name']}")
    for k, v in res["lib_props"].items():
        L.append(f"  {k:<15} = {v}")
    if res["header_units"]:
        L.append("  文本补充单位:")
        for k, v in res["header_units"].items():
            L.append(f"    {k:<22} = {v}")

    L.append("\n[2] 单元统计")
    L.append(f"  cell 总数        = {res['cell_total']}")
    L.append(f"  时序单元(seq)    = {res['n_seq']}")
    L.append(f"  组合单元(comb)   = {res['n_comb']}")
    L.append(f"  其它/黑盒        = {res['n_other']}")
    L.append(f"  时钟门控单元     = {res['n_clock_gating']}")
    L.append(f"  含 clock pin 单元 = {res['cells_with_clock_pin']}")
    L.append(f"  总引脚数         = {res['total_pins']}")
    L.append(f"  总面积           = {res['total_area']:.4f}")
    L.append(f"  timing arc 总数  = {res['total_arcs']}  (分布在 {res['cells_with_arcs']} 个 cell)")

    L.append("\n[3] 引脚 direction 分布")
    for d, c in res["pin_direction_dist"].items():
        L.append(f"  {str(d):<10} {c}")

    L.append(f"\n[4] timing arc 最多的 {top_n} 个 cell")
    for name, cnt in res["top_arcs"]:
        L.append(f"  {name:<28} {cnt}")

    L.append(f"\n[5] 面积最大的 {top_n} 个 cell")
    for name, a in res["top_area"]:
        L.append(f"  {name:<28} {a:.4f}")

    L.append(f"\n[6] 引脚最多的 {top_n} 个 cell")
    for name, p in res["top_pins"]:
        L.append(f"  {name:<28} {p}")

    L.append(f"\n[7] 时序单元样例 (前 {top_n})")
    L.append("  " + ", ".join(res["seq_sample"]))
    L.append(f"\n[8] 组合单元样例 (前 {top_n})")
    L.append("  " + ", ".join(res["comb_sample"]))

    return "\n".join(L)


def main():
    top_n = 15
    args = [a for a in sys.argv[1:]]
    if "--top" in args:
        i = args.index("--top")
        top_n = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        print(f"用法: {os.path.basename(sys.argv[0])} <lib_file> [--top N]")
        sys.exit(1)

    for path in args:
        if not os.path.isfile(path):
            print(f"[跳过] 文件不存在: {path}")
            continue
        res = analyze_lib(path, top_n)
        print(report(res, top_n))
        print()


if __name__ == "__main__":
    main()
