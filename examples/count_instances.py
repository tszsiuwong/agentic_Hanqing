#!/usr/bin/env python3
"""
统计 Verilog 网表中的 Instance 数量。

用法:
    python examples/count_instances.py <netlist.v>

示例:
    python examples/count_instances.py tests/st/db_tclio/netlist/design.v
"""

import sys
import datalens


def count_instances(netlist_file):
    print(f"Loading: {netlist_file}")
    ret = datalens.exchange.load_netlist([netlist_file])
    if ret != 0:
        print(f"Error: load_netlist returned {ret}")
        sys.exit(1)

    project = datalens.design.present_project()
    project.make_unique()
    top = project.present_module()

    HierFilterType = datalens.design.HierFilterType

    total_all = top.inst_count(HierFilterType.ALL)
    total_leaf = top.inst_count(HierFilterType.LEAF)
    total_hier = top.inst_count(HierFilterType.HIER)

    print(f"\nTop Module: {top.name}")
    print(f"  Total instances: {total_all}")
    print(f"    Leaf cells:    {total_leaf}")
    print(f"    Hier blocks:   {total_hier}")

    # 按 ref_name 分组统计
    ref_count = {}
    for inst in top.inst_iter():
        ref = inst.ref_name
        ref_count[ref] = ref_count.get(ref, 0) + 1

    print(f"\n  Cell type breakdown ({len(ref_count)} types):")
    for ref in sorted(ref_count, key=ref_count.get, reverse=True):
        print(f"    {ref}: {ref_count[ref]}")

    # 递归统计所有层级
    all_cells = top.get_cells("*", "", True)
    print(f"\n  Total cells (hierarchical): {len(all_cells)}")

    net_count = top.net_count()
    port_count = top.port_count()
    print(f"\n  Ports: {port_count}")
    print(f"  Nets:  {net_count}")

    project.destroy()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/count_instances.py <netlist.v>")
        sys.exit(1)

    count_instances(sys.argv[1])
