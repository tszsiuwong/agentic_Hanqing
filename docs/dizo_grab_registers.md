# GRAB_REGISTER_RESULT —— 成功

> 任务：用 dizo（datalens）**按单元类型**（不依赖时钟网）抓取 `jpeg_sky130hd` 里全部 Register（触发器/锁存器）。
> 脚本：`~/clk_fanout_jpeg/grab_registers.py`
> 输入：`~/agentic_Hanqing/test/jpeg_sky130hd.v`（只读）

---

## 一、Register 识别规则

遍历全设计所有模块的所有叶子实例（`datalens.design.module_iter()` + `module.inst_iter(False)`），
用 `inst.ref_name` 判定时序单元。

sky130 `fd_sc_hd` 库命名约定：时序单元功能名以 `d`(data) 开头，后接 `f`(flip-flop) 或 `l`(latch)：

| 功能名前缀 | 含义 | 示例 |
|-----------|------|------|
| `df*` | D 触发器 | `dfxtp` / `dfrtp` / `dfstp` / `dfxbp` / `dfbbp` |
| `dl*` | D 锁存器 (DLAT) | `dlxtp` / `dlrtp` / `dlytp` |
| `edf*` | 带使能 DFF | `edfxtp` |
| `edl*` | 带使能 DLAT | `edlxtp` |
| `sdf*` | 扫描 DFF | `sdfxtp` / `sdfrtp` / `sdfstp` |
| `sdl*` | 扫描 DLAT | `sdlxtp` |

判定方法（剥离 `sky130_fd_sc_hd__` 前缀与 `_N` 驱动强度后缀后取功能名）：
`re.match(r'^(edf|sdf|sdl|edl|df|dl)', base)`。组合单元名
（`and/or/nand/nor/a2*/o2*/mux/fa/ha/inv/buf/clkbuf/clkinv/conb` 等）均不含 `df`/`dl`，不会误判。

---

## 二、按 ref_name 分布表

| ref_name | 数量 | 类别 | 功能 |
|----------|------|------|------|
| `sky130_fd_sc_hd__edfxtp_1` | 4318 | DFF | 带使能 D 触发器 |
| `sky130_fd_sc_hd__dfrtp_1` | 64 | DFF | 带异步复位 D 触发器 |
| `sky130_fd_sc_hd__dfstp_2` | 2 | DFF | 带置位 D 触发器 |
| **合计** | **4384** | — | — |

- 锁存器 (DLAT) 数量：**0**。
- 全设计唯一 ref_name 共 92 种，其中含 `df`/`dl` 的时序类仅上表 3 种。

---

## 三、总数

| 项目 | 值 |
|------|-----|
| 全设计实例总数 | 33,083 |
| Register 总数（按类型识别） | **4384** |
| 其中 DFF | 4384 |
| 其中 DLAT（锁存器） | 0 |

---

## 四、与 clk all_fanout(4384) 的对比

| 来源 | 数量 | 分布 |
|------|------|------|
| `clk.all_fanout(only_cell=True)` | 4384 | edfxtp_1=4318, dfrtp_1=64, dfstp_2=2 |
| **按类型识别（本次）** | **4384** | edfxtp_1=4318, dfrtp_1=64, dfstp_2=2 |

- 挂在 clk 但类型规则未识别：**0 个**。
- 类型规则识别到但不在 clk 网：**0 个**。
- 二者集合完全一致（`set` 差集均为空）。

**结论：不存在「未挂在 clk 网上的寄存器」。** 该设计为单时钟域（`clk`），
所有 4384 个时序单元均为 DFF，且全部由 `clk` 直接驱动；无锁存器、无额外多时钟/异步复位产生的独立时序单元。

---

## 五、代表性实例清单

`dfrtp_1`（带异步复位，pins = CLK/D/Q/RESET_B，共 64 个）：

```
fdct_zigzag.dct_mod.ddgo$_DFFE_PN0P_
fdct_zigzag.dct_mod.ddin[0]$_DFFE_PN0P_
fdct_zigzag.dct_mod.ddin[1]$_DFFE_PN0P_
fdct_zigzag.dct_mod.ddin[2]$_DFFE_PN0P_
fdct_zigzag.dct_mod.ddin[3]$_DFFE_PN0P_
```

`dfstp_2`（带置位，pins = CLK/D/Q/SET_B，共 2 个）：

```
fdct_zigzag.dct_mod.ddcnt$_DFFE_PN1P_
fdct_zigzag.dct_mod.dddcnt$_DFFE_PN1P_
```

