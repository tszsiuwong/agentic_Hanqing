#!/usr/bin/env python3
"""解析 DEF 文件，提取布局结构信息。

用法:
    source ~/agentic_Hanqing/datalens_env.sh
    python3.11 parse_def.py [def_file] [lef_files...]

默认: demo_out.def + Nangate45.lef
"""
import sys
import os
import csv
from collections import Counter

import datalens
from datalens.design import PlaceStatus, UseType

DEFAULT_DEF = os.path.expanduser("~/or_synth_demo/demo_out.def")
DEFAULT_LEFS = [os.path.expanduser("~/OpenROAD/test/Nangate45/Nangate45.lef")]

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def enum_name(e):
    s = str(e)
    return s.split(".")[-1] if "." in s else s


def bbox_str(b):
    if b is None:
        return "N/A"
    return f"({b.left()}, {b.bottom()}) - ({b.right()}, {b.top()})"


def main():
    if len(sys.argv) > 1 and sys.argv[1].endswith(".def"):
        def_file = sys.argv[1]
        lef_files = sys.argv[2:] if len(sys.argv) > 2 else DEFAULT_LEFS
    else:
        def_file = DEFAULT_DEF
        lef_files = DEFAULT_LEFS

    print(f"[parse_def] DEF: {def_file}")
    print(f"[parse_def] LEF: {lef_files}")

    datalens.exchange.load_lef(lef_files)
    datalens.exchange.load_def(def_file)

    project = datalens.design.present_project()
    top = project.present_module()
    print(f"[parse_def] 顶层模块: {top.name}")

    tech = datalens.phylib.present_tech()
    micron_per_dbu = tech.unit().micron_per_dbu()

    summary = {"def_file": def_file, "module": top.name,
               "micron_per_dbu": micron_per_dbu}

    # ---------------------------------------------------------------- die/core area
    die_bbox = top.bbox()
    die_w = die_bbox.right() - die_bbox.left()
    die_h = die_bbox.top() - die_bbox.bottom()
    summary.update({
        "die_bbox": bbox_str(die_bbox),
        "die_width_dbu": die_w,
        "die_height_dbu": die_h,
        "die_width_um": round(die_w * micron_per_dbu, 3),
        "die_height_um": round(die_h * micron_per_dbu, 3),
        "die_area_um2": round(die_w * die_h * micron_per_dbu * micron_per_dbu, 3),
    })
    print("\n== Die / Core Area ==")
    print(f"  DIEAREA bbox = {bbox_str(die_bbox)}")
    print(f"  Die: {die_w} x {die_h} dbu  =  "
          f"{die_w * micron_per_dbu:.3f} x {die_h * micron_per_dbu:.3f} um  =  "
          f"{die_w * die_h * micron_per_dbu ** 2:.3f} um^2")

    # ---------------------------------------------------------------- rows
    rows = list(top.row_iter())
    row_sites = {}
    row_rows = []
    core_xl = core_yl = 1 << 60
    core_xh = core_yh = -(1 << 60)
    orient_counter = Counter()
    for r in rows:
        b = r.bbox()
        site = r.site
        if site.name not in row_sites:
            row_sites[site.name] = (site.width, site.height)
        orient_counter[enum_name(r.site_orient)] += 1
        core_xl = min(core_xl, b.left())
        core_yl = min(core_yl, b.bottom())
        core_xh = max(core_xh, b.right())
        core_yh = max(core_yh, b.top())
        row_rows.append({
            "name": r.name,
            "site": site.name,
            "site_width_dbu": site.width,
            "site_height_dbu": site.height,
            "orient": enum_name(r.site_orient),
            "is_horizontal": r.is_horizontal(),
            "x_count": r.x_count(),
            "y_count": r.y_count(),
            "x_step": r.x_step(),
            "y_step": r.y_step(),
            "location": str(r.location),
        })

    summary.update({
        "row_count": len(rows),
        "row_orient_dist": dict(orient_counter),
    })
    if rows:
        summary["row_site"] = rows[0].site.name
        summary["row_site_width_dbu"] = rows[0].site.width
        summary["row_site_height_dbu"] = rows[0].site.height

    print("\n== Row (行) ==")
    print(f"  总数: {len(rows)}")
    if row_rows:
        r0 = row_rows[0]
        print(f"  首行: {r0['name']}  site={r0['site']}  site尺寸={r0['site_width_dbu']}x{r0['site_height_dbu']}dbu "
              f"orient={r0['orient']} 水平={r0['is_horizontal']}  x_count={r0['x_count']}  x_step={r0['x_step']}")
    print(f"  行方向分布: {dict(orient_counter)}")
    print(f"  由行围出的 core bbox: ({core_xl}, {core_yl}) - ({core_xh}, {core_yh}) dbu  "
          f"= {(core_xh - core_xl) * micron_per_dbu:.3f} x {(core_yh - core_yl) * micron_per_dbu:.3f} um")

    with open(os.path.join(OUT_DIR, "def_rows.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row_rows[0].keys()))
        w.writeheader()
        w.writerows(row_rows)

    # ---------------------------------------------------------------- components
    insts = list(top.inst_iter(False))
    status_counter = Counter()
    coord_rows = []
    for inst in insts:
        st = enum_name(inst.place_status())
        status_counter[st] += 1
        b = inst.bbox()
        if b is not None:
            coord_rows.append({
                "name": inst.name,
                "ref": inst.ref_name,
                "status": st,
                "xl": b.left(), "yl": b.bottom(),
                "xh": b.right(), "yh": b.top(),
                "orient": enum_name(inst.orient()),
            })

    summary["component_count"] = len(insts)
    summary["component_status_dist"] = dict(status_counter)
    print("\n== Component (组件) ==")
    print(f"  总数: {len(insts)}")
    print(f"  摆放状态分布: {dict(status_counter)}")
    placed = status_counter.get("PLACED", 0)
    fixed = status_counter.get("FIXED", 0)
    unplaced = status_counter.get("UNPLACED", 0)
    cover = status_counter.get("COVER", 0)
    soft = status_counter.get("SOFT_FIXED", 0)
    print(f"    PLACED={placed}  FIXED={fixed}  UNPLACED={unplaced}  "
          f"COVER={cover}  SOFT_FIXED={soft}")

    if coord_rows:
        xl = min(r["xl"] for r in coord_rows)
        yl = min(r["yl"] for r in coord_rows)
        xh = max(r["xh"] for r in coord_rows)
        yh = max(r["yh"] for r in coord_rows)
        ref_counter = Counter(r["ref"] for r in coord_rows)
        summary["component_bbox"] = f"({xl},{yl}) - ({xh},{yh})"
        summary["component_ref_kinds"] = len(ref_counter)
        print(f"  已摆放组件包围盒: ({xl}, {yl}) - ({xh}, {yh}) dbu  "
              f"= {(xh - xl) * micron_per_dbu:.3f} x {(yh - yl) * micron_per_dbu:.3f} um")
        print(f"  引用的 cell 种类: {len(ref_counter)}")

    with open(os.path.join(OUT_DIR, "def_components.csv"), "w", newline="") as f:
        if coord_rows:
            w = csv.DictWriter(f, fieldnames=list(coord_rows[0].keys()))
            w.writeheader()
            w.writerows(coord_rows)

    # ---------------------------------------------------------------- ports
    ports = list(top.port_iter())
    dir_counter = Counter()
    no_pos = 0
    bus_port = bit_port = scalar_port = 0
    port_rows = []
    for p in ports:
        dir_counter[enum_name(p.dir)] += 1
        b = p.bbox()
        if p.is_bus():
            bus_port += 1
        elif p.is_bit():
            bit_port += 1
        else:
            scalar_port += 1
        port_rows.append({
            "name": p.name,
            "dir": enum_name(p.dir),
            "use": enum_name(p.use()),
            "is_special": p.is_special(),
            "is_bus": p.is_bus(),
            "bbox": bbox_str(b),
            "has_position": b is not None,
        })
        if b is None:
            no_pos += 1

    summary["port_count"] = len(ports)
    summary["port_bus_count"] = bus_port
    summary["port_bit_count"] = bit_port
    summary["port_scalar_count"] = scalar_port
    summary["port_dir_dist"] = dict(dir_counter)
    summary["port_without_position"] = no_pos
    print("\n== Port (端口) ==")
    print(f"  总数(port_iter): {len(ports)}  (DEF PINS 声明 = 54)")
    print(f"    其中 bus={bus_port}  bit={bit_port}  scalar={scalar_port}")
    print(f"  方向分布: {dict(dir_counter)}")
    print(f"  无位置信息的端口数: {no_pos}")

    with open(os.path.join(OUT_DIR, "def_ports.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(port_rows[0].keys()))
        w.writeheader()
        w.writerows(port_rows)

    # ---------------------------------------------------------------- nets
    nets = list(top.net_iter())
    use_counter = Counter()
    special = normal = 0
    bus_net = bit_net = scalar_net = 0
    total_wire = 0
    total_via = 0
    net_shape_rows = []
    for n in nets:
        u = enum_name(n.use())
        use_counter[u] += 1
        if u in ("POWER", "GROUND", "ANALOG", "BACKUP_POWER", "BACKUP_GROUND"):
            special += 1
        else:
            normal += 1
        if n.is_bus():
            bus_net += 1
        elif n.is_bit():
            bit_net += 1
        else:
            scalar_net += 1
        n_wire = n_via = 0
        for shp in n.shape_iter():
            if shp.is_wire():
                n_wire += 1
            elif shp.is_via():
                n_via += 1
        total_wire += n_wire
        total_via += n_via
        if n_wire or n_via:
            net_shape_rows.append({"net": n.name, "use": u,
                                   "wire_shapes": n_wire, "via_shapes": n_via})

    summary["net_count"] = len(nets)
    summary["net_bus_count"] = bus_net
    summary["net_bit_count"] = bit_net
    summary["net_scalar_count"] = scalar_net
    summary["net_use_dist"] = dict(use_counter)
    summary["special_net_count"] = special
    summary["normal_net_count"] = normal
    summary["total_wire_shapes"] = total_wire
    summary["total_via_shapes"] = total_via

    print("\n== Net (线网) ==")
    print(f"  总数(net_iter): {len(nets)}  (DEF NETS 声明 = 301)")
    print(f"    其中 bus={bus_net}  bit={bit_net}  scalar={scalar_net}")
    print(f"  use 分布: {dict(use_counter)}")
    print(f"  特殊网(电源地等): {special}   普通信号网: {normal}")
    print(f"  物理布线形状: wire={total_wire}  via={total_via}")

    with open(os.path.join(OUT_DIR, "def_nets.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["net", "use", "wire_shapes", "via_shapes"])
        w.writeheader()
        w.writerows(net_shape_rows)

    # ---------------------------------------------------------------- gcell / track
    gcells = list(top.gcellgrid_iter())
    tracks = list(top.track_iter())
    summary["gcellgrid_count"] = len(gcells)
    summary["track_count"] = len(tracks)
    print("\n== GcellGrid / Track ==")
    print(f"  GCellGrid: {len(gcells)}")
    for g in gcells:
        print(f"    num={g.num} start={g.start} space={g.space} "
              f"horizontal={g.is_horizontal()}")
    print(f"  Track: {len(tracks)}")
    track_layer_counter = Counter(t.layer().name for t in tracks)
    print(f"    按层分布: {dict(track_layer_counter)}")

    # ---------------------------------------------------------------- 汇总导出
    with open(os.path.join(OUT_DIR, "def_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        for k, v in summary.items():
            w.writerow([k, v])

    print("\n[parse_def] 完成，输出 CSV 到", OUT_DIR)


if __name__ == "__main__":
    main()
