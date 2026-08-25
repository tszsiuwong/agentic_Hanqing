# 更多格式解析结果（datalens / dizo）

环境：`cd ~/agentic_Hanqing && source datalens_env.sh && python3.11`
脚本位置：`~/more_parse/`（sdc_parse.py / lib_parse.py / spef_parse.py / saif_parse.py / vcd_parse.py）

结论速览：

| 格式 | datalens API | 能否拿到有意义数据 | 备注 |
|------|--------------|--------------------|------|
| SDC  | `design.constraint_view` | **否**（仅暴露文件名） | 用文本/正则解析 |
| Liberty | `exchange.load_lib` + `timinglib` | **是** | 最完整 |
| SPEF | `exchange.load_spef` + `parasitic` | **是**（需匹配 design） | gcd.spef 是 reduced 抽取 |
| SAIF | `exchange.load_saif` | **是**（需 lib+netlist+map_from） | 翻转率 |
| VCD  | `exchange.load_vcd` | **是**（需 netlist+inst_name） | flip_times |

---

## 1. SDC（重点）

### 1.1 ConstraintView API 结论：未暴露约束查询

`datalens.design.constraint_view` 暴露的方法只有：

```
create, destroy, is_active, is_hold, is_setup, name, sdc_files, set_sdc_files
```

即只能 get/set **SDC 文件名**，没有任何 `create_clock` / `set_input_delay` / `set_false_path`
等约束对象的查询接口。此外：

- `constraint_view.create()` 需要 MCMM 处于初始化状态（需先 `load_project`/`init_mcmm_mode`
  且有设计上下文），否则抛 `RuntimeError: MCMM objects can't be created or destroyed when MCMM is
  not initializing`，更糟时直接 **SIGSEGV**（`Project::GetMCMMMgr` 空指针）。
- `delay_view` / `timing_path` 是 STA 结果对象，也没有"列出所有时钟/约束"的入口。

→ **结论：datalens 目前没有把 SDC 约束解析结果暴露给 Python，只能文本解析。**

### 1.2 文本解析结果

解析器 `sdc_parse.py` 提取 create_clock / create_generated_clock / set_input_delay /
set_output_delay / set_false_path / set_load / set_driving_cell / set_input_transition /
set_clock_uncertainty / set_max_transition 等。

| 文件 | create_clock | 其它 |
|------|--------------|------|
| `gcd_nangate45.sdc` | `core_clock` period=0.485ns，端口 `clk` | `set_all_input_output_delays` 1 条 |
| `aes_asap7.sdc` | `core_clock` period=400ps，端口 `clk` | `set_all_input_output_delays` 1 条 |
| `timing_api_2.sdc` | `core_clock` period=0.46ns，端口 `clk` | set_input_delay ×35 (值 0.092)，set_output_delay ×18 (0.092)，set_propagated_clock ×1 |

示例（timing_api_2.sdc）：
- 时钟 `core_clock`，period 0.46ns
- 35 条 `set_input_delay 0.092 -clock core_clock -add_delay`（req_msg[0..31]、req_val、reset、resp_rdy）
- 18 条 `set_output_delay 0.092 -clock core_clock -add_delay`（req_rdy、resp_msg[0..15]、resp_val）

注意：本机 `~/OpenROAD/test/*.sdc` 大多只有 `create_clock` + `set_all_input_output_delays`（OpenROAD
flow 模板），没有 `set_false_path` / `set_driving_cell` / `set_load` / `create_generated_clock` 的真实例子；
这几条命令的分支已用合成样例验证过解析正确性。

---

## 2. Liberty（重点）

`load_lib` + `datalens.timinglib` 解析很完整。类：`lib_library` / `lib_cell` / `lib_pin` /
`lib_timing` / `lib_table`，通用属性走 `get_property(name)` / `list_properties()`。

### 2.1 库级

| 项 | Nangate45_fast | sky130_fd_sc_hd__tt_025C_1v80 |
|----|----------------|-------------------------------|
| lib name | `NangateOpenCellLibrary_fast` | `sky130_fd_sc_hd__tt_025C_1v80` |
| 时间单位 | 1ns | 1ns |
| 电压单位 | 1V | 1V |
| 电容单位 | 1ff | 1pf |
| 标称工艺/电压/温度 | 1.00 / 1.25 / 0.00 | 1.0 / 1.8 / 25.0 |

