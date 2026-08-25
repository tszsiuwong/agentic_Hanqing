# Dizo 文件解析能力 —— 物理设计工程师视角

> 本文从物理设计（Physical Design）工程师的视角，梳理 RTL→GDS 流程中每一步涉及的数据格式，
> 以及 dizo（datalens）如何解析、分析这些文件。所有数据均来自本机真实跑通的结果。

---

## 1. 物理设计流程与数据格式全景

物理设计是把 RTL 变成可制造的版图（GDS）的过程。每个阶段都有对应的**输入/输出数据格式**，
dizo 的作用就是作为一个统一的数据模型（data model）和文件交换（exchange）层，把这些格式读进来、存成对象、供查询分析。

| 阶段 | 工具（开源） | 关键格式 | 作用 |
|------|-------------|---------|------|
| 逻辑综合 | Yosys | Verilog(RTL) → Verilog(网表) | RTL 转门级网表 |
| 时序约束 | — | SDC | 时钟、输入/输出延迟、false path |
| 时序库 | — | Liberty(.lib) | 单元时序、功耗、面积信息（STA 依据） |
| 布局规划/摆放 | OpenROAD | LEF + DEF | 物理库 + 布局结果 |
| 时钟树/布线 | OpenROAD | DEF(带 routing) | 布线后的物理实现 |
| 寄生提取 | OpenRCX 等 | SPEF | 寄生 RC，用于 post-route STA |
| 功耗分析 | — | SAIF / VCD | 翻转率、活动性 |

dizo 的 `datalens` Python 绑定对这几种格式的支持程度不同，下面逐一说明。

---

## 2. 工具链

| 工具 | 版本/来源 | 备注 |
|------|-----------|------|
| Yosys | 0.52（apt） | 逻辑综合 |
| OpenROAD | 源码编译（gcc-15，C++20） | 布局布线，主程序 `build/bin/openroad` |
| dizo + datalens | 源码编译（gcc-12，Python 3.11） | 数据模型 + 文件解析 |

> 注意：dizo 代码较老（C++17，gcc-10 时代），需 gcc-12；OpenROAD 是 C++20 新代码，需 gcc-15。
> 两者编译环境要求正好相反。

---

## 3. 各格式解析详解

### 3.1 网表（Verilog）

- **流程角色**：综合后的门级网表，是物理设计的输入。
- **解析方法**：`datalens.exchange.load_netlist([file])`，遍历 `module_iter()` / `inst_iter(False)`。
- **能拿到**：instance 数、cell 类型、端口、net、degree/fanout、时序/组合分类、时钟域。

gcd 综合网表实测（`gcd_synth.v`）：

| 指标 | 值 |
|------|-----|
| Instance | 231 |
| Cell 类型 | 21 |
| 端口 | 56（IN 37 / OUT 19） |
| Net | 358 |
| Degree（标准单元） | μ=3.7，[2–6] |
| Fanout（信号网） | μ=2.36，P95=6，max=20 |
| 时序/组合 | 34 : 197 ≈ 1:5.8 |
| 时钟域 | 1（clk，34 个 DFF） |

**注意**：RTL 文件（含 `always` 行为描述、层次化子模块）`load_netlist` 能解析，但 instance 数为 0
（无门级叶子实例），不能直接做门级结构分析——必须先综合。

### 3.2 SDC（时序约束）

- **流程角色**：定义时钟、IO 延迟、false path 等，是 STA 和时序优化的输入。
- **解析方法**：⚠️ datalens 的 `constraint_view` 只暴露 SDC 文件名的 get/set，**没有约束查询接口**
  （`create()` 还需 MCMM 初始化，否则 SIGSEGV）。→ 需**文本/正则解析**。
- **能拿到**：create_clock（name/period/端口）、create_generated_clock、set_input_delay、
  set_output_delay、set_false_path、set_load、set_driving_cell 等。

实测（`timing_api_2.sdc`）：

```
create_clock core_clock  period 0.46ns, 端口 clk
set_input_delay  0.092 -clock core_clock  ×35（req_msg[0..31]、req_val、reset、resp_rdy）
set_output_delay 0.092 -clock core_clock  ×18（req_rdy、resp_msg[0..15]、resp_val）
```

### 3.3 Liberty（时序库）

- **流程角色**：单元的时序/功耗/面积信息，STA 和综合映射的依据。
- **解析方法**：`datalens.exchange.load_lib([file])` + `datalens.timinglib` 模块
  （`current_lib()`、`libcell_iter()`、`libpin_iter()`、`timing_iter()`、`is_clock`、`direction` 等）。
- **能拿到**：库名、cell 数、每个 cell 的面积/引脚数/timing arc 数、时序/组合单元分类、引脚方向分布。

实测：

| 库 | cell 数 | 时序单元 | 组合单元 | timing arc | 引脚方向 |
|----|--------:|---------:|---------:|-----------:|---------:|
| Nangate45 | 134 | 29 | 98 | 1494 | in 388 / out 145 |
| sky130hd | 428 | 69 | 347 | 1854 | — |

**限制**：库级单位（时间/电容单位）API 未暴露，需从 .lib 文本补充。

### 3.4 LEF（物理库）

