# 网表分析脚本

基于 Dizo Python API (datalens) 的通用网表分析工具，支持 LEF + DEF + LIB 输入。

## 环境准备

需要 **Python 3.11** 和 Dizo 带 `datalens` 模块编译的产物。

### 方式 1：环境变量

```bash
export PATH=/path/to/datalens/bin:$PATH
export LD_LIBRARY_PATH=/path/to/datalens/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/path/to/datalens/lib:$PYTHONPATH
```

然后直接：

```bash
python3.11 analysis/count_instances.py <tech.lef> <cell.lef> <design.def>
```

### 方式 2：用 datalens_python 脚本（推荐，自动设好环境）

```bash
/path/to/datalens/bin/datalens_python analysis/count_instances.py <tech.lef> <cell.lef> <design.def>
```

---

## 脚本说明

| 脚本 | 功能 | 用法 |
|------|------|------|
| `count_instances.py` | Instance / Cell / Port / Net 基础统计 | `... <tech.lef> <cell.lef> <design.def>` |
| `cell_distribution.py` | 单元类型分布 + 柱状图 | `... <tech.lef> <cell.lef> <design.def> <output.png>` |
| `connectivity_analysis.py` | Degree / Fanout / Rent's Rule | `... <tech.lef> <cell.lef> <design.def> <output.png>` |
| `seq_comb_analysis.py` | 时序/组合比 + 功能类别 | `... <tech.lef> <cell.lef> <design.def> <timing.lib> <output.png>` |

---

## 示例：GCD (Nangate45)

```bash
datalens_python analysis/count_instances.py \
    Nangate45/tech.lef \
    Nangate45/cells.lef \
    gcd/gcd_route.def

datalens_python analysis/cell_distribution.py \
    Nangate45/tech.lef \
    Nangate45/cells.lef \
    gcd/gcd_route.def \
    gcd_cells.png

datalens_python analysis/connectivity_analysis.py \
    Nangate45/tech.lef \
    Nangate45/cells.lef \
    gcd/gcd_route.def \
    gcd_connectivity.png

datalens_python analysis/seq_comb_analysis.py \
    Nangate45/tech.lef \
    Nangate45/cells.lef \
    gcd/gcd_route.def \
    Nangate45/NangateOpenCellLibrary.lib \
    gcd_seq_comb.png
```
