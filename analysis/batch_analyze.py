#!/usr/bin/env python3
"""批量分析所有 Nangate45_3D 网表"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.dizo_utils import load_netlist, count_by_ref, get_inst_degrees, get_net_fanouts, classify_seq_comb

BENCH_DIR = "/home/shared/benchmarks/nangate45_3D"
SKIP = {"platform"}

results = {}
for d in sorted(os.listdir(BENCH_DIR)):
    if d in SKIP:
        continue
    vfile = os.path.join(BENCH_DIR, d, "2_2_floorplan_io.v")
    if not os.path.exists(vfile):
        continue
    print(f"\n{'='*50}\n{d}\n{'='*50}")
    try:
        project, top = load_netlist(vfile)
        refs = count_by_ref(top)
        degrees = get_inst_degrees(top)
        fanouts = get_net_fanouts(top)
        seq, comb = classify_seq_comb(top)
        total = sum(refs.values())

        import numpy as np
        deg_arr = np.array(sorted(degrees))
        cg = np.arange(1, len(deg_arr)+1); cp = np.cumsum(deg_arr)
        start = max(len(cg)//4, 10)
        p, log_k = np.polyfit(np.log10(cg[start:]), np.log10(cp[start:]), 1)
        k = 10**log_k

        results[d] = {
            "instances": total,
            "cell_types": len(refs),
            "ports": top.port_count(),
            "nets": top.net_count(),
            "degree_mean": float(np.mean(degrees)),
            "degree_max": max(degrees),
            "fanout_mean": float(np.mean(fanouts)),
            "fanout_max": max(fanouts),
            "rent_p": round(p, 3),
            "rent_k": round(k, 1),
            "seq_count": len(seq),
            "comb_count": len(comb),
            "cs_ratio": round(len(comb) / max(len(seq), 1), 1),
            "top_cells": sorted(refs.items(), key=lambda x: -x[1])[:5],
        }
        print(f"  Instances: {total}, Cells: {len(refs)}, Rent p={p:.3f}, C/S={len(comb)/max(len(seq),1):.1f}")

        project.destroy()
    except Exception as e:
        print(f"  ERROR: {e}")

# Print summary table
print(f"\n\n{'='*80}")
print(f"{'Design':<18} {'Inst':>8} {'Types':>6} {'Rent p':>7} {'C/S':>5} {'Deg μ':>6} {'FO μ':>6} {'Ports':>6} {'Nets':>8}")
print("-"*80)
for name in sorted(results.keys()):
    r = results[name]
    print(f"{name:<18} {r['instances']:>8} {r['cell_types']:>6} {r['rent_p']:>7.3f} {r['cs_ratio']:>5.1f} {r['degree_mean']:>6.1f} {r['fanout_mean']:>6.1f} {r['ports']:>6} {r['nets']:>8}")

# Save JSON
with open(os.path.expanduser("~/all_benchmarks.json"), "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved: ~/all_benchmarks.json")
