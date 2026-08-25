#!/usr/bin/env python3
"""SDC 约束解析。

优先尝试 datalens 的 ConstraintView API；确认其只暴露「文件名」层面后，
回退到文本/正则解析，提取 create_clock / create_generated_clock / IO delay /
false path / load / driving_cell 等约束的计数与关键字段。

用法:
  sdc_parse.py <sdc1> [sdc2 ...]
"""

import os
import re
import sys
from collections import Counter, defaultdict

try:
    import datalens
    HAS_DATALENS = True
except Exception:
    HAS_DATALENS = False


# ── 探测 datalens ConstraintView API ──────────────────────────────
def try_constraint_view(sdc_files):
    """探测 datalens.design.constraint_view 暴露的接口。

    注意: constraint_view.create() 需要 MCMM 处于初始化状态(需先 load_project /
    init_mcmm_mode 且有设计上下文), 否则会抛 RuntimeError 甚至 SIGSEGV。
    这里只做静态自省, 不真正实例化。
    """
    if not HAS_DATALENS:
        return None
    try:
        cv_cls = datalens.design.constraint_view
        methods = [m for m in dir(cv_cls) if not m.startswith("_")]
        docs = {}
        for m in ["create", "set_sdc_files", "sdc_files", "is_active", "is_setup", "is_hold"]:
            try:
                docs[m] = getattr(getattr(cv_cls, m), "__doc__", None)
            except Exception:
                docs[m] = None
        # 判定: 除了文件名 get/set 之外没有任何约束查询接口
        query_methods = [m for m in methods if any(k in m for k in
                         ("clock", "delay", "path", "load", "uncertainty", "transition", "case"))]
        return {"api_methods": methods, "query_methods": query_methods, "docs": docs}
    except Exception as e:
        return {"error": str(e)}


# ── 文本解析 ─────────────────────────────────────────────────────
def parse_sdc_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    result = {
        "file": path,
        "create_clock": [],
        "create_generated_clock": [],
        "set_input_delay": [],
        "set_output_delay": [],
        "set_false_path": [],
        "set_load": [],
        "set_driving_cell": [],
        "set_input_transition": [],
        "set_propagated_clock": [],
        "set_clock_uncertainty": [],
        "set_max_transition": [],
        "counts": Counter(),
        "other": Counter(),
    }

    # 去掉行内注释（# 开头的注释）
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        cmd = line.split()[0]
        result["counts"][cmd] += 1

        # create_clock / create_generated_clock
        if cmd == "create_clock":
            result["create_clock"].append(_parse_clock(line))
        elif cmd == "create_generated_clock":
            result["create_generated_clock"].append(_parse_clock(line))

        # 用 get_ports 提取端口集合
        elif cmd == "set_input_delay":
            result["set_input_delay"].append(_parse_delay(line))
        elif cmd == "set_output_delay":
            result["set_output_delay"].append(_parse_delay(line))
        elif cmd == "set_false_path":
            result["set_false_path"].append(_parse_false_path(line))
        elif cmd == "set_load":
            result["set_load"].append(_parse_load(line))
        elif cmd == "set_driving_cell":
            result["set_driving_cell"].append(_parse_driving_cell(line))
        elif cmd == "set_input_transition":
            result["set_input_transition"].append(_parse_transition(line))
        elif cmd == "set_propagated_clock":
            result["set_propagated_clock"].append(_parse_propagated(line))
        elif cmd == "set_clock_uncertainty":
            result["set_clock_uncertainty"].append(_parse_uncertainty(line))
        elif cmd == "set_max_transition":
            result["set_max_transition"].append(_parse_max_transition(line))
        else:
            result["other"][cmd] += 1

    return result


def _extract_objects(s, key):
    """提取 get_ports/get_clocks 里的对象名列表。

    处理形式: get_ports clk / get_ports {a b c} / get_ports req_msg[0]。
    保留 [N:M] 位选。
    """
    objs = []
    # 1) 花括号分组 {a b c}
    for m in re.finditer(r"%s\s*\{([^}]*)\}" % key, s):
        for tok in m.group(1).split():
            objs.append(tok)
    # 2) 裸名 / 位选名（先剔除花括号段避免重复统计）
    s2 = re.sub(r"%s\s*\{[^}]*\}" % key, "", s)
    for m in re.finditer(r"%s\s+([A-Za-z_\\][\w\\/\.$]*(?:\[[^\]]*\])?)" % key, s2):
        objs.append(m.group(1))
    return objs


def _ports_in(s):
    return _extract_objects(s, "get_ports")


