# 网表分析脚本

基于 Dizo Python API (datalens) 的通用网表分析工具。

## 环境准备

Python 3.11 + Dizo 带 `datalens` 编译产物。

```bash
export LD_LIBRARY_PATH=/path/to/datalens/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/path/to/datalens/lib:$PYTHONPATH
# 或直接用:
/path/to/datalens/bin/datalens_python analysis/xxx.py ...
```

## 脚本说明

| 脚本 | 输入 | 输出 |
|------|------|------|
| `count_instances.py` | `.def` 或 `.v` | 终端打印 |
| `cell_distribution.py` | `.def` 或 `.v` | 终端 + PNG |
| `connectivity_analysis.py` | `.def` 或 `.v` | 终端 + PNG |
| `seq_comb_analysis.py` | `.def` + `.lib` | 终端 + PNG |

## 用法

### 纯网表（Verilog）

```bash
datalens_python analysis/count_instances.py design.v
datalens_python analysis/cell_distribution.py design.v cells.png
datalens_python analysis/connectivity_analysis.py design.v connectivity.png
```

### LEF + DEF（物理设计）

```bash
datalens_python analysis/count_instances.py design.def tech.lef cells.lef
datalens_python analysis/cell_distribution.py design.def cells.png tech.lef cells.lef
datalens_python analysis/connectivity_analysis.py design.def connectivity.png tech.lef cells.lef
```

### LEF + DEF + LIB（含时序）

```bash
datalens_python analysis/seq_comb_analysis.py design.def timing.lib seq_comb.png tech.lef cells.lef
```
