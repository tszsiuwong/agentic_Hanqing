# GCD 网表分析报告

## 运行

```bash
python3.11 analysis/netlist_profiler.py <gcd.v>
```

## 基础统计

| 指标 | 数值 |
|------|------|
| 总 Instance | 301 |
| Cell 类型 | 23 种 |
| Port | 56 (IN:37 OUT:19) |
| Net | 376 |

![单元分布](cells.png)

---

## 功能分类

![功能分类](cell_functions.png)

---

## 连接度分析

| 指标 | 数值 |
|------|------|
| Degree 均值（标准单元） | 3.5 (σ=1.2) |
| Degree 范围（标准单元） | 2–6 |
| Fanout 均值（信号网） | 2.8 (P95=5) |
| Fanout 最大（信号网） | 35 |

## 宏单元

无（纯标准单元设计）。

## 特殊网（时钟/复位/常量）

| 类型 | 网名 | Fanout |
|------|------|-------:|
| clock | clk | 34 |
| reset | reset | 2 |

---

## Rent's Rule

| 参数 | 数值 |
|------|------|
| **p** | **1.365** |
| k | 0.42 |

![连接度](connectivity.png)

---

## 总结

GCD 电路：301 门小型设计，组合逻辑为主（DFF 仅 34 个 ≈11%），Rent p=1.365 布线复杂度正常，时钟网 clk 驱动 34 个负载（FO=34）。