> 注意：库级 `list_properties()` 只返回 `source_file_name/full_name/name/object_class/
> default_threshold_voltage_group` 5 项，**时间/电容单位 API 未暴露**，以上单位来自 .lib 头部
> 文本补充解析（`time_unit : "1ns"` 等）。

### 2.2 单元统计

| 项 | Nangate45 | sky130hd |
|----|-----------|----------|
| cell 总数 | 134 | 428 |
| 时序单元（is_sequential） | 29 | 69 |
| 组合单元（is_combinational） | 98 | 347 |
| 其它/黑盒 | 7 | 12 |
| 时钟门控单元 | 8 | 6 |
| 含 clock pin 的 cell | 29 | 69 |
| 总引脚数 | 549 | 1777 |
| 总面积 | 416.556 | 6880.335 |
| timing arc 总数 | 1494（分布在 125 cell） | 1854（分布在 414 cell） |

### 2.3 引脚 direction 分布

- Nangate45：`in` 388 / `out` 145 / `internal` 16
- sky130hd：`in` 1311 / `out` 454 / `internal` 12

### 2.4 其它统计（Nangate45）

- timing arc 最多：`SDFFRS_X1/X2`（111）、`AOI222_*`（54）、`OAI222_*`（54）
- 面积最大：`BUF_X32`（13.03）、`INV_X32`（8.78）、`FILLCELL_X32`（8.51）
- 引脚最多：`SDFFRS_X1/X2`（8 pin）

### 2.5 timinglib API 心得

- 时序 arc：`lib_pin.timing_iter()` → `lib_timing`，`lib_timing.related_pin_iter()` 拿 related pin；
  `lib_timing.pin()` 是方法（不是属性，需加 `()`）。
- 属性判断：`is_sequential`/`is_combinational`/`is_clock_gating_cell`（cell 级），
  `is_clock_pin`/`direction`/`capacitance`/`signal_type`（pin 级）。
- `lib_timing` 暴露面较窄（只有 `get_ocv_sigma_table`/`pin`/`related_pin_iter`），
  delay/slew 具体查找表值（lib_table 的 value_iter）没能从 `lib_timing` 直接挂到，
  更细的 delay/transition 表需走 `lib_table.index_iter()` / `value_iter()`。
- `datalens.timinglib.current_lib()` 返回当前合并库；`libcell_iter()`/`libpin_iter()`
  是迭代器，需 `list()` 化或 for 循环。

---

## 3. SPEF（顺带）

### 3.1 gcd.spef（有匹配 lef+def，API 完整）

`load_lef(Nangate45.lef)` + `load_def(gcd.def)` + `load_spef([gcd.spef])` → `top.parasitic()`。

- 单位/scale：time NS(1.0)、cap FF(1.0)、res OHM(1.0)、induct H(1.0)
- dnet 数量：**55**；总节点 411；总电阻 5.571Ω；总耦合电容 0
- 但本 gcd.spef 是 StarRC **reduced/降规模抽取**：54 个信号网 `*D_NET` 的 total_cap 全是 0，
  只有 `VDD` 电源网有完整 RC：
  - VDD：411 节点、440 电阻、电阻和 5.571Ω（min 1e-6 ~ max 0.0451）、对地电容合计 ~1.08 fF
- 所以"总电容"几乎为 0 是文件本身如此，不是解析错误（`top.spef` 里 total_cap 能读到 2.2）。

### 3.2 top.spef（无匹配 design）

`load_spef(['top.spef'])` 直接返回 **rc=-1**：
`Design 'TopCell' in SPEF file is not found in DB`（该文件没有配套 netlist/def，SPEF 必须映射到
已加载的 design）。于是改文本解析：
- 头部单位：T_UNIT 1.2ns / C_UNIT 2.3pF / R_UNIT 3.4Ω / L_UNIT 1H
- 3 个 D_NET，各自 total cap 2.2；节点电容 6 条（9.9）；电阻 5 条

> 任务里写的 `~/dizo/tests/ut/dm/design/data/gcd.spef` 实际不存在，真身在
> `~/dizo/tests/ut/dm/design/data/gcd/gcd.spef`（配套 gcd.def + Nangate45.lef）。

---

## 4. SAIF（顺带）

