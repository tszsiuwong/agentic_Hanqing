#!/usr/bin/env python3
"""VCD 值变化转储解析。

load_netlist + load_vcd 后，通过 project.vcd_info() 读时间尺度/范围，
通过 pin.flip_times() 读信号翻转序列。

用法:
  vcd_parse.py [vcd_file]   # 默认 alu_rtl.vcd
"""

import os
import sys

import datalens
from datalens import design as D

VCD_DIR = "/home/zixiao/dizo/tests/ut/interpreter/command/data/vcd"
NETLIST = os.path.join(VCD_DIR, "vcd_gate.v")
NAME_MAP = os.path.join(VCD_DIR, "vcd_name_map.map")


def main():
    vcd_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VCD_DIR, "alu_rtl.vcd")
    inst_name = "tb/alu_tb"

    e = datalens.exchange
    d = datalens.design

    L = []
    L.append("=" * 70)
    L.append(f"  VCD 解析  —  {os.path.basename(vcd_file)}")
    L.append("=" * 70)

    rc_nl = e.load_netlist([NETLIST])
    L.append(f"\n[1] load_netlist rc={rc_nl}")

    rc = e.load_vcd(vcd_file, inst_name=inst_name, name_map=NAME_MAP)
    L.append(f"[2] load_vcd rc={rc} (inst_name='{inst_name}')")

    proj = d.present_project()
    vi = proj.vcd_info()
    L.append("\n[3] vcd_info")
    L.append(f"  time_scale = {vi.time_scale()}")
    L.append(f"  time_unit  = {vi.time_unit()}")
    L.append(f"  start_time = {vi.start_time()}")
    L.append(f"  end_time   = {vi.end_time()}")

    top = proj.present_module()

    # 顶层端口翻转（只显示有真实翻转的，其余汇总）
    L.append("\n[4] 顶层端口信号翻转 (flip_times, 只列 >1 次翻转)")
    active = []
    n_static = 0
    for port in top.ports:
        io = port.io_pin()
        if io is None:
            continue
        ft = io.flip_times()
        if len(ft) > 1:
            active.append((port.name, ft))
        elif ft:
            n_static += 1
    for name, ft in active:
        L.append(f"  port {name:<14} {len(ft)} 次翻转: "
                 f"{[(t, str(v).split('.')[-1]) for t, v in ft]}")
    L.append(f"  (其余 {n_static} 个端口仅有初始值, 无翻转)")

    # 实例引脚翻转统计
    L.append("\n[5] 实例引脚翻转统计 (Top 15)")
    rows = []
    total_flips = 0
    for inst in top.inst_iter(False):
        for pin in inst.pins:
            ft = pin.flip_times()
            if ft:
                total_flips += len(ft)
                rows.append((inst.name, pin.name, len(ft), ft))
    rows.sort(key=lambda x: -x[2])
    L.append(f"  有翻转的引脚数 = {len(rows)}, 总翻转次数 = {total_flips}")
    for inst_name_, pin_name, n, ft in rows[:15]:
        L.append(f"  {inst_name_:<16} {pin_name:<6} {n} 次 "
                 f"首={ft[0]}")

    # 时钟端口 clk 的完整波形
    try:
        clk_port = top.port("clk")
        if clk_port is not None:
            io = clk_port.io_pin()
            if io is not None:
                L.append("\n[6] 时钟 clk 完整翻转序列")
                L.append(f"  {io.flip_times()}")
    except Exception as ex:
        L.append(f"  [clk] {ex}")

    print("\n".join(L))


if __name__ == "__main__":
    main()
