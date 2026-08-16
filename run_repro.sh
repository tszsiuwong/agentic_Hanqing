#!/bin/bash
# Reproduce analysis for all 6 designs (robust: continues on per-script errors)
cd /home/zixiao/agentic_Hanqing
source datalens_env.sh
OUT=results/repro
mkdir -p "$OUT"

run_design() {
  local name=$1 v=$2 lib=$3
  local o=$OUT/$name
  mkdir -p "$o"
  echo "===================== $name ====================="
  echo "--- netlist_profiler ---"
  python3.11 analysis/netlist_profiler.py "$v" --out "$o" > "$o/netlist_profiler.log" 2>&1 || echo "  [FAIL netlist_profiler]"
  echo "--- clock_analysis ---"
  python3.11 analysis/clock_analysis.py "$v" --lib "$lib" --out "$o" > "$o/clock_analysis.log" 2>&1 || echo "  [FAIL clock_analysis]"
  echo "--- count_instances ---"
  python3.11 analysis/count_instances.py "$v" --png "$o" > "$o/count_instances.log" 2>&1 || echo "  [FAIL count_instances]"
  echo "--- connectivity_analysis ---"
  ( cd "$o" && python3.11 /home/zixiao/agentic_Hanqing/analysis/connectivity_analysis.py "/home/zixiao/agentic_Hanqing/$v" > connectivity.log 2>&1 ) || echo "  [FAIL connectivity]"
  echo "--- cell_area ---"
  local lef=""
  case "$name" in
    *nangate45*) lef="test/Nangate45/NangateOpenCellLibrary.tech.lef test/Nangate45/NangateOpenCellLibrary.macro.lef" ;;
    *sky130hd*)  lef="test/sky130hd/sky130_fd_sc_hd.tlef test/sky130hd/sky130_fd_sc_hd_merged.lef" ;;
    *sky130hs*)  lef="test/sky130hs/sky130_fd_sc_hs.tlef test/sky130hs/sky130_fd_sc_hs_merged.lef" ;;
  esac
  python3.11 analysis/cell_area.py "$v" $lef > "$o/cell_area.log" 2>&1 || echo "  [FAIL cell_area]"
  echo "DONE $name"
}

run_design gcd_sky130hs      test/gcd_sky130hs.v      test/sky130hs/sky130_fd_sc_hs__tt_025C_1v80.lib
run_design gcd_nangate45     test/gcd_nangate45.v     test/Nangate45/NangateOpenCellLibrary_typical.lib
run_design aes_nangate45     test/aes_nangate45.v     test/Nangate45/NangateOpenCellLibrary_typical.lib
run_design ibex_sky130hd     test/ibex_sky130hd.v     test/sky130hd/sky130_fd_sc_hd__tt_025C_1v80.lib
run_design jpeg_sky130hd     test/jpeg_sky130hd.v     test/sky130hd/sky130_fd_sc_hd__tt_025C_1v80.lib
run_design tinyRocket_nangate45 test/tinyRocket_nangate45.v test/Nangate45/NangateOpenCellLibrary_typical.lib
echo "ALL_REPRO_DONE"