`test.saif`（`~/dizo/tests/ut/exchange/saif/data/case1/`）：

- 文本头：SAIFVERSION 2.0、DIRECTION backward、DESIGN `top_module`、TIMESCALE 1ps、
  DURATION 100000.00、VENDOR "Huawei, Inc"、Program "Power Compiler write_saif"
- T0/T1/TC：`input_A[0]` → T0=50000 T1=50000 TC=50
- API：需先 `load_lib(test.lib)` + `load_netlist(test.v)`，再
  `load_saif(saif, set_tr_sp=True, map_from="top_module", map_to="")`，否则 rc=-1。
- 结果：`port input_A[0].io_pin().toggle_rate()` = **0.5**（TC 50 / 100000ps = 0.5 次/ns），
  其余端口为 FLT_MAX（3.4e38，未标注）。
- 顺带验证 case2 `constnet_trsp.saif` 含更丰富的 NET 级 T0/T1/TX/TC/TG/IG 字段。

---

## 5. VCD（顺带）

`alu_rtl.vcd`（`~/dizo/tests/ut/interpreter/command/data/vcd/`）：

- `load_netlist(vcd_gate.v)` + `load_vcd(alu_rtl.vcd, inst_name="tb/alu_tb", name_map="vcd_name_map.map")`
- `project.vcd_info()`：time_scale=10、time_unit=TIME_NS、start=0、end=20
- 翻转：时钟 `clk` 3 次翻转 `(0,BIT0)→(15,BIT1)→(20,BIT0)`；`Out[0]` `(0,0)→(5,1)→(20,0)`；
  实例 `reg_test_1_0/Q` 4 次翻转
- 统计：有翻转引脚 261 个，总翻转 266 次
- `time_range=[5,15]` 变体也可用（读 alu_time_range.vcd）

---

## 6. 遇到的问题 & 心得

1. **ConstraintView 会崩**：`constraint_view.create()` 在 MCMM 未初始化时先抛 RuntimeError，
   再直接触发 SIGSEGV（backtrace 指向 `Project::GetMCMMMgr`）。所以脚本里只做静态自省（dir+docstring），
   **不要真正实例化**。SDC 用正则文本解析最稳。
2. **SAIF 必须带 `set_tr_sp=True` + `map_from`**：默认参数读不进去（rc=-1）。map_from 要填
   网表顶层模块名（如 `top_module`）。
3. **SPEF 必须映射到已加载 design**：`load_spef([...])` 需要先 load_def/load_netlist，
   否则 `Design 'xxx' is not found in DB` 返回 -1。`top.spef` 没有配套网表，只能文本解析。
4. **VCD 需要 inst_name 对齐层级**：`inst_name="tb/alu_tb"`（testbench 层级路径），否则 flip_times 对不上。
5. **Lib 单位 API 不暴露**：时间/电容单位不在 `lib_library.list_properties()` 里，需读 .lib 头部文本补充。
6. **迭代器 vs 属性**：`libcell_iter()` 等返回迭代器；`lib_timing.pin()` 是方法要加括号，
   `lib_pin.direction` 是 `get_property("direction")`。返回"未标注"数值是 FLT_MAX(3.4e38)。
7. **复用已有正则**：`~/agentic_Hanqing/analysis/clock_analysis.py` 里的 SDC 正则（create_clock /
   generated_clock 的 port/name/period/source/divide_by）可直接借鉴，本脚本在它基础上扩展了
   IO delay / false_path / load / driving_cell / uncertainty 等。

---

## 7. 脚本使用

```bash
cd ~/agentic_Hanqing && source datalens_env.sh

python3.11 ~/more_parse/sdc_parse.py  ~/OpenROAD/test/gcd_nangate45.sdc \
        ~/OpenROAD/test/aes_asap7.sdc ~/OpenROAD/test/timing_api_2.sdc

python3.11 ~/more_parse/lib_parse.py  ~/OpenROAD/test/Nangate45/Nangate45_fast.lib \
        ~/OpenROAD/test/sky130hd/sky130_fd_sc_hd__tt_025C_1v80.lib

python3.11 ~/more_parse/spef_parse.py
python3.11 ~/more_parse/saif_parse.py
python3.11 ~/more_parse/vcd_parse.py
```

全程只读输入文件，未改动 `~/dizo` 与 `~/OpenROAD/build`。