def _clocks_in(s):
    return _extract_objects(s, "get_clocks")


def _parse_clock(line):
    d = {}
    m = re.search(r"-name\s+(\S+)", line)
    d["name"] = m.group(1) if m else None
    m = re.search(r"-period\s+([\d.eE+-]+)", line)
    d["period"] = float(m.group(1)) if m else None
    # 波形 -waveform {rise fall}
    m = re.search(r"-waveform\s*\{([^}]*)\}", line)
    d["waveform"] = [float(x) for x in m.group(1).split()] if m else None
    d["ports"] = _ports_in(line)
    # source: -source [get_ports clk] / -source clk / -source [get_pins u/Q]
    m = re.search(r"-source\s+\[\s*get_(\w+)\s+\[?\{?(\w+)", line)
    if m:
        d["source"] = m.group(2)
        d["source_kind"] = m.group(1)  # ports / pins / clocks
    else:
        m = re.search(r"-source\s+(\S+)", line)
        d["source"] = m.group(1) if m else None
        d["source_kind"] = None
    m = re.search(r"-divide_by\s+(\d+)", line)
    d["divide_by"] = int(m.group(1)) if m else None
    m = re.search(r"-multiply_by\s+(\d+)", line)
    d["multiply_by"] = int(m.group(1)) if m else None
    d["raw"] = line
    return d


def _parse_delay(line):
    d = {"raw": line}
    # 值可能出现在 -min / -max 之后
    m = re.search(r"^set_\w+_delay\s+(?:-min\s+|-max\s+)?([\d.eE+-]+)", line)
    d["value"] = float(m.group(1)) if m else None
    d["ports"] = _ports_in(line)
    d["clocks"] = _clocks_in(line)
    m = re.search(r"-min", line)
    d["min"] = bool(m)
    m = re.search(r"-max", line)
    d["max"] = bool(m)
    m = re.search(r"-clock_fall", line)
    d["clock_fall"] = bool(m)
    return d


def _parse_false_path(line):
    d = {"raw": line}
    d["from"] = []
    d["to"] = []
    d["through"] = []
    m = re.search(r"-from\s*(\[[^\]]*\]|\S+)", line)
    if m:
        d["from"] = [x.strip("{}[]") for x in m.group(1).split()]
    m = re.search(r"-to\s*(\[[^\]]*\]|\S+)", line)
    if m:
        d["to"] = [x.strip("{}[]") for x in m.group(1).split()]
    m = re.search(r"-through\s*(\[[^\]]*\]|\S+)", line)
    if m:
        d["through"] = [x.strip("{}[]") for x in m.group(1).split()]
    return d


def _parse_load(line):
    d = {"raw": line}
    m = re.search(r"-pin_load\s+([\d.eE+-]+)", line)
    d["pin_load"] = float(m.group(1)) if m else None
    d["ports"] = _ports_in(line)
    return d


def _parse_driving_cell(line):
    d = {"raw": line}
    m = re.search(r"-lib_cell\s+(\S+)", line)
    d["lib_cell"] = m.group(1) if m else None
    d["ports"] = _ports_in(line)
    return d


def _parse_transition(line):
    d = {"raw": line}
    m = re.search(r"^set_input_transition\s+([\d.eE+-]+)", line)
    d["value"] = float(m.group(1)) if m else None
    d["ports"] = _ports_in(line)
    return d


def _parse_propagated(line):
    return {"raw": line, "clocks": _clocks_in(line)}


def _parse_uncertainty(line):
    d = {"raw": line}
    m = re.search(r"^set_clock_uncertainty\s+(?:-setup\s+|-hold\s+)?([\d.eE+-]+)", line)
    d["value"] = float(m.group(1)) if m else None
    d["clocks"] = _clocks_in(line)
    m = re.search(r"-setup", line)
    d["setup"] = bool(m)
    m = re.search(r"-hold", line)
    d["hold"] = bool(m)
    return d


def _parse_max_transition(line):
    d = {"raw": line}
    m = re.search(r"^set_max_transition\s+([\d.eE+-]+)", line)
    d["value"] = float(m.group(1)) if m else None
    d["clocks"] = _clocks_in(line)
    return d


