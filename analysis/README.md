# 递进式设计分析

基于 Dizo Python API (datalens) 的通用设计分析工具。

## 环境准备

```bash
export LD_LIBRARY_PATH=/path/to/datalens/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/path/to/datalens/lib:$PYTHONPATH
# 或直接:
/path/to/datalens/bin/datalens_python analysis/design_analyze.py ...
```

## 五步递进

| Step | 输入 | 新增分析 |
|------|------|---------|
| 1 | `design.v` | 基础统计 (Inst/Cell/Port/Net) |
| 2 | `+ tech.lef + macro.lef` | 单元面积/几何 |
| 3 | `+ timing.lib` | 时序/组合比 |
| 4 | `design.def` 替换 `.v` | 物理 placement/利用率 |
| 5 | `+ timing.lib` | 全量分析 + 连接度/Rent + 图表 |

## 用法

```bash
# Step 1: 纯网表
datalens_python analysis/design_analyze.py design.v

# Step 2: +LEF
datalens_python analysis/design_analyze.py design.v tech.lef cells.lef

# Step 3: +LIB
datalens_python analysis/design_analyze.py design.v tech.lef cells.lef timing.lib

# Step 4: DEF (placement)
datalens_python analysis/design_analyze.py design.def tech.lef cells.lef --png out/

# Step 5: 全量
datalens_python analysis/design_analyze.py design.def tech.lef cells.lef timing.lib --png out/
```

## 输出

终端打印分 Step 1-5 递进展示，`--png <dir>` 生成 3 张图：
- `cells.png` — Cell 分布柱状图
- `connectivity.png` — Degree + Fanout 分布
- `seq_comb.png` — 时序/组合比 (需 LIB)
