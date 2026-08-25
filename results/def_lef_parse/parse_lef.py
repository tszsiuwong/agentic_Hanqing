#!/usr/bin/env python3
"""解析 LEF 文件，提取物理库结构信息。

用法:
    source ~/agentic_Hanqing/datalens_env.sh
    python3.11 parse_lef.py [lef_files...]

默认解析 Nangate45 主库 (Nangate45.lef + Nangate45_lvt.lef)。
"""
import sys
import os
import re
import csv
from collections import Counter, defaultdict

import datalens
from datalens.phylib import LayerType, MacroMajorClass

DEFAULT_LEFS = [
    os.path.expanduser("~/OpenROAD/test/Nangate45/Nangate45.lef"),
]

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def enum_name(e):
    """把 pybind 枚举的 'LayerType.ROUTING' 之类去前缀，仅保留值名。"""
    s = str(e)
    return s.split(".")[-1] if "." in s else s


def bbox_str(bbox):
    if bbox is None:
        return "N/A"
    return f"({bbox.left()}, {bbox.bottom()}) - ({bbox.right()}, {bbox.top()})"


def main():
    lef_files = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_LEFS
    print(f"[parse_lef] 输入 LEF: {lef_files}")

    datalens.exchange.load_lef(lef_files)
    tech = datalens.phylib.present_tech()
    print(f"[parse_lef] tech name = {tech.name}")

    results = {}

    # ---------------------------------------------------------------- 单位
    unit = tech.unit()
    micron_per_dbu = unit.micron_per_dbu() if unit else None
    results["unit_micron_per_dbu"] = micron_per_dbu
    print("\n== 单位 ==")
    print(f"  micron_per_dbu = {micron_per_dbu}")

    # ---------------------------------------------------------------- 层
    layers = list(tech.layer_iter())
    layer_rows = []
    for lyr in layers:
        t = enum_name(lyr.type)
        row = {
            "name": lyr.name,
            "num": lyr.num,
            "type": t,
            "is_routing": lyr.is_general_routing_type(),
            "is_cut": lyr.is_general_cut_type(),
            "direction": enum_name(lyr.direction()) if lyr.direction() is not None else "N/A",
            "width": lyr.width(),
            "pitch": lyr.pitch(),
        }
        layer_rows.append(row)

    type_counter = Counter(r["type"] for r in layer_rows)
    results["layer_count"] = len(layers)
    results["layer_types"] = dict(type_counter)
    results["layer_names"] = [r["name"] for r in layer_rows]

    print("\n== 层 (layer) ==")
    print(f"  总数: {len(layers)}  类型分布: {dict(type_counter)}")
    for r in layer_rows:
        print(f"    {r['name']:<8} num={r['num']:<3} type={r['type']:<10} "
              f"routing={r['is_routing']!s:<5} cut={r['is_cut']!s:<5} "
              f"dir={r['direction']:<12} width={r['width']} pitch={r['pitch']}")

    with open(os.path.join(OUT_DIR, "lef_layers.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(layer_rows[0].keys()))
        w.writeheader()
        w.writerows(layer_rows)

    # ---------------------------------------------------------------- 过孔
    vias = list(tech.via_iter())
    via_rows = []
    for v in vias:
        via_rows.append({
            "name": v.name,
            "bottom": v.bottom_layer.name if v.bottom_layer else "",
            "cut": v.cut_layer.name if v.cut_layer else "",
            "top": v.top_layer.name if v.top_layer else "",
            "is_default": v.is_default(),
            "is_generated": v.is_generated(),
        })
    results["via_count"] = len(vias)
    results["via_names"] = [r["name"] for r in via_rows]

    print("\n== 过孔 (via template) ==")
    print(f"  总数: {len(vias)}")
    for r in via_rows:
        print(f"    {r['name']:<12} {r['bottom']} -> {r['top']} "
              f"(cut={r['cut']}, default={r['is_default']}, generated={r['is_generated']})")

    with open(os.path.join(OUT_DIR, "lef_vias.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(via_rows[0].keys()))
        w.writeheader()
        w.writerows(via_rows)

    # ---------------------------------------------------------------- via rule
    via_rules = list(tech.via_rule_iter())
    results["via_rule_count"] = len(via_rules)
    results["via_rule_names"] = [vr.name for vr in via_rules]
    print("\n== 过孔规则 (via rule) ==")
    print(f"  总数: {len(via_rules)}")
    print("  名称: " + ", ".join(vr.name for vr in via_rules[:40]) +
          ("..." if len(via_rules) > 40 else ""))

    # ---------------------------------------------------------------- site
    # 注意: datalens.phylib 未暴露 tech.site_iter()，站点名称需从 LEF 文本读取
    # 再通过 tech.site(name) 获取权威尺寸/对称性。
    site_names = []
    for lef in lef_files:
        with open(lef) as fh:
            for line in fh:
                m = re.match(r"^SITE\s+(\S+)", line)
                if m and m.group(1) not in site_names:
                    site_names.append(m.group(1))

    site_rows = []
    for name in site_names:
        site = tech.site(name)
        if site is None:
            continue
        site_rows.append({
            "name": site.name,
            "class": enum_name(site.class_type),
            "width": site.width,
            "height": site.height,
            "sym_x": site.has_sym_x(),
            "sym_y": site.has_sym_y(),
            "sym_r90": site.has_sym_r90(),
        })
    results["site_count"] = len(site_rows)
    results["site_names"] = site_names

    print("\n== 站点 (site) ==")
    print(f"  总数: {len(site_rows)}")
    for s in site_rows:
        w_um = s["width"] * micron_per_dbu
        h_um = s["height"] * micron_per_dbu
        print(f"    {s['name']}  class={s['class']}  "
              f"width={s['width']}dbu ({w_um:.3f}um)  height={s['height']}dbu ({h_um:.3f}um)  "
              f"sym(x={s['sym_x']}, y={s['sym_y']}, r90={s['sym_r90']})")

    with open(os.path.join(OUT_DIR, "lef_sites.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(site_rows[0].keys()))
        w.writeheader()
        w.writerows(site_rows)

    # ---------------------------------------------------------------- 宏单元
    macros = list(tech.macro_iter())
    macro_rows = []
    pin_counts = []
    class_counter = Counter()
    major_counter = Counter()
    for m in macros:
        cls = enum_name(m.class_type)
        major = enum_name(m.major_class())
        pin_cnt = m.pin_count()
        area = m.area()  # um^2
        pin_counts.append(pin_cnt)
        class_counter[cls] += 1
        major_counter[major] += 1
        macro_rows.append({
            "name": m.name,
            "class": cls,
            "major_class": major,
            "pin_count": pin_cnt,
            "area_um2": round(area, 4),
            "width_dbu": m.bbox().right() - m.bbox().left(),
            "height_dbu": m.bbox().top() - m.bbox().bottom(),
            "is_std_cell": m.is_std_cell(),
            "is_physical_cell": m.is_physical_cell(),
            "is_pad": m.is_pad(),
            "is_block": m.is_block(),
            "is_cover": m.is_cover(),
        })

    results["macro_count"] = len(macros)
    results["macro_class_dist"] = dict(class_counter)
    results["macro_major_dist"] = dict(major_counter)
    results["macro_pin_min"] = min(pin_counts) if pin_counts else 0
    results["macro_pin_max"] = max(pin_counts) if pin_counts else 0
    results["macro_pin_avg"] = round(sum(pin_counts) / len(pin_counts), 2) if pin_counts else 0

    print("\n== 宏单元 (macro) ==")
    print(f"  总数: {len(macros)}")
    print(f"  major_class 分布: {dict(major_counter)}")
    print(f"  class 分布: {dict(class_counter)}")
    print(f"  引脚数统计: min={results['macro_pin_min']}  max={results['macro_pin_max']}  "
          f"avg={results['macro_pin_avg']}")

    top_n = sorted(macro_rows, key=lambda r: -r["area_um2"])[:10]
    print("\n  Top 10 面积最大宏单元:")
    print(f"    {'name':<28} {'major':<8} {'area(um2)':>10} {'WxH(dbu)':>18} {'pins':>5}")
    for r in top_n:
        print(f"    {r['name']:<28} {r['major_class']:<8} {r['area_um2']:>10.3f} "
              f"{str(r['width_dbu'])+'x'+str(r['height_dbu']):>18} {r['pin_count']:>5}")

    with open(os.path.join(OUT_DIR, "lef_macros.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(macro_rows[0].keys()))
        w.writeheader()
        w.writerows(macro_rows)

    # ---------------------------------------------------------------- 汇总导出
    summary = {
        "lef_files": ";".join(lef_files),
        "tech_name": tech.name,
        "micron_per_dbu": micron_per_dbu,
        "layer_count": len(layers),
        "via_count": len(vias),
        "via_rule_count": len(via_rules),
        "site_count": len(site_rows),
        "macro_count": len(macros),
        "macro_pin_min": results["macro_pin_min"],
        "macro_pin_max": results["macro_pin_max"],
        "macro_pin_avg": results["macro_pin_avg"],
    }
    with open(os.path.join(OUT_DIR, "lef_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        for k, v in summary.items():
            w.writerow([k, v])

    print("\n[parse_lef] 完成，输出 CSV 到", OUT_DIR)


if __name__ == "__main__":
    main()
