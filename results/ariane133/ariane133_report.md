# Ariane133 网表分析

Ariane RISC-V 64 位处理器核心。

## 基础统计

| 指标 | 数值 |
|------|------|
| Instance | 83,924 |
| Cell 类型 | 77 |
| Port | 500 (IN:221 OUT:279) |
| Net | 109,590 |

![单元分布](cells.png)  ![功能分类](cell_functions.png)

## 连接度

| 指标 | 数值 |
|------|------|
| Degree 均值 | 4.6 (σ=1.6) |
| Degree 范围 | 2–44 |
| Fanout 均值（信号网） | 3.2 (P95=6) |
| Fanout 最大（信号网） | 362 |

## 特殊网（时钟/复位/常量）

> 单独分析，不计入上述 Fanout 统计。

| 类型 | 网名 | Fanout |
|------|------|-------:|
| clock | clk_i | 19,629 |
| reset | rst_ni | 19,585 |
| constant | LOGICAL_1 | 705 |
| constant | LOGICAL_0 | 13 |
| reset | csr_regfile_i_mtvec_rst_load_q | 7 |

## Rent's Rule

| 参数 | 数值 |
|------|------|
| **p** | **1.377** |
| k | 0.06 |

![连接度](connectivity.png)

## 设计特征

- **RISC-V 核心**：84K 门、77 种单元、500 IO 口，典型嵌入式处理器规模
- **Degree 均值 4.6**：高于 Nangate45 平均，使用更多复杂门（AOI/OAI），时序优化结果
- **时序单元占比高**：SDFFR_X1 (10,272) + DFFR_X1 (9,264) ≈ 23%，含 scan DFF（SDFFR）
- **时钟/复位树**：clk_i 驱动 19,629、rst_ni 驱动 19,585，均接近全设计 1/4 实例
- **信号网扇出健康**：P95=6，最大 362（scoreboard 旁路控制信号，需关注 buffer 插入）
- **Rent p=1.377**：在当前 Benchmark 中最高，RISC-V 控制路径复杂、互联不规则
