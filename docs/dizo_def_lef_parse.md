# DEF/LEF 解析结果（datalens / dizo）

运行环境：`cd ~/agentic_Hanqing && source datalens_env.sh && python3.11`。
脚本与 CSV 输出在 `~/def_lef_parse/`：

- `parse_lef.py` → `lef_summary.csv` / `lef_layers.csv` / `lef_vias.csv` / `lef_sites.csv` / `lef_macros.csv`
- `parse_def.py` → `def_summary.csv` / `def_rows.csv` / `def_components.csv` / `def_ports.csv` / `def_nets.csv`

输入：
- LEF：`~/OpenROAD/test/Nangate45/Nangate45.lef`
- DEF：`~/or_synth_demo/demo_out.def`（gcd 全局布线后的 `write_def`，未加 `-routing`）

---

## 1. LEF 解析结果（Nangate45.lef）

### 1.1 层（layer）—— 共 22 层

| 类型 | 数量 | 层名 |
|------|------|------|
| ROUTING | 10 | metal1 … metal10 |
| CUT | 9 | via1 … via9 |
| MASTERSLICE | 2 | poly, active |
| OVERLAP | 1 | OVERLAP |

金属层线宽 / 间距（datalens 可读 `width()` / `pitch()`）：

| 层 | 线宽 (dbu / µm) | pitch (dbu / µm) | 方向 |
|----|-----------------|------------------|------|
| metal1 | 140 / 0.070 | 280 / 0.140 | HORIZONTAL |
| metal2 | 140 / 0.070 | 380 / 0.190 | VERTICAL |
| metal3 | 140 / 0.070 | 280 / 0.140 | HORIZONTAL |
| metal4–6 | 280 / 0.140 | 560 / 0.280 | V/H 交替 |
| metal7–8 | 800 / 0.400 | 1600 / 0.800 | V/H 交替 |
| metal9–10 | 1600 / 0.800 | 3200 / 1.600 | V/H 交替 |

> 单位：`tech.unit().micron_per_dbu() == 0.0005`（DBU=2000）。

### 1.2 过孔（via template）—— 27 个

全部 `DEFAULT`（`is_default()==True`，`is_generated()==False`）：

| 组 | 数量 | 名称 |
|----|------|------|
| via1_* | 9 | via1_0 … via1_8（metal1→metal2）|
| via2_* | 9 | via2_0 … via2_8（metal2→metal3）|
| via3_* | 3 | via3_0 … via3_2（metal3→metal4）|
| via4_0 … via9_0 | 6 | 各 1 个（metal4→metal5 … metal9→metal10）|

### 1.3 via rule —— 19 个

`Via1Array-0..4`、`Via2Array-0..4`、`Via3Array-0..2`、`Via4Array-0`、`Via5Array-0`、`Via6Array-0`、`Via7Array-0`、`Via8Array-0`、`Via9Array-0`。

### 1.4 site —— 1 个

| 名称 | class | 宽 (dbu / µm) | 高 (dbu / µm) | 对称性 |
|------|-------|---------------|---------------|--------|
| FreePDK45_38x28_10R_NP_162NW_34O | CORE | 380 / 0.190 | 2800 / 1.400 | Y |

### 1.5 宏单元（macro）—— 135 个

| 项 | 值 |
|----|----|
| 总数 | 135 |
| major_class | CORE × 135 |
| class 分布 | CORE ×127、CORE_SPACER ×6、CORE_ANTENNACELL ×1、CORE_WELLTAP ×1 |
| 引脚数 | min=2, max=10, avg=5.95 |

按面积 Top 5：

| 宏 | 面积 (µm²) | 尺寸 (dbu) | 引脚数 |
|----|-----------|------------|--------|
| BUF_X32 | 13.034 | 18620×2800 | 4 |
| INV_X32 | 8.778 | 12540×2800 | 4 |
| FILLCELL_X32 | 8.512 | 12160×2800 | 2 |
| SDFFRS_X2 | 8.246 | 11780×2800 | 10 |
| CLKGATETST_X8 | 7.714 | 11020×2800 | 6 |

> 说明：加载 `Nangate45_lvt.lef` 后宏总数会翻倍为 270（135 主库 + 135 lvt）。

---

## 2. DEF 解析结果（demo_out.def, 顶层模块 gcd）

### 2.1 die / core area

| 项 | bbox (dbu) | 尺寸 (µm) | 面积 (µm²) |
|----|-----------|-----------|-----------|
| DIEAREA (`module.bbox()`) | (0,0)–(200260,201600) | 100.130 × 100.800 | 10093.104 |
| core（由行 row 围出） | (20140,22400)–(180500,182000) | 80.180 × 79.800 | ~6398 |

### 2.2 行（row）—— 57 行

- 名称：`ROW_0` … `ROW_56`
- site：FreePDK45_38x28_10R_NP_162NW_34O（380×2800 dbu）
- 方向：N ×29 / FS ×28（水平，`is_horizontal()==True`）
- 每行 `x_count()=422`，`x_step()=380`，`y_count()=1`

### 2.3 组件（component）—— 231 个

