#!/usr/bin/env python3
"""SAIF 翻转率/活动性解析。

先 load_lib + load_netlist，再 load_saif，通过 pin.toggle_rate() 读取翻转率。
同时文本解析 SAIF 头部（design / timescale / duration / T0 T1 TC）。

用法:
  saif_parse.py
"""

import os
import re

import datalens


SAIF_DIR = "/home/zixiao/dizo/tests/ut/exchange/saif/data/case1"
SAIF_FILE = os.path.join(SAIF_DIR, "test.saif")
LIB_FILE = os.path.join(SAIF_DIR, "test.lib")
V_FILE = os.path.join(SAIF_DIR, "test.v")


def parse_saif_text(path):
    txt = open(path).read()
    info = {}
    for key in ["SAIFVERSION", "DIRECTION", "DESIGN", "DATE", "VENDOR",
                "PROGRAM_NAME", "PROGRAM_VERSION", "TIMESCALE", "DURATION"]:
        m = re.search(r'\(%s\s+"?([^"\)]*)"?\)' % key, txt)
        if m:
            info[key] = m.group(1).strip()
    m = re.search(r'\(DIVIDER\s+(\S+)\)', txt)
    if m:
        info["DIVIDER"] = m.group(1)
    # T0 T1 TC 条目
    toggles = re.findall(r'\((\S+)\s*\(T0\s+([\d.]+)\)\s*\(T1\s+([\d.]+)\)\s*\(TC\s+([\d.]+)\)', txt)
    return info, toggles


def main():
    e = datalens.exchange
    d = datalens.design

    info, toggles = parse_saif_text(SAIF_FILE)

    L = []
    L.append("=" * 70)
    L.append("  SAIF 解析  —  test.saif")
    L.append("=" * 70)

    L.append("\n[1] 文本头部")
    for k, v in info.items():
        L.append(f"  {k:<16} = {v}")
    L.append(f"\n  T0/T1/TC 原始条目:")
    for t in toggles:
        L.append(f"    {t[0]:<14} T0={t[1]} T1={t[2]} TC={t[3]}")

    # API 加载
    e.load_lib([LIB_FILE])
    e.load_netlist([V_FILE])
    rc = e.load_saif(SAIF_FILE, set_tr_sp=True, map_from="top_module", map_to="")

    L.append(f"\n[2] load_saif(API)  rc={rc}")
    top = d.present_project().present_module()
    L.append(f"  top module      = {top.name}")

    L.append("\n[3] 引脚翻转率 (toggle_rate)")
    n_annotated = 0
    for p in top.ports:
        io = p.io_pin()
        if io is None:
            continue
        tr = io.toggle_rate()
        # 3.4e38 为 FLT_MAX，表示未标注
        if tr < 1.0:
            L.append(f"  port {p.name:<14} toggle_rate = {tr}")
            n_annotated += 1
        else:
            L.append(f"  port {p.name:<14} (未标注, FLT_MAX)")
    L.append(f"\n  已标注端口数 = {n_annotated} / {len(top.ports)}")

    print("\n".join(L))


if __name__ == "__main__":
    main()