def report(result):
    out = []
    out.append("=" * 70)
    out.append(f"  SDC 解析  —  {result['file']}")
    out.append("=" * 70)

    c = result["counts"]
    out.append("\n[1] 命令计数")
    for cmd in ["create_clock", "create_generated_clock", "set_input_delay",
                "set_output_delay", "set_false_path", "set_load", "set_driving_cell",
                "set_input_transition", "set_propagated_clock", "set_clock_uncertainty",
                "set_max_transition"]:
        if c.get(cmd):
            out.append(f"  {cmd:<28} {c[cmd]}")
    others = {k: v for k, v in c.items() if k not in
              {"create_clock", "create_generated_clock", "set_input_delay",
               "set_output_delay", "set_false_path", "set_load", "set_driving_cell",
               "set_input_transition", "set_propagated_clock", "set_clock_uncertainty",
               "set_max_transition"}}
    for k, v in sorted(others.items()):
        out.append(f"  {k:<28} {v}  (其它)")

    if result["create_clock"]:
        out.append("\n[2] create_clock")
        for clk in result["create_clock"]:
            wave = ""
            if clk.get("waveform"):
                wave = f" waveform={clk['waveform']}"
            out.append(f"  name={clk['name']} period={clk['period']} "
                       f"ports={clk['ports']}{wave}")

    if result["create_generated_clock"]:
        out.append("\n[3] create_generated_clock")
        for clk in result["create_generated_clock"]:
            out.append(f"  name={clk['name']} source={clk['source']} "
                       f"divide_by={clk.get('divide_by')} multiply_by={clk.get('multiply_by')} "
                       f"ports={clk['ports']}")

    if result["set_input_delay"]:
        vals = [d["value"] for d in result["set_input_delay"] if d["value"] is not None]
        nports = len(set(p for d in result["set_input_delay"] for p in d["ports"]))
        out.append(f"\n[4] set_input_delay  {len(result['set_input_delay'])} 条")
        if vals:
            out.append(f"  value 范围: min={min(vals)} max={max(vals)} "
                       f"(覆盖 {nports} 个端口)")
        for d in result["set_input_delay"][:5]:
            out.append(f"    value={d['value']} ports={d['ports']} clock={d['clocks']}")

    if result["set_output_delay"]:
        vals = [d["value"] for d in result["set_output_delay"] if d["value"] is not None]
        nports = len(set(p for d in result["set_output_delay"] for p in d["ports"]))
        out.append(f"\n[5] set_output_delay  {len(result['set_output_delay'])} 条")
        if vals:
            out.append(f"  value 范围: min={min(vals)} max={max(vals)} "
                       f"(覆盖 {nports} 个端口)")
        for d in result["set_output_delay"][:5]:
            out.append(f"    value={d['value']} ports={d['ports']} clock={d['clocks']}")

    if result["set_false_path"]:
        out.append(f"\n[6] set_false_path  {len(result['set_false_path'])} 条")
        for d in result["set_false_path"][:5]:
            out.append(f"    from={d['from']} to={d['to']} through={d['through']}")

    if result["set_load"]:
        out.append(f"\n[7] set_load  {len(result['set_load'])} 条")
        for d in result["set_load"][:5]:
            out.append(f"    pin_load={d['pin_load']} ports={d['ports']}")

    if result["set_driving_cell"]:
        out.append(f"\n[8] set_driving_cell  {len(result['set_driving_cell'])} 条")
        for d in result["set_driving_cell"][:5]:
            out.append(f"    lib_cell={d['lib_cell']} ports={d['ports']}")

    if result["set_input_transition"]:
        out.append(f"\n[9] set_input_transition  {len(result['set_input_transition'])} 条")

    if result["set_clock_uncertainty"]:
        out.append(f"\n[10] set_clock_uncertainty  {len(result['set_clock_uncertainty'])} 条")

    if result["set_max_transition"]:
        out.append(f"\n[11] set_max_transition  {len(result['set_max_transition'])} 条")

    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print(f"用法: {os.path.basename(sys.argv[0])} <sdc1> [sdc2 ...]")
        sys.exit(1)

    for path in sys.argv[1:]:
        if not os.path.isfile(path):
            print(f"[跳过] 文件不存在: {path}")
            continue

        # 1) ConstraintView 探测
        if HAS_DATALENS:
            cv_info = try_constraint_view([path])
            print(f"\n[ConstraintView 探测] {path}")
            if cv_info and "error" in cv_info:
                print(f"  探测失败: {cv_info['error']}")
            elif cv_info:
                print(f"  暴露方法   = {cv_info['api_methods']}")
                print(f"  约束查询接口 = {cv_info['query_methods'] or '无'}")
                print("  结论: 仅暴露文件名 get/set, 无 create_clock/io delay 查询接口 → 用文本解析")

        # 2) 文本解析
        result = parse_sdc_text(path)
        print()
        print(report(result))


if __name__ == "__main__":
    main()
