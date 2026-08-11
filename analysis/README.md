# 设计分析脚本

基于 Dizo Python API (datalens)，按需选取。

## 环境

```bash
export LD_LIBRARY_PATH=/path/to/datalens/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/path/to/datalens/lib:$PYTHONPATH
```

## 一键分析

```bash
datalens_python analysis/analyze.py design.v
datalens_python analysis/analyze.py design.def tech.lef cells.lef
```

加载一次，全量输出：基础统计 → 单元分布 → 功能分类 → 连接度 → Rent → 图表。

## 分步脚本（按需）

| Step | 脚本 | 输入 | 分析内容 |
|------|------|------|---------|
| 1 | `count_instances.py` | `.v` 或 `.def` | 基础统计 + 单元分布 + 功能分类 + 图 |
| 2 | `cell_area.py` | + tech.lef + macro.lef | 单元面积/几何 |
| 3 | `timing_analysis.py` | + timing.lib | 时序/组合比 |
| 4 | `placement_analysis.py` | .def + tech.lef + macro.lef | 物理 placement |
| 5 | `connectivity_analysis.py` | `.v` 或 `.def` | Degree/Fanout/Rent + 图 |

## 示例：GCD (Nangate45)

### 一键运行

```bash
datalens_python analysis/analyze.py gcd.v
```

```
============================================================
  基础统计
============================================================
  Instance:  301
  Cell 类型: 23
  Port:      56  (IN:32  OUT:16  INOUT:8)
  Net:       376

============================================================
  单元分布
============================================================
  Cell                        数量      占比
  ------------------------------------------
  INV_X1                      42     14.0%
  DFF_X1                      34     11.3%
  AOI22_X1                    32     10.6%
  ...

  Top 3 (INV_X1, DFF_X1, AOI22_X1) = 108 (36%)

============================================================
  功能分类
============================================================
  INV               68  (22.6%)
  DFF               34  (11.3%)
  AOI22             32  (10.6%)
  NAND2             24  (8.0%)
  NOR2              19  (6.3%)

============================================================
  连接度
============================================================
  Degree:    均值 3.6  范围 1–6
  Fanout:    均值 3.0  最大 35
  Rent  p:   1.366    k: 0.40

============================================================
  Done — 图表 → out/
============================================================
```

### 分步运行（按需）

```bash
datalens_python analysis/count_instances.py design.v        # 基础统计+图
datalens_python analysis/connectivity_analysis.py design.v  # 连接度+图
datalens_python analysis/cell_area.py design.v tech.lef cells.lef  # 面积
datalens_python analysis/timing_analysis.py design.v ... timing.lib  # 时序
datalens_python analysis/placement_analysis.py design.def ... # placement
```
