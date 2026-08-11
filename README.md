# agentic_Hanqing

基于 Dizo 的 EDA 设计分析工具集。

## 结构

```
├── analysis/                    # 分析脚本（[详见](analysis/README.md)）
│   ├── netlist_profiler.py      # 一键分析流水线
│   ├── count_instances.py       # 基础统计 + 单元分布
│   ├── connectivity_analysis.py # Degree / Fanout / Rent
│   ├── cell_area.py             # 单元面积/几何（需 LEF）
│   ├── timing_analysis.py       # 时序/组合比（需 Liberty）
│   └── placement_analysis.py    # 物理布局（需 DEF + LEF）
├── src/dizo_utils.py            # 可复用工具库
├── results/<benchmark>/         # 各 benchmark 分析结果
└── docs/                        # 参考文档
```

## 快速开始

```bash
# 一键分析
python3.11 analysis/netlist_profiler.py <设计.v>

# 分步分析
python3.11 analysis/count_instances.py <设计.v>
python3.11 analysis/connectivity_analysis.py <设计.v>
```

## 案例

| Benchmark | 规模 | 报告 |
|-----------|------|------|
| GCD | 301 | [报告](results/gcd/gcd_report.md) |
| JPEG | 39,866 | [报告](results/jpeg/jpeg_report.md) |
| NVDLA | 2,229,371 | [报告](results/nvdla/nvdla_report.md) |
| superblue1 | 1,206,104 | [报告](results/superblue1/superblue1_report.md) |

[设计特征化对比](results/design_characterization.md)
