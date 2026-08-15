# 需求：Dizo Python API 暴露 LibPin 时钟/方向属性

- **需求方**：EDA 工具链团队（agentic_Hanqing 分析工具）
- **模块**：`modules/py`（datalens Python 绑定）
- **涉及文件**：`modules/py/src/dm/timing_lib/py_libpin.cc`（当前仅暴露 `name` / `timing_iter` / `capacitance`）
- **状态**：待评审

---

## 1. 背景与动机

当前时钟结构分析工具（`clock_analysis.py`）需要识别时序单元的时钟引脚、复位引脚、时钟门控引脚等。C++ 层 `LibPin` 类已完整实现这些属性（见 `include/dm/timinglib/lib_pin.h`），但 Python 绑定只暴露了 `name` / `timing_iter` / `capacitance` 三个接口，导致 Python 侧无法精确读取，只能靠引脚命名启发式（`CK` / `G` / `RN` 等）猜测。

启发式的局限：
1. 工艺库命名不规范时识别失效（如 `PCLK`、`PHI1` 等非常规时钟引脚名）
2. 无法区分时钟门控单元的使能引脚与数据引脚
3. 无法识别 isolation / level-shifter 等低功耗单元的特殊引脚

## 2. 目标

在 datalens Python 绑定中暴露 `LibPin` 的时钟/方向属性，使 Python 侧能**精确**识别引脚语义，替代启发式猜测。

## 3. 需求详情

### 3.1 优先级 P0 —— 时钟结构分析必需

| Python 方法 | C++ 方法 | 返回类型 | 语义 |
|------------|----------|---------|------|
| `is_clock` | `IsClock()` | `Optional[bool]` | 是否为时钟引脚 |
| `direction` | `GetDirectionType()` | `Optional[DirectionType]` | 引脚方向（INPUT/OUTPUT/INOUT） |

### 3.2 优先级 P1 —— 时钟门控分析

| Python 方法 | C++ 方法 | 返回类型 | 语义 |
|------------|----------|---------|------|
| `is_clock_gate_clock_pin` | `IsClockGateClockPin()` | `Optional[bool]` | 时钟门控单元的时钟输入引脚 |
| `is_clock_gate_enable_pin` | `IsClockGateEnablePin()` | `Optional[bool]` | 时钟门控单元的使能引脚 |
| `is_clock_gate_out_pin` | `IsClockGateOutPin()` | `Optional[bool]` | 时钟门控单元的门控时钟输出引脚 |
| `is_clock_gate_obs_pin` | `IsClockGateObsPin()` | `Optional[bool]` | 可观测性引脚 |
| `is_clock_gate_test_pin` | `IsClockGateTestPin()` | `Optional[bool]` | 测试引脚 |

### 3.3 优先级 P2 —— 低功耗/隔离单元

| Python 方法 | C++ 方法 | 返回类型 | 语义 |
|------------|----------|---------|------|
| `is_isolation_cell_enable_pin` | `IsIsolationCellEnablePin()` | `Optional[bool]` | 隔离单元使能引脚 |
| `is_isolation_cell_data_pin` | `IsIsolationCellDataPin()` | `Optional[bool]` | 隔离单元数据引脚 |
| `is_clock_isolation_cell_clock_pin` | `IsClockIsolationCellClockPin()` | `Optional[bool]` | 时钟隔离单元时钟引脚 |
| `pulse_clock` | `GetPulseClock()` | `Optional[PulseClockType]` | 脉冲时钟类型 |

## 4. 转换规则

`LibOptional<T>` → Python `Optional[T]`：

| LibOptional 状态 | Python 值 |
|-----------------|-----------|
| 未赋值（属性缺失） | `None` |
| 已赋值 | 对应 Python 值（bool / 枚举） |

`DirectionType` 枚举需同步暴露到 `datalens.timinglib`（或 `datalens.liberty`），命名与现有 `SignalDirection` 风格一致（建议 `INPUT` / `OUTPUT` / `INOUT`）。

## 5. 验收标准

1. 加载 Nangate45 Liberty 文件后，以下断言成立：
   - `lib_cell.pin("CK").is_clock == True`（DFF_X1 的时钟引脚）
   - `lib_cell.pin("D").is_clock == False`
   - `lib_cell.pin("CK").direction == INPUT`
2. 对含 clock gating 属性的 Liberty 单元，`is_clock_gate_*` 系列返回正确布尔值；无该属性的引脚返回 `None`（不抛异常）。
3. 未加载 Liberty 或属性未标注时，返回 `None`，不影响其他接口。

## 6. 使用示例（验收脚本伪码）

```python
import datalens
datalens.exchange.load_lib(["Nangate45_typ.lib"])
lib = datalens.timinglib.current_lib()
cell = lib.cell("DFF_X1")

for lp in cell.libpin_iter():
    if lp.is_clock:            # 精确识别时钟引脚
        print(f"{lp.name} is clock pin")
    if lp.direction == datalens.timinglib.DirectionType.INPUT:
        print(f"{lp.name} is input")
```

## 7. 备注

- 本次改动仅涉及 Python 绑定（`.cc` pybind11 注册），**不修改 C++ `LibPin` 类本身**。
- 需同步更新 `modules/py/docs/` 中 lib_pin 的 API 文档。
- 需补充 Python 单元测试（参考 `modules/py/tests/ut/` 现有 timinglib 测试用例）。
