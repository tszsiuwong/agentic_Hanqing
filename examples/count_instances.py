#!/usr/bin/env python3
"""GCD 网表基础统计"""
import sys
from src.dizo_utils import load_netlist, count_by_ref

netlist = sys.argv[1] if len(sys.argv) > 1 else "/home/shared/benchmarks/nangate45_3D/gcd/2_2_floorplan_io.v"

project, top = load_netlist(netlist)
HierFilterType = __import__('datalens').design.HierFilterType

refs = count_by_ref(top)
total_all = sum(refs.values())
total_leaf = top.inst_count(HierFilterType.LEAF)
total_hier = top.inst_count(HierFilterType.HIER)

print(f"\nTop Module: {top.name}")
print(f"  Total instances: {total_all}")
print(f"    Leaf cells:    {total_leaf}")
print(f"    Hier blocks:   {total_hier}")
print(f"\n  Cell types ({len(refs)}):")
for ref, cnt in sorted(refs.items(), key=lambda x: -x[1]):
    print(f"    {ref}: {cnt}")

all_cells = top.get_cells("*", "", True)
print(f"\n  Total cells (hierarchical): {len(all_cells)}")
print(f"  Ports: {top.port_count()}")
print(f"  Nets:  {top.net_count()}")

project.destroy()
