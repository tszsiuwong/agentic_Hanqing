# GCD 网表分析报告

用 Dizo Python API 对 GCD（Nangate45）网表进行多维度分析。

## 运行

```bash
python3.11 examples/count_instances.py   # 基础统计
python3.11 examples/gcd_analysis.py      # 单元分布可视化
python3.11 examples/connectivity_analysis.py     # Degree / Fanout / Rent
python3.11 examples/seq_comb_analysis.py    # 时序/组合比
```

---

## 基础统计

| 指标 | 数值 |
|------|------|
| 总 Instance | 301 |
| Cell 类型 | 23 种 |
| Port | 56 |
| Net | 376 |

![单元分布](gcd_analysis.png)

前三类（INV_X1、DFF_X1、AOI22_X1）占总量 44%，典型的组合逻辑+时序电路特征。

---

## 连接度分析

| 指标 | 数值 | 说明 |
|------|------|------|
| Degree 均值 | 3.6 | 每个门平均 3.6 个 pin |
| Degree 范围 | 1–6 | 符合 Nangate45 标准单元特征 |
| Fanout 均值 | 3.0 | 每条线平均驱动 3 个负载 |
| Fanout 最大 | 35 | 一条高扇出线（时钟/复位） |

---

## Rent's Rule

| 参数 | 数值 | 含义 |
|------|------|------|
| **p** | **1.366** | Rent 指数，p>1 布线复杂度偏高 |
| k | 0.4 | 每个门平均对外终端数 |

![深度分析](gcd_connectivity_analysis.png)

---

## 时序/组合比

| 类别 | 数量 | 占比 |
|------|------|------|
| 组合逻辑 | 267 | 88.7% |
| 时序逻辑 (DFF) | 34 | 11.3% |
| 组合/时序比 | 7.9 : 1 | |

### 单元功能类别 Top 5

| 类别 | 数量 |
|------|------|
| INV | 68 |
| DFF | 34 |
| AOI22 | 32 |
| NAND2 | 24 |
| NOR2 | 19 |

![逻辑分析](gcd_seq_comb_analysis.png)

---

## 总结

GCD 电路特征：301 门中等规模，组合逻辑为主（88.7%），Rent 指数 p=1.366 布线复杂度正常，有一条高扇出时钟/复位线（FO=35）。
