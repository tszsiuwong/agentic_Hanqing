# 设计分析脚本

基于 Dizo Python API (datalens)，按需选取。

## 环境

```bash
export LD_LIBRARY_PATH=/path/to/datalens/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/path/to/datalens/lib:$PYTHONPATH
# 或:
/path/to/datalens/bin/datalens_python analysis/xxx.py ...
```

## 脚本

| Step | 脚本 | 输入 | 分析内容 |
|------|------|------|---------|
| 1 | `count_instances.py` | `.v` 或 `.def` | 基础统计 |
| 2 | `cell_area.py` | + tech.lef + macro.lef | 单元面积/几何 |
| 3 | `timing_analysis.py` | + timing.lib | 时序/组合比 |
| 4 | `placement_analysis.py` | .def + tech.lef + macro.lef | 物理 placement |
| 5 | `connectivity_analysis.py` | `.v` 或 `.def` | Degree/Fanout/Rent + 图 |

## 用法

```bash
# Step 1
datalens_python analysis/count_instances.py design.v
datalens_python analysis/count_instances.py design.def tech.lef cells.lef

# Step 2
datalens_python analysis/cell_area.py design.v tech.lef cells.lef

# Step 3
datalens_python analysis/timing_analysis.py design.v tech.lef cells.lef timing.lib

# Step 4
datalens_python analysis/placement_analysis.py design.def tech.lef cells.lef

# Step 5
datalens_python analysis/connectivity_analysis.py design.v
datalens_python analysis/connectivity_analysis.py design.def tech.lef cells.lef
```