`edfxtp_1`（带使能，pins = CLK/D/DE/Q，共 4318 个）：

```
dfdct_dout[0]$_DFFE_PP_
dfdct_dout[10]$_DFFE_PP_
dfdct_dout[11]$_DFFE_PP_
dfdct_dout[1]$_DFFE_PP_
dfdct_dout[2]$_DFFE_PP_
```

---

## 六、结论

1. **成功**：按 ref_name 类型规则识别出全部 **4384** 个 Register，均为 DFF，无锁存器。
2. 与 `clk` 端口 `all_fanout` 抓到的 4384 个 DFF **完全一致**（0 差异），双向交叉验证通过。
3. 设计为单时钟域扁平网表，`clk` 直连全部 DFF；不存在未挂 `clk` 的寄存器或额外时序单元。
4. 复位/置位端口差异仅体现在 `dfrtp_1`(RESET_B) 与 `dfstp_2`(SET_B) 上，不影响总数。

---

*报告生成时间：2026-08-28；全程只读输入，未改动 `~/dizo`、`~/OpenROAD/build`，未 commit/push。*


---

## 具体命令 / 复现步骤

### 01 一键复现（整流程）
```bash
# 配置 datalens 环境（必须先 source）
cd ~/agentic_Hanqing
source datalens_env.sh

# 抓 clk 端口 all_fanout -> 全部时钟 sink 点
python3.11 results/clk_fanout_jpeg/clk_fanout_jpeg.py

# 按单元类型抓全部 Register（DFF/锁存器），与 clk 抓取交叉验证
python3.11 results/clk_fanout_jpeg/grab_registers.py
```
> 注：分析时脚本实际位于 `~/clk_fanout_jpeg/`（开发目录）；仓库内归档于 `results/clk_fanout_jpeg/`。输入网表 `jpeg_sky130hd.v` 已 hardcode 在脚本内。

### 02 datalens 内联核心命令（交互式 / 手写脚本）

**A. 环境 + 加载网表**
```python
cd ~/agentic_Hanqing && source datalens_env.sh && python3.11
# >>> import datalens
# >>> netlist = "/home/zixiao/agentic_Hanqing/test/jpeg_sky130hd.v"
# >>> datalens.exchange.load_netlist([netlist])
# >>> top = datalens.design.present_project().present_module()
```

**B. 从 clk 端口 all_fanout 抓 sink**
```python
# 注意：get_ports 返回 list，不是 get_port
clk_port = top.get_ports("clk")[0]

all_objs = clk_port.all_fanout()                       # 全部扇出对象(port/pin/inst/net)
end_pins = clk_port.all_fanout(only_end=True)          # 时序端点(叶子 sink, 即 DFF 的 CLK pin)
cells    = clk_port.all_fanout(only_cell=True)         # sink 单元(DFF instance)
flattened = clk_port.all_fanout(is_flatten_view=True, only_end=True)

# 对象取值注意：name/inst/ref_name 是属性, pin 用 .inst 拿所属实例;
#              pin.name / inst.ref_name / net.name 是属性；port.net() 是方法
for pin in end_pins:
    print(pin.name, pin.inst.name, pin.inst.ref_name)  # CLK <inst> <ref>
```
> 参数：`is_flatten_view`(展平层级)、`should_has_time_arc`(只看时序弧,默认True)、
> `only_end`(只端点)、`only_cell`(只单元)、`level`(最大深度,默认UINT32_MAX)。
> 全量结果含起始 port 自身(计数时要剥掉)。

**C. 按单元类型抓全部 Register（不依赖时钟网）**
```python
import re
from collections import Counter
pat = re.compile(r'^(edf|sdf|sdl|edl|df|dl)')   # sky130 fd_sc_hd 时序功能名前缀
regs = []
for m in datalens.design.module_iter():
    for inst in m.inst_iter(False):
        base = inst.ref_name.replace("sky130_fd_sc_hd__", "").rsplit("_", 1)[0]
        if pat.match(base):
            regs.append(inst)
print(len(regs))                                    # -> 4384
print(Counter(i.ref_name for i in regs))            # edfxtp_1 4318 / dfrtp_1 64 / dfstp_2 2
```
> 判定：功能名去掉库前缀 + 驱动强度后缀后，匹配 `df*`(DFF) / `dl*`(DLAT) / `edf*`(使能DFF) /
> `sdf*`(扫描DFF) 等；`and/or/mux/inv/clkbuf...` 组合单元不含 `df`/`dl`，不会误判。
