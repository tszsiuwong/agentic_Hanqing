# agentic_Hanqing

基于 Dizo 的 EDA 网表分析工具集。

## 环境

```bash
export LD_LIBRARY_PATH=$HOME/local/python3/lib:$HOME/dizo/third_party/spring_rls/lib:$HOME/dizo/build/dizo/lib:$HOME/dizo/build/dizo/lib/modules/py:$HOME/dizo/build/dizo/parser/tclio/bin:$LD_LIBRARY_PATH
export PYTHONPATH=$HOME/dizo/build/dizo/lib/modules/py
export PATH=$HOME/local/python3/bin:$HOME/local/bin:$HOME/.local/bin:$PATH
```

## 结构

```
├── analysis/              # 通用分析脚本（适用任意网表）
│   ├── count_instances.py
│   ├── connectivity_analysis.py
│   ├── seq_comb_analysis.py
│   └── cell_distribution.py
├── src/dizo_utils.py      # 可复用工具库
├── results/<benchmark>/   # 各 benchmark 的分析结果
└── docs/                  # 参考文档
```

## 使用

```bash
python3.11 analysis/count_instances.py <网表.v>
python3.11 analysis/connectivity_analysis.py <网表.v>
python3.11 analysis/seq_comb_analysis.py <网表.v>
```

## 案例: GCD

| 指标 | 数值 |
|------|------|
| Instance | 301 |
| Cell 类型 | 23 |
| Rent p | 1.366 |
| 组合/时序比 | 7.9:1 |

详见 [`results/gcd/gcd_report.md`](results/gcd/gcd_report.md)
