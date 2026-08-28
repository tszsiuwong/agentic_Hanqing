# CLK_FANOUT_JPEG_RESULT —— 成功

> 任务：用 dizo（datalens）对 `jpeg_sky130hd` 的 `clk` 端口执行 `all_fanout`，抓取全部时钟 sink 点并统计时钟树结构。
> 脚本：`~/clk_fanout_jpeg/clk_fanout_jpeg.py`
> 输入：`~/agentic_Hanqing/test/jpeg_sky130hd.v`（只读）

---

## 一、设计信息

| 项目 | 值 |
|------|-----|
| 设计 | jpeg（JPEG 编码器） |
| Top module | `jpeg_encoder` |
| 网表文件 | `jpeg_sky130hd.v`（Verilog 门级网表） |
| 全设计实例总数 | 33,083 |
| 时钟端口 | `clk`（单时钟域，输入端口） |
| 时钟端口 net | `clk`（port 与 net 同名，加载时 read_verilog 已删除同名内部 net，port/net 合流） |

---

## 二、`clk` 端口 `all_fanout` 对象分类统计

调用 `clk_port.all_fanout()`（默认参数：`is_flatten_view=False, should_has_time_arc=True, only_end=False, only_cell=False, level=UINT32_MAX`）：

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| `port` | 1 | clk 端口自身（起始点） |
| `pin` | 4384 | 全部时钟 sink 引脚，**引脚名全部为 `CLK`** |
| `net` | 0 | 无中间 net 对象（时钟网为单级扇出，无缓冲分支） |
| **合计** | **4385** | |

- 4384 个 pin 分属 4384 个**互不相同的** DFF 实例（`len(set(pin.inst.name)) == 4384`）。
- 返回对象里没有 `instance`、也没有中间 `net`，说明时钟树是**完全扁平**的：`clk` 网直连所有 DFF 的 `CLK` 引脚。

---

## 三、`only_cell` 按 ref_name 分布（时钟树组成）

`clk_port.all_fanout(only_cell=True)` → **4384 个 instance**，全部是 DFF：

| ref_name | 数量 | 单元类型 |
|----------|------|----------|
| `sky130_fd_sc_hd__edfxtp_1` | 4318 | 带使能的 D 触发器（enable DFF） |
| `sky130_fd_sc_hd__dfrtp_1` | 64 | 带异步复位的 D 触发器 |
| `sky130_fd_sc_hd__dfstp_2` | 2 | 带置位的 D 触发器 |
| **合计** | **4384** | |

> **关键发现**：`only_cell` 结果中**没有任何 CLKBUF / CLKINV**。即时钟树中不存在缓冲级，`clk` 端口直接扇出到全部 4384 个寄存器。

---

## 四、`only_end` 时序端点（叶子 DFF）+ 展平

| 调用方式 | 返回类型 | 数量 |
|----------|----------|------|
| `all_fanout(only_end=True)` | pin | **4384** |
| `all_fanout(is_flatten_view=True, only_end=True)` | pin | **4384** |
| `all_fanout(is_flatten_view=True, only_cell=True)` | instance | **4384** |

- `only_end` 与 `is_flatten_view=True` 的结果完全一致，因为该网表本身就是**扁平网表**（无层级块），展平视图无差异。
- 端点 ref_name 分布与 `only_cell` 完全一致（`edfxtp_1` 4318 / `dfrtp_1` 64 / `dfstp_2` 2）。

---

## 五、参数矩阵对照

所有参数组合结果一致，佐证时钟网为单级直连、无时序弧/层级/深度影响：

| 参数组合 | 总数 | 类型分布 |
|----------|------|----------|
| 默认 | 4385 | port=1, pin=4384 |
| `should_has_time_arc=False` | 4385 | port=1, pin=4384 |
| `is_flatten_view=True` | 4385 | port=1, pin=4384 |
| `only_cell=True` | 4384 | instance=4384 |
| `only_end=True` | 4384 | pin=4384 |
| `only_end=True, only_cell=True` | 4384 | instance=4384 |
| `level=1` / `level=2` / `level=3` | 4385 | port=1, pin=4384 |

> `level=1` 即已遍历到全部 4384 个 DFF，说明时钟网深度仅为 1 层（端口 → DFF），无中间缓冲跳数。

---

## 六、时钟树层级 / 缓冲器说明（874 CLKBUF 的作用）

设计中共有 **874** 个时钟类缓冲/反相单元：

| ref_name | 数量 |
|----------|------|
| `sky130_fd_sc_hd__clkbuf_1` | 842 |
| `sky130_fd_sc_hd__clkbuf_2` | 30 |
| `sky130_fd_sc_hd__clkinv_1` | 2 |

**核查结论：这 874 个 CLKBUF/CLKINV 不在时钟路径上。**