- **流程角色**：工艺信息（层、过孔、site）+ 单元宏定义，是布局布线的基础。
- **解析方法**：`datalens.exchange.load_lef([...])`，从 `datalens.phylib.present_tech()` 取。
- **能拿到**：层（数量/类型）、via（template/rule）、site（尺寸）、macro（面积/类/引脚）。

实测（Nangate45.lef）：

| 项目 | 值 |
|------|-----|
| 层 | 22（10 routing + 9 cut + 2 masterslice + 1 overlap） |
| via | 27 template + 19 rule |
| site | 1（0.19×1.4µm） |
| macro | 135（CORE 127 + SPACER 6 + ANTENNACELL 1 + WELLTAP 1） |

### 3.5 DEF（布局结果）

- **流程角色**：die/core 面积、行、单元摆放位置、布线。
- **解析方法**：`load_lef` 后 `datalens.exchange.load_def(file)`，从 `present_module()` 取。
- **能拿到**：die/core bbox、row（site 名/尺寸/数量）、组件摆放状态、端口、网（普通/特殊）。

实测（gcd 布局布线后 DEF）：

| 项目 | 值 |
|------|-----|
| die | 100.13 × 100.80 µm（10093 µm²） |
| core | 80.18 × 79.8 µm（6398 µm²） |
| 行 | 57 |
| 组件 | 231，全 PLACED |
| 端口 | 56 |
| 网 | 307（301 标量 + 6 bus），0 特殊网 |
| 利用率 | 6.2% |

**注意**：DEF 必须**先读 LEF**，否则 `load_def` 段错误；`write_def` 不带 `-routing` 时 DEF 无布线形状。

### 3.6 SPEF（寄生参数）

- **流程角色**：布线后的寄生 RC，post-route STA 和功耗分析输入。
- **解析方法**：`datalens.exchange.load_spef(file)`，需匹配当前 design。
- **能拿到**：dnet 的寄生电容/电阻。

实测（gcd.spef）：55 条 dnet + VDD 电源网（411 节点 / 440 电阻）。top.spef 无匹配 design 时返回 rc=-1。

### 3.7 SAIF（活动性）

- **流程角色**：翻转率/活动性文件，功耗分析输入。
- **解析方法**：`datalens.exchange.load_saif(...)`，需 lib+netlist+`map_from`。
- **能拿到**：信号的翻转率。

实测：`input_A[0]` 翻转率 0.5。

### 3.8 VCD（值变化转储）

- **流程角色**：仿真波形，功耗/活动性分析输入。
- **解析方法**：`datalens.exchange.load_vcd(...)` + `vcd_info()` + `pin.flip_times()`。
- **能拿到**：信号翻转序列。

实测：clk 翻转序列 `(0→0, 15→1, 20→0)`。

---

## 4. 端到端案例：gcd 全流程

用一个完整例子串起整条链路，验证工具链 + dizo 解析：

```
gcd RTL(.v)
  └─ Yosys 综合 ──> gcd_synth.v（231 cell：34 DFF + 197 组合，面积 397.9 µm²）
        └─ OpenROAD 布局布线 ──> demo_out.def（285 网布线成功，0 拥塞，线长 4910 µm，util 6.2%）
              └─ dizo 解析 ──> 网表/DEF/LEF/SDC/Liberty 结构分析（见第 3 节）
```

关键交叉验证：

- **综合后 = 布局后**：cell 数/类型完全一致（231 / 21 种），布局不改变逻辑结构。
- **net 数 358→307**：DEF 只保留参与布线的信号网，悬空/优化掉的 net 不进 DEF。
- **面积**：dizo（datalens）算得 397.94 µm²，与 OpenROAD 报告的利用率 6.2% 一致。

---

## 5. 格式支持速查

| 格式 | datalens 接口 | 支持程度 | 备注 |
|------|--------------|---------|------|
| Verilog | `load_netlist` | ✅ 完整 | 门级可分析，RTL 需先综合 |
| SDC | `constraint_view`（仅文件名） | ⚠️ 需文本解析 | 无约束查询接口 |
| Liberty | `load_lib` + `timinglib` | ✅ 最完整 | 库级单位需文本补充 |
| LEF | `load_lef` | ✅ 完整 | — |
| DEF | `load_def` | ✅ 完整 | 必须先读 LEF |
| SPEF | `load_spef` | ✅ | 需匹配 design |
| SAIF | `load_saif` | ✅ | 需 lib+netlist+map_from |
| VCD | `load_vcd` | ✅ | 需 netlist+inst_name |

---

## 6. 结论

1. **dizo 覆盖了物理设计流程的大部分关键格式**：网表、LEF、DEF、Liberty、SPEF、SAIF、VCD 都有正式的 datalens API，能拿到结构化数据。
2. **SDC 是短板**：约束解析结果未暴露给 Python，只能文本解析。若要完整解析 SDC 约束，需走 dizo 的 TCL 解释器（`db_tclio`）或 C++ 层。
3. **工具链已打通**：yosys（综合）+ OpenROAD（P&R）+ dizo（解析分析）在 Linux 台式机上可完整复现。
4. 以上解析脚本和报告均已归档在 `results/` 目录下，可直接复用。
