# GCD 网表结构分析 — Dizo (datalens)

对 gcd 一整套文件（RTL → 综合后 → 布局布线后）做结构分析，产出对比指标。

- 分析环境：`~/agentic_Hanqing`，`source datalens_env.sh` + `python3.11`，datalens 导入正常。
- 输入文件（只读）：
  - `~/or_synth_demo/gcd_rtl.v`（RTL 源码）
  - `~/or_synth_demo/gcd_synth.v`（Yosys 综合后门级网表，231 cell）
  - `~/or_synth_demo/demo_out.def`（OpenROAD 布局布线后 DEF，PDK = Nangate45/FreePDK45）
- 结果目录：`~/agentic_Hanqing/results/gcd_dizo/`（子目录 `synth/`、`pnr/`、`rtl/`）。

## 1. 三文件核心指标对比

| 指标 | RTL `gcd_rtl.v` | 综合后 `gcd_synth.v` | 布局后 `demo_out.def` |
|---|---|---|---|
| 加载方式 | load_netlist | load_netlist | load_def(+LEF) |
| Instance 数 | 0（见说明） | 231 | 231 |
| Cell 类型数 | 0 | 21 | 21 |
| 端口数 | 56（IN 37 / OUT 19） | 56（IN 37 / OUT 19） | 56（IN 37 / OUT 19） |
| Net 数 | 69 | 358 | 307 |
| 宏单元 | 无 | 无 | 无 |
| Degree（标准单元）均值/范围 | N/A | μ=3.7 σ=0.7，[2–6] | μ=3.7 σ=0.7，[2–6] |
| Fanout（信号网）均值/P95/max | μ=0.27 / P95=1 / 1 | μ=2.36 / P95=6 / 20 | μ=1.89 / P95=5 / 19 |
| Clock 网 fanout | 0 | 34 | 34 |
| Reset 网 fanout | 0 | 2 | 2 |
| Rent p / k | N/A | 1.186 / 1.32 | 1.186 / 1.32 |

单元分布（综合后与布局后完全一致，`diff` 验证 `cell_distribution.csv` 相同）：

| Cell | 数量 | 占比 |
|---|---|---|
| AOI21_X1 | 34 | 14.7% |
| DFF_X1 | 34 | 14.7% |
| MUX2_X1 | 32 | 13.9% |
| NOR2_X1 | 27 | 11.7% |
| NAND2_X1 | 19 | 8.2% |
| XNOR2_X1 | 19 | 8.2% |
| AOI22_X1 | 12 | 5.2% |
| OAI21_X1 | 9 | 3.9% |
| OR2_X1 | 8 | 3.5% |
| XOR2_X1 | 8 | 3.5% |
| 其余 11 种 | 29 | 12.6% |

Top 3（AOI21 / DFF / MUX2）合计 100 个，占 43%。

## 2. 时钟结构（`clock_analysis.py`，综合后）

| 项目 | 值 |
|---|---|
| 时序单元（DFF） | 34 |
| 时钟门控（ICG） | 0 |
| 时钟 buffer | 0 |
| 组合逻辑 | 197 |
| 时钟域 | 1（`clk`，34 个寄存器） |
| 带复位寄存器 | 0 / 34 |
| 带使能/scan 寄存器 | 0 / 34 |
| 时钟树 | 单层（L0），无 buffer，直连 34 个 DFF 叶子 |

时序/组合比 ≈ 34 : 197 ≈ 1 : 5.8。时序单元全部为 `DFF_X1`。

## 3. 结论与对比说明

- **综合后 vs 布局后 cell 数一致**：均为 231 instance、21 种类型，单元分布完全相同。DEF 是综合网表布局布线后的结果，逻辑结构（cell 组成）保持不变，符合预期。
- **端口数一致**：三个阶段均为 56 端口（37 IN / 19 OUT），端口完全保留。
- **Net 数不一致（358 → 307）**：布局后 DEF 比综合网表少了 51 条 net。原因：OpenROAD 写出的 DEF 只保留实际参与布线的信号网，综合网表中未被使用/悬空/被优化掉的 net 不会进入 DEF；DEF 中电源地走 SPECIALNETS 不计入普通 net。因此 `load_def` 分支统计的 net 数偏少，signal fanout 均值/最大值也相应略降（μ 2.36→1.89，max 20→19）。
- **RTL 不能直接做门级结构分析**：`load_netlist` 能成功解析 RTL（读入 10 个 module，端口 56 个、net 69 条），但 instance 数为 0——因为 RTL 里全是层次化子模块实例（`GcdUnitCtrlRTL_*`、`GcdUnitDpathRTL_*` 等）和 `always` 行为描述，没有标准单元叶子；`netlist_profiler.py` 只统计 `is_hier()==False` 的门级叶子实例，故结果为 0。结论：RTL 需先综合成门级网表才能用该脚本分析。

## 4. 遇到的问题

1. **DEF 必须先读 LEF，否则段错误（SIGSEGV）**：直接 `load_def(demo_out.def)` 报错 "The LEF file is not read before the DEF file is read"，随后 `present_module()` 返回空导致 segfault（exit 139）。修复：按脚本约定传入 LEF —— `netlist_profiler.py demo_out.def ~/OpenROAD/test/Nangate45/Nangate45.lef --out ...` 后正常。该 DEF 的 PDK 是 Nangate45（FreePDK45 site），与 `demo.tcl` 中 `read_lef Nangate45.lef` 一致。
2. **RTL 分析在画图阶段崩溃（脚本 bug）**：RTL 无门级实例时 `stdcell_degrees` 为空，`netlist_profiler.py` 第 293 行 `ax.bar(*zip(*dc))` 对空 `dc` 解包失败（`TypeError: Axes.bar() missing 2 required positional arguments`）。CSV 已正常写出，仅 PNG 未生成。属于脚本对空设计的边界未处理，不影响门级网表分析。
3. **综合网表读入告警**：Yosys 输出的 `gcd_synth.v` 端口与内部 net 同名（如 `clk`），datalens 给出 `[VRLG-I-0033] Port and net have the same name` 告警并自动删除同名 net，不影响统计结果（clk 仍正确识别为 clock 网，FO=34）。
4. `connectivity_analysis.py`（复用 `src/dizo_utils.py`）的 Fanout 口径与 profiler 不同（统计所有 pin 含时钟，μ=2.6），本文以 `netlist_profiler.py` 的「信号网 fanout（排除时钟/复位）」为准。

## 5. 输出文件清单

```
~/agentic_Hanqing/results/gcd_dizo/
├── synth/                  # gcd_synth.v（netlist_profiler + clock_analysis + connectivity_analysis）
│   ├── summary.csv  cell_distribution.csv  special_nets.csv  macro_cells.csv  seq_cells.csv
│   ├── clock_summary.csv  clock_domains.csv  clock_tree.csv
│   └── cells.png  cell_functions.png  connectivity.png  clock_structure.png  gcd_connectivity.png
├── pnr/                    # demo_out.def（netlist_profiler）
│   └── summary.csv  cell_distribution.csv  special_nets.csv  macro_cells.csv + 3 PNG
└── rtl/                    # gcd_rtl.v（netlist_profiler，0 instance，CSV 已出）
    └── summary.csv  cell_distribution.csv  special_nets.csv  macro_cells.csv + 2 PNG（缺 connectivity.png）
```