- `clk` 网直接连接 4385 个 pin（1 port + 4384 DFF 的 `CLK`），网表上没有任何 buffer 单元串接在 `clk` 网与 DFF 之间。
- 核查 874 个 buffer 的输入引脚所接网：`clk` 网出现在 CLKBUF 输入的次数为 **0**。
- 这些 CLKBUF/CLKINV 实际作为**数据/复位/高扇出信号的通用缓冲器**使用，其输入网多为综合器生成的内部网（如 `_06831_`、`_08197_`、`_08208_`…，且常以每组 10 个 buffer 共享同一驱动网的形式出现）。

**因此 `jpeg_sky130hd.v` 是综合（synthesis）阶段、尚未做时钟树综合（pre-CTS）的扁平门级网表**：`clk` 是一条无缓冲、扇出 4384 的单一网；并不存在「带缓冲层的真实时钟树」，874 个 CLKBUF 与时钟树无关（它们名字里的 "clk" 只是标准单元库命名，不代表承担时钟树角色）。

---

## 七、交叉验证结论

| 校验项 | 结果 |
|--------|------|
| `only_end` 叶子 DFF 数 | 4384 ✅ |
| `only_cell` 单元 DFF 数 | 4384 ✅ |
| 预期 DFF 总数（背景） | 4384 ✅ |
| 全设计实例总数 | 33083 ✅ |
| 时钟缓冲层（CLKBUF 在 clk 路径上） | 无（0 个）——与「874 CLKBUF」预期**不一致** |

**结论**：`clk` 端口 `all_fanout` 成功抓出全部 **4384** 个时钟 sink 点（即 4384 个 DFF 的 `CLK` 引脚），与预先分析的 4384 个 DFF 完全吻合，交叉验证通过。设计为单时钟域、扁平、无缓冲时钟树。

---

## 八、遇到的坑

1. **属性 vs 方法不一致（最易踩坑）**：
   - `port.name` / `net.name` / `pin.name` / `inst.name` / `inst.ref_name` 是**属性**（直接取值）。
   - `port.net` 是**方法**（必须 `port.net()`）；`inst.pin_iter()` / `inst.is_hier()` / `net.pin_iter()` 是**方法**。
   - 任务提示里的 `pin.inst()`、`pin.name()`、`net.name()` 会报错（`'str' object is not callable` / `'builtin_function_or_method' object has no attribute ...`），实际应写 `pin.inst`、`pin.name`、`net.name`。
2. **`get_port` 不存在**：top module 用 `get_ports('clk')`（返回 list），不是 `get_port`。
3. **load_verilog 的 WARNING**：port 与 net 同名（`clk` 等）时 read_verilog 会删除同名内部 net，port 与 net 合流，属正常现象，不影响结果。
4. **`all_fanout` 返回对象含起始 port 自身**：全量结果 4385 = 1（port）+ 4384（pin），计数时需把 port 单独剥离，别当成 sink 点。
5. **预期偏差**：背景假设「有真实时钟树 + 874 CLKBUF 参与缓冲」，但实际网表为 pre-CTS 扁平网表，clk 直连 DFF；CLKBUF 只是数据路径通用缓冲器。以实测 `net.pin_iter()` 为准做交叉验证，避免照搬假设。

---

*报告生成时间：2026-08-28；全程只读输入，未改动 `~/dizo`、`~/OpenROAD/build`，未 commit/push。*


---

## 具体命令 / 复现步骤

### 01 一键复现
```bash
cd ~/agentic_Hanqing
source datalens_env.sh
python3.11 results/clk_fanout_jpeg/clk_fanout_jpeg.py
```
> 分析时脚本位于 `~/clk_fanout_jpeg/`；仓库内归档于 `results/clk_fanout_jpeg/`。

### 02 datalens 内联核心命令
```python
cd ~/agentic_Hanqing && source datalens_env.sh && python3.11
# >>> import datalens
# >>> netlist = "/home/zixiao/agentic_Hanqing/test/jpeg_sky130hd.v"
# >>> datalens.exchange.load_netlist([netlist])
# >>> top = datalens.design.present_project().present_module()

# 注意：get_ports 返回 list
clk_port = top.get_ports("clk")[0]
all_objs  = clk_port.all_fanout()                       # port=1 + pin=4384
end_pins  = clk_port.all_fanout(only_end=True)          # 4384 叶 DFF
cells     = clk_port.all_fanout(only_cell=True)         # 4384 DFF instance
flat_ends = clk_port.all_fanout(is_flatten_view=True, only_end=True)

# 属性 vs 方法：pin.name / pin.inst / inst.ref_name / net.name 是属性; port.net() 是方法
# all_fanout 全量结果含起始 port 自身(4385 = 1 port + 4384 pin)，计数时要剥掉
```
> 参数：`is_flatten_view` / `should_has_time_arc`(默认True) / `only_end` / `only_cell` / `level`(默认UINT32_MAX)。
