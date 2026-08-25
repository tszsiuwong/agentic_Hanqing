# agentic_Hanqing

基于 Dizo 的 EDA 设计分析工具集。用 dizo 的 Python 绑定 `datalens` 对各类 EDA 文件做结构分析，
并跑通「综合 → 布局布线 → 解析」的完整链路。

## 结构

```
├── analysis/                    # 分析脚本（[详见](analysis/README.md)）
│   ├── netlist_profiler.py      # 网表结构一键分析（宏单元/特殊网/标准单元分离）
│   ├── clock_analysis.py        # 时钟结构分析（时钟域/时序单元/门控）
│   ├── count_instances.py       # 基础统计 + 单元分布
│   ├── connectivity_analysis.py # Degree / Fanout / Rent
│   ├── cell_area.py             # 单元面积/几何（需 LEF）
│   ├── timing_analysis.py       # 时序/组合比（需 Liberty）
│   └── placement_analysis.py    # 物理布局（需 DEF + LEF）
├── src/dizo_utils.py            # 可复用工具库
├── results/                     # 各 benchmark 分析结果 + repro/ + 解析任务输出
├── docs/                        # 参考文档（含 dizo 解析指南）
└── test/                        # 测试网表（本地生成，不入库）
```

## 快速开始

```bash
# 配置 datalens 环境（一次性）
cd ~/agentic_Hanqing && source datalens_env.sh

# 网表结构一键分析
python3.11 analysis/netlist_profiler.py <设计.v>

# 时钟结构分析
python3.11 analysis/clock_analysis.py <设计.v>

# 分步分析
python3.11 analysis/count_instances.py <设计.v>
python3.11 analysis/connectivity_analysis.py <设计.v>
```

## dizo 文件解析（datalens）

dizo 的 `datalens` 能解析流程里几乎所有关键格式，脚本在 `results/` 对应任务目录下，报告见 `docs/`。

| 格式 | datalens 接口 | 脚本 | 报告 |
|------|--------------|------|------|
| 网表 Verilog | `exchange.load_netlist` | `analysis/*.py` | [网表分析](docs/dizo_netlist_analysis.md) |
| SDC | `constraint_view`（仅文件名，需文本解析） | `results/more_parse/sdc_parse.py` | [更多格式](docs/dizo_more_formats_parse.md) |
| Liberty | `exchange.load_lib` + `timinglib` | `results/more_parse/lib_parse.py` | 同上 |
| SPEF | `exchange.load_spef` | `results/more_parse/spef_parse.py` | 同上 |
| SAIF | `exchange.load_saif` | `results/more_parse/saif_parse.py` | 同上 |
| VCD | `exchange.load_vcd` | `results/more_parse/vcd_parse.py` | 同上 |
| LEF | `exchange.load_lef` | `results/def_lef_parse/parse_lef.py` | [DEF/LEF](docs/dizo_def_lef_parse.md) |
| DEF | `exchange.load_def` | `results/def_lef_parse/parse_def.py` | 同上 |

完整体系介绍（物理设计工程师视角）：[dizo 物理设计工程师指南](docs/dizo_pd_engineer_guide.md)

## 工具链（全开源）

```
RTL(.v) --Yosys综合--> 门级网表 --OpenROAD布局布线--> GDS/DEF
                              │
                              └─> dizo(datalens) 做结构/物理/时序解析
```

| 工具 | 作用 |
|------|------|
| Yosys | 逻辑综合 |
| OpenROAD | 布局规划/摆放/时钟树/布线 |
| dizo + datalens | 数据模型 + 全格式解析分析 |

## 复现结果

`results/repro/` 记录了用 dizo 重新分析 6 个 OpenROAD test 设计的完整结果
（gcd / aes / ibex / jpeg / tinyRocket），对比见 `results/design_characterization.md`。

## 案例

| Benchmark | 规模 | 报告 |
|-----------|------|------|
| GCD | 301 | [报告](results/gcd/gcd_report.md) |
| JPEG | 39,866 | [报告](results/jpeg/jpeg_report.md) |
| ariane133 | 83,924 | [报告](results/ariane133/ariane133_report.md) |
| openc910 | 938,955 | [报告](results/openc910/openc910_report.md) |
| superblue1 | 1,206,104 | [报告](results/superblue1/superblue1_report.md) |
| NVDLA | 2,229,371 | [报告](results/nvdla/nvdla_report.md) |
| mempool | 2,579,164 | [报告](results/mempool/mempool_report.md) |

[设计特征化对比](results/design_characterization.md)

## 文档

| 文档 | 说明 |
|------|------|
| [dizo 物理设计工程师指南](docs/dizo_pd_engineer_guide.md) | PD 视角的全流程 + 格式解析总览 |
| [网表分析报告](docs/dizo_netlist_analysis.md) | gcd 网表（RTL/综合/布局）结构分析 |
| [DEF/LEF 解析报告](docs/dizo_def_lef_parse.md) | LEF 物理库 + DEF 布局解析 |
| [更多格式解析报告](docs/dizo_more_formats_parse.md) | SDC/Liberty/SPEF/SAIF/VCD 解析 |
| [quickstart](docs/quickstart.md) | 工具快速上手 |
| [python-api](docs/python-api.md) | datalens Python API 参考 |