| 状态 | 数量 |
|------|------|
| PLACED | 231 |
| FIXED | 0 |
| UNPLACED | 0 |
| COVER / SOFT_FIXED | 0 |

- 已摆放组件包围盒：(61180,22400)–(134900,70000) dbu = 36.860 × 23.800 µm
- 引用 cell 种类：21 种
- 单元总面积 ≈ 398 µm²（与 OpenROAD 日志 `Design area 398 um^2` 一致）
- 利用率 ≈ 398 / 6398 ≈ 6.2%（相对 core，与日志 6% 一致）

### 2.4 端口（port）

- `port_iter()` 共 56 个；其中 **bus 端口 2**（`req_msg[31:0]`、`resp_msg[15:0]`）+ bit 48 + scalar 6
- DEF 实际声明 `PINS 54`（54 个物理 pin = 48 bit + 6 scalar，与上一致）
- 方向：INPUT 37 / OUTPUT 19
- 全部有位置（无位置端口数 = 0）

### 2.5 线网（net）

- `net_iter()` 共 307 个；其中 **bus 网 6**（`_197_[15:0]`、`ctrl.state.out[1:0]`、`dpath.a_reg.out[15:0]`、`dpath.b_reg.out[15:0]`、`req_msg[31:0]`、`resp_msg[15:0]`）+ bit 98 + scalar 203
- DEF 实际声明 `NETS 301`（301 = 98 bit + 203 scalar，与上一致）
- use 分布：CLOCK ×1（`clk`）、SIGNAL ×306
- 特殊网（电源/地）：0（该 DEF 无 SPECIALNETS，未做 PDN）
- 物理布线形状：wire=0、via=0（见下方 API 坑 #9）

### 2.6 GCellGrid / Track（可选）

- GCellGrid：2 个（X：35×5700，Y：35×5700，start=0）
- Track：20 条（metal1–metal10 各 2 条 X/Y）

---

## 3. 交叉验证

复用 `analysis/placement_analysis.py` 与 `analysis/cell_area.py` 核对：

- `placement_analysis.py`：Instance 231 / Placed 231 / Fixed 0 / Unplaced 0，Cell area 398 µm² ✅（Rows 显示 N/A，因它调用了不存在的 `site_array_iter()`）
- `cell_area.py`：21/21 种 cell，总面积 397.94 µm² ✅

与 `parse_def.py` 结果（231 组件、全 PLACED、21 种 cell、~398 µm²）一致。

---

## 4. 遇到的 API 坑

1. **tech 名称**：`load_lef()` 不传 name 时 `tech.name` 是默认 `"ref"`，不会取 LEF 内库名。
2. **枚举 str 带类名前缀**：`str(layer.type)` 返回 `"LayerType.ROUTING"` 而非 `"ROUTING"`；打印/入库前需 `str(e).split(".")[-1]`，比较则用 `datalens.phylib.LayerType.ROUTING` 等成员。
3. **tech 无 `site_iter()` / 无各种 count()**：layer/via/macro 只能用 `tech.layer_iter()/via_iter()/macro_iter()` 遍历计数（仅有 `via_rule_count()`）。site 只能用 `tech.site(name)` 按名字取，站点名需自行从 LEF 文本 `^SITE <name>` 提取，或从 DEF 的 `row.site` 拿到。
4. **module 无 `site_array_iter()`**：旧脚本 `placement_analysis.py` 用的 `top.site_array_iter()` 在当前 build 不存在（被 except 吞掉显示 N/A）。正确接口是 `module.row_iter()`，行对象是 `SiteArray`，属性 `name/site/location/bbox/is_horizontal/x_count/y_count/x_step/y_step`。
5. **层间距读不到**：`layer.width()`、`layer.pitch()/pitch_x()/pitch_y()` 可读；但 `spacing`（同层间距）没有直接方法暴露（只在 routing rule 里，pybind 未开放）。
6. **bus 聚合对象**：`port_iter()` 会额外给出 bus 端口（`req_msg[31:0]`），`net_iter()` 会额外给出 bus 网（`_197_[15:0]` 等），因此 `port_count()=56 > DEF PINS 54`、`net_count()=307 > DEF NETS 301`。用 `is_bus()/is_bit()/is_scalar()` 区分。
7. **摆放状态**：`inst.place_status()` 返回 `PlaceStatus` 枚举（PLACED/FIXED/UNPLACED/COVER/SOFT_FIXED），用 `str()` 或与枚举成员比较。
8. **特殊网判断**：`net` 没有 `is_special()`；判断电源/地用 `net.use()` 返回 `UseType`（POWER/GROUND/…）。本 DEF 无 SPECIALNETS（未做 PDN），故特殊网=0。
9. **无布线形状**：`write_def` 未加 `-routing`，DEF 里无 `+ ROUTED`、无 SPECIALNETS，所以 `net.shape_iter()` 里 wire/via 计数为 0（是数据本身没有，不是解析失败）。要拿到布线需重跑 `write_def -routing` 或解析全局布线 DB。
10. **die/core 面积**：`module.bbox()` 返回 DIEAREA 包围盒；core 面积需自行由 `row_iter()` 的 bbox 围出（该 DEF 没有单独的 CORE 语句）。
