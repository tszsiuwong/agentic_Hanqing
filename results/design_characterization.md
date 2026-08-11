# Design Characterization

> 从网表结构特征预判物理设计瓶颈：Congestion、时序收敛、可布线性。

---

## 1. 方法论

| 维度 | 指标 | 预判方向 |
|------|------|----------|
| 规模 | Instance 数、Cell 类型数 | 工具容量、runtime 估算 |
| 连接度 | Degree 分布、Fanout 分布 | 布线密度、局部拥塞 |
| 拓扑复杂度 | Rent's Rule p 值 | 全局互连复杂度 |
| 功能特征 | 时序/组合比、算术单元密度 | 关键路径深度、时钟树规模 |

---

## 2. Benchmark 总览

| Benchmark | Instance | Cell 类型 | Ports | Nets | 报告 |
|-----------|----------|-----------|-------|------|------|
| GCD | 301 | 23 | 56 | 376 | [gcd_report.md](gcd/gcd_report.md) |
| JPEG | 39,866 | 47 | 53 | 48,752 | [jpeg_report.md](jpeg/jpeg_report.md) |
| Ariane133 | 83,924 | 77 | 500 | 109,590 | [ariane133_report.md](ariane133/ariane133_report.md) |
| openc910 | 938,955 | 64 | 1,388 | 957,583 | [openc910_report.md](openc910/openc910_report.md) |
| superblue1 | 1,206,104 | 248 | 6,528 | 1,215,710 | [superblue1_report.md](superblue1/superblue1_report.md) |
| NVDLA | 2,229,371 | 102 | 1,765 | 2,818,808 | [nvdla_report.md](nvdla/nvdla_report.md) |
| mempool | 2,579,164 | 96 | 11,439 | 3,001,949 | [mempool_report.md](mempool/mempool_report.md) |

---

## 3. 连接度

| Benchmark | Degree μ | Degree σ | Fanout μ | Fanout max |
|-----------|----------|----------|----------|------------|
| GCD | 3.5 | 1.2 | 2.9 | 35 |
| JPEG | 3.5 | 1.0 | 2.9 | — |
| Ariane133 | 4.6 | 1.6 | 3.6 | 19,629 |
| openc910 | 3.9 | 1.2 | 3.8 | 84,231 |
| superblue1 | 3.1 | 4.7 | 3.1 | 7,213 |
| NVDLA | 3.8 | 4.2 | 3.1 | 355,370 |
| mempool | 4.1 | 1.7 | 3.5 | 271,528 |

### 归因

Degree 均值反映门级复杂度。Ariane133（4.6）最高，使用更多 AOI/OAI 复杂门做时序优化。σ 值区分了均质设计（JPEG σ=1.0）和异构设计（superblue1 σ=4.7，含宏单元/IP 导致 degree 方差极大）。高扇出线是 clock/reset，需关注 buffer 插入策略。

---

## 4. Rent's Rule

| Benchmark | p | k |
|-----------|---|---|
| GCD | 1.365 | 0.42 |
| JPEG | 1.215 | 0.30 |
| Ariane133 | 1.377 | 0.06 |
| openc910 | 1.376 | 0.02 |
| superblue1 | 1.356 | 0.02 |
| NVDLA | 1.316 | 0.04 |
| mempool | 1.371 | 0.02 |

### 归因

- **p ≈ 1.2**：数据通路型（JPEG、NVDLA），互联规整
- **p ≈ 1.35–1.38**：控制+数据混合型（GCD、superblue1、Ariane133），互联较复杂
- **p > 1.5**：未出现，说明基准测试中无极端互联设计

Ariane133 的 p=1.377 最高，RISC-V 控制路径最复杂。Rent p 与规模几乎无关，完全是设计结构特征的反映。

---

## 5. 设计身份推断

> 以下推断基于纯网表结构特征，未参考 RTL 源码。命名已知的 benchmark 用于独立验证。

### GCD — 控制密集型算法
| 特征 | 数值 | 推断 |
|------|------|------|
| 301 gates, 34 DFF | 小型 FSM+Datapath | 教学级设计，无 DFT |
| XNOR2 16 (5.3%) | 相等比较器 | a==b 判断 |
| Rent p=1.365 | 控制密集 | FSM 扇入扇出集中 |

### JPEG — 数据通路密集型
| XNOR2+XOR2 4405 (11%) | 比较器阵列 | DCT 变换 |
| FA+HA 2218 (5.6%) | 加法器树 | 矩阵乘法 |
| SDFF 3021 (68%时序) | Scan DFT | 生产级设计 |

### Ariane133 — RISC-V 处理器核心
| 84K gates, 77 类型 | 中等规模 CPU | 嵌入式 RISC-V |
| Degree 4.6, p=1.377 | 复杂门+控制密集 | 时序优化 + 不规则互联 |
| Fanout max 19,629 | 全局时钟/复位 | 大规模时钟树 |

### superblue1 — 工业级 SoC
| 1.2M gates, 248 类型 | 大规模异构设计 | 含宏单元/IP |
| Degree max 1243 | RAM/ROM 宏单元 | 存在超大模块 |
| Fanout max 7213, 6528 ports | IO 密集 | 复杂互联拓扑 |

### NVDLA — 深度学习加速器
| FA_X1 111K (5%), XNOR2 164K (7.4%) | MAC 阵列 | 卷积计算核心 |
| 273K 寄存器, p=1.325 | 深流水线 | 数据通路为主 |

> **验证**：GCD=迭代算法、JPEG=DCT编码器、NVDLA=MAC加速器、Ariane133=RISC-V核心，结构特征与实际功能一致。superblue1 因 ICCAD 竞赛匿名无法验证，但工业级异构特征符合预期。
