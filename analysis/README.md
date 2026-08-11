# 设计分析脚本

基于 Dizo Python API (datalens)，按需选取。

## 环境

```bash
export LD_LIBRARY_PATH=/path/to/datalens/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/path/to/datalens/lib:$PYTHONPATH
```

## 脚本

| Step | 脚本 | 输入 | 分析内容 |
|------|------|------|---------|
| 1 | `count_instances.py` | `.v` 或 `.def` | 基础统计 + 单元分布 + 功能分类 + 图 |
| 2 | `cell_area.py` | + tech.lef + macro.lef | 单元面积/几何 |
| 3 | `timing_analysis.py` | + timing.lib | 时序/组合比 |
| 4 | `placement_analysis.py` | .def + tech.lef + macro.lef | 物理 placement |
| 5 | `connectivity_analysis.py` | `.v` 或 `.def` | Degree/Fanout/Rent + 图 |

## 用法

```bash
datalens_python analysis/count_instances.py design.v
datalens_python analysis/cell_area.py design.v tech.lef cells.lef
datalens_python analysis/timing_analysis.py design.v tech.lef cells.lef timing.lib
datalens_python analysis/placement_analysis.py design.def tech.lef cells.lef
datalens_python analysis/connectivity_analysis.py design.v
```

## 示例：GCD (Nangate45)

### Step 1: 纯网表基础统计

```bash
datalens_python analysis/count_instances.py gcd.v
```

```
================================================================
  纯网表基础统计
================================================================
  总 Instance:   301
  Cell 类型:     23 种
  Port:          56  (IN:32  OUT:16  INOUT:8)
  Net:           376

  Cell                    数量      占比
  --------------------------------------
  INV_X1                   42     14.0%
  DFF_X1                   34     11.3%
  AOI22_X1                 32     10.6%
  NAND2_X1                 24      8.0%
  NOR2_X1                  19      6.3%
  ...

  Top 3 (INV_X1, DFF_X1, AOI22_X1) = 108 (36%)

  功能类别           数量      占比
  ------------------------------
  INV                  68     22.6%
  DFF                  34     11.3%
  AOI22                32     10.6%
  NAND2                24      8.0%
  NOR2                 19      6.3%
  ...

Saved: cells.png
Saved: cell_functions.png
```

### Step 5: 连接度分析

```bash
datalens_python analysis/connectivity_analysis.py gcd.v
```

```
==================================================
连接度分析
==================================================
  Degree 均值: 3.6  (范围 1–6)
  Fanout 均值: 3.0  (最大 35)
  Rent p:      1.366  k: 0.40
==================================================

Saved: connectivity.png
```

### Step 3: 时序/组合比

```bash
datalens_python analysis/timing_analysis.py gcd.v tech.lef cells.lef timing.lib
```

```
==================================================
时序/组合分析
==================================================
  组合逻辑:  267  (88.7%)
  时序逻辑:  34   (11.3%)
  组合/时序比: 7.9 : 1
--------------------------------------------------
  功能类别              数量
--------------------------------------------------
  INV                   68
  DFF                   34
  AOI22                 32
  NAND2                 24
  NOR2                  19
  ...
```

### 完整运行

```bash
datalens_python analysis/count_instances.py gcd.def Nangate45.tech.lef Nangate45.cells.lef
datalens_python analysis/cell_area.py gcd.def Nangate45.tech.lef Nangate45.cells.lef
datalens_python analysis/timing_analysis.py gcd.def Nangate45.tech.lef Nangate45.cells.lef Nangate45.lib
datalens_python analysis/placement_analysis.py gcd.def Nangate45.tech.lef Nangate45.cells.lef
datalens_python analysis/connectivity_analysis.py gcd.def Nangate45.tech.lef Nangate45.cells.lef
```
