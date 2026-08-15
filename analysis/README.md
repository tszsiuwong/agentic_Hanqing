# 设计分析脚本

基于 Dizo Python API (datalens)。

## 环境

```bash
export LD_LIBRARY_PATH=/path/to/datalens/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/path/to/datalens/lib:$PYTHONPATH
```

## 网表结构分析 `netlist_profiler.py`

加载一次，全量输出：基础统计 → 单元分布 → 功能分类 → 连接度 → 宏单元 → 特殊网 → Rent → 图表。

```bash
datalens_python analysis/netlist_profiler.py design.v
datalens_python analysis/netlist_profiler.py design.def tech.lef cells.lef
datalens_python analysis/netlist_profiler.py design.v --out out_dir/   # 指定输出目录
```

分析采用三层分离，避免异构单元互相污染统计：

- **标准单元**：Degree 均值/σ/范围、Fanout 均值/P95/max
- **宏单元**（SRAM/ROM/regfile/pad）：单独统计，不计入 Degree
- **特殊网**（clock/reset/constant）：单独列出，不计入 Fanout

输出：`summary.csv` / `macro_cells.csv` / `special_nets.csv` / `cell_distribution.csv` + 3 张图。

## 时钟结构分析 `clock_analysis.py`

独立于网表结构分析。输出：单元分类（时序/门控/时钟 buffer/组合）、时钟域（含频率）、时序单元类型分布、复位/使能统计、时钟树拓扑。

```bash
datalens_python analysis/clock_analysis.py design.v
datalens_python analysis/clock_analysis.py design.v --lib cells.lib          # 用 is_clock 精确识别
datalens_python analysis/clock_analysis.py design.v --lib cells.lib --sdc design.sdc  # 关联时钟频率
datalens_python analysis/clock_analysis.py design.v --out out_dir/
```

- `--lib <file>`：加载 Liberty，用 `lib_pin.is_clock` 精确识别时钟引脚（回退启发式）
- `--sdc <file>`：解析 `create_clock` 拿时钟周期/频率，关联时钟域

输出：`clock_summary.csv` / `clock_domains.csv`（含频率）/ `seq_cells.csv` / `clock_tree.csv` + `clock_structure.png`。

## 分步脚本（按需）

| Step | 脚本 | 输入 | 分析内容 |
|------|------|------|---------|
| 1 | `count_instances.py` | `.v` 或 `.def` | 基础统计 + 单元分布 + 功能分类 + 图 |
| 2 | `cell_area.py` | + tech.lef + macro.lef | 单元面积/几何 |
| 3 | `timing_analysis.py` | + timing.lib | 时序/组合比 |
| 4 | `placement_analysis.py` | .def + tech.lef + macro.lef | 物理 placement |
| 5 | `connectivity_analysis.py` | `.v` 或 `.def` | Degree/Fanout/Rent + 图 |

## 示例：GCD

```bash
datalens_python analysis/netlist_profiler.py gcd.v
```

```
================================================================
  基础统计
================================================================
  Instance:  301
  Cell 类型: 23
  Port:      56  (IN:37  OUT:19  INOUT:0)
  Net:       376

================================================================
  连接度
================================================================
  Degree (标准单元): 均值 3.5  σ=1.2  范围 2–6
  Fanout (信号网): 均值 2.8  P95=5  最大 35

================================================================
  宏单元（SRAM/ROM/regfile/pad）—— 单独分析
================================================================
  无宏单元

================================================================
  特殊网（时钟/复位/常量）—— 单独分析
================================================================
  Clock 网: 1 条 | Reset 网: 1 条 | 常量网: 0 条
  [clock   ] clk                                    FO=34
  [reset   ] reset                                  FO=2
  Rent  p:   1.365    k: 0.42  (标准单元)

================================================================
  Done — 图表 → out/
================================================================
```
