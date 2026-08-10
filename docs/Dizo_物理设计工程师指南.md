# Dizo 物理设计工程师指南

> **版本**: 0.2.0 | **日期**: 2026-06-16 | **项目**: [https://gitee.com/edahelper/dizo](https://gitee.com/edahelper/dizo)

---

## 1. 项目概述

Dizo 是一款面向 IC 设计数字底座的开源 EDA 数据库与交换工具。对物理设计工程师而言，Dizo 提供了一套**完整的物理设计数据模型**和**多格式文件读写能力**，支持从工艺库加载到版图输出的全流程数据处理。

### 1.1 物理设计核心能力

| 能力 | 描述 |
|------|------|
| **工艺数据管理** | 完整 LEF 5.7/5.8 工艺规则建模（Layer、Via、Site、NDR、DRC Rule 等 100+ 规则类） |
| **设计数据管理** | 布局布线数据：Placement、Routing、Special Net、Row/Track、Blockage/Halo/Region |
| **多格式读写** | LEF/DEF 读写、GDSII 写入、SPEF/SDF 寄生参数读取、Liberty 时序库读取、UPF 电源域读取 |
| **空间查询** | 基于 HV-Tree（层次 Voronoi 树）的高效区域查询，支持多线程构建与查询 |
| **2D→3D 映射** | 支持 2D 版图数据向 3D 封装映射的自动化流程 |
| **Chiplet 支持** | 多芯粒（Multi-Die）物理设计数据管理与位置分配 |
| **Python 绑定** | 通过 datalens 模块以 Python API 访问所有物理设计数据 |
| **TCL 交互** | 完整的 TCL 命令行交互接口，支持脚本化批量操作 |

### 1.2 应用场景

- **设计数据交换**：在不同 EDA 工具间传输 LEF/DEF 数据，统一数据表示
- **工艺规则检查**：加载 LEF 工艺文件，查询任何 Layer/Via/NDR/DRC 规则参数
- **布局分析**：分析 Row、Track、Placement、Routing 等物理数据
- **寄生参数提取**：读取 SPEF 文件，构建 RC 树模型
- **版图输出**：生成 GDSII 流文件
- **自动化脚本**：通过 TCL/Python 批量处理物理设计数据

---

## 2. 快速开始

### 2.1 启动与加载设计

```bash
# 启动 TCL 交互终端
db_shell
```

```tcl
# 加载工艺库（LEF）
load_lef tech.lef
load_lef stdcell.lef
load_lef macro.lef

# 加载设计（DEF）
load_def design.def

# 加载时序库（Liberty）
load_lib timing.lib

# 加载寄生参数（SPEF）
load_parasitics parasitic.spef

# 加载 SDF
load_sdf delay.sdf
```

### 2.2 导出数据

```tcl
# 导出 DEF
dump_def -file output.def

# 导出 LEF
dump_lef -file output.lef

# 导出 LEF Abstract（只含端口/物理信息）
dump_lef_abstract -file abstract.lef -obs_top_layer 4

# 导出 GDSII（需启用 gds2txt 模块）
dump_gds2 -file output.gds -map gds_layer_map.json
```

---

## 3. 数据模型详解

Dizo 的物理设计数据模型分为三大层级：**工艺库（Tech）** → **设计物理数据（ModulePhys）** → **物理几何与网络（NetPhys / RouteShape）**。

### 3.1 工艺数据模型（`dm/tech/`）

工艺数据模型实现了 **LEF 5.7/5.8 完整规范**，覆盖 100+ 种工艺规则类型。

#### 3.1.1 核心工艺对象

| 类 | 路径 | 描述 |
|----|------|------|
| `Tech` | `include/dm/tech/tech.h` | 工艺数据库根对象，管理所有 Layer、Via、Site、NDR、DRC Rule |
| `Layer` | `include/dm/tech/layer.h` | 层定义基类，包含名称、类型、层号、默认宽度、掩模数 |
| `PhysicalLayer` | `include/dm/tech/physical_layer.h` | 物理层，支持工艺栈顺序、上下层导航 |
| `Site` | `include/dm/tech/site.h` | 标准单元 Site 定义（宽度、高度、对称性） |
| `ViaTemplate` | `include/dm/tech/via_template.h` | 通孔模板，定义 Cut/Bottom/Top 三层几何形状 |
| `ViaRule` | `include/dm/tech/via_rule.h` | 通孔自动生成规则（VIARULE GENERATE） |
| `NonDefaultWidthRule` | `include/dm/tech/ndr_rule.h` | 非默认宽度规则 |
| `NonDefaultSpaceRule` | `include/dm/tech/ndr_rule.h` | 非默认间距规则 |

#### 3.1.2 DRC 规则全览

**Routing Layer 规则** (`RoutingLayerRule`, `include/dm/tech/routing_layer_rule.h`)：

| 规则类别 | 包含规则项 |
|----------|------------|
| **基本尺寸** | MINWIDTH/MAXWIDTH, PITCH, OFFSET, DIAGPITCH, DIAGWIDTH, DIAGSPACING |
| **间距规则** | SPACING（含 SAMENET/NOTCHLENGTH/ENDOFLINE/PARALLELOVERLAP 等 30+ 子类型） |
| **面积/密度** | MINAREA, FILLDENSITY, MAXFLOATINGAREA |
| **工艺参数** | 方块电阻 (RESPERSQ), 方块电容 (CAPPERSQ), 边缘电容 (EDGECAP), 厚度/高度 |
| **高级规则** | CORNERSPACING, EOLKEEPOUT, EOL_EXTENSIONSPACING, JOGTOJOG, FORBIDDENSPACING, VOLTAGESPACING, SPANLENGTHENCLOSURESPACING, FIVEWIRESEOLSPACING, LITHOMACROHALO, PINCONNECTBLOCKAGE, RIGHTWAYONGRIDONLY, COREEOLBLOCKAGE, BOUNDARYEOLBLOCKAGE |
| **查找表** | WIDTHTABLE, SPACINGTABLE, SPANLENGTHTABLE |

**Cut Layer 规则** (`CutLayerRule`, `include/dm/tech/cut_layer_rule.h`)：

| 规则类别 | 包含规则项 |
|----------|------------|
| **基本规则** | CUTSPACING, ENCLOSURE, PREFERENCLOSURE, ARRAYSPACING |
| **高级规则** | EOLSPACING, EOLENCLOSURE, ENCLOSUREEDGE, ENCLOSURETABLE, KEEPOUTZONE, ORTHOGONALSPACING, DIRECTIONALSPACING, NOMETALSPACING, ENCLOSURETOJOINT, ADJACENTFOURCUTS, ONEDARRAY, CUTONCENTERLINE, FORBIDDENSPACING, PRLTWOSIDESSPACING, OPPOSITEOVERLAPCUTSPACING |
| **分组规则** | CUTCLASS, VIAGROUP / VIAGROUPSPACING, VIACLUSTER, SAMEMETALALIGNEDCUTS |

**Masterslice Layer 规则** (`MSLayerRule`, `include/dm/tech/ms_layer_rule.h`)：

- MSSPACING, COREEDGELENGTH, TRIMSHAPE (SADP), TRIMMEDMETAL, WIDTHLENGTHRATIO, MSENCLOSURE

#### 3.1.3 Layer 类型枚举

```cpp
// include/dm/tech/enums.h
enum LayerType {
  kRouting     = 0,   // 布线层
  kCut         = 1,   // 通孔层
  kMasterslice = 2,   // 电源层 / Masterslice
  kOverlap     = 3,   // 重叠层
  kImplant     = 4,   // 注入层
  kNWell       = 12,  // N 阱
  kPWell       = 14,  // P 阱
  kDiffusion   = 15,  // 扩散层
  // ... 以及 TRIM, CUTMETAL, MEOL, FINFET 等 30+ 类型
};

enum LayerDirection {
  kHorizDir   = 0,  // 水平
  kVertDir    = 1,  // 垂直
  kDiag45Dir  = 2,  // 对角线 45°
  kDiag135Dir = 3   // 对角线 135°
};
```

#### 3.1.4 工艺数据查询示例

```tcl
# 获取所有层
get_obj_layers

# 查询指定层
set m1 [get_obj_layers "M1"]
get_attribute $m1 width
get_attribute $m1 pitch
get_attribute $m1 direction

# 查询通孔定义
get_obj_via_templates

# 查询通孔规则
get_obj_via_rules

# 查询 Site 定义
get_obj_sites
```

---

### 3.2 设计物理数据模型（`dm/design/physical/`）

#### 3.2.1 核心对象

| 类 | 文件 | 描述 |
|----|------|------|
| `ModulePhys` | `include/dm/design/physical/module_phys.h` | 模块物理数据容器（Die/Core 边界、Row、Track、NDR、Place/Route Guide） |
| `InstPhys` | `src/dm/design/physical/inst_phys.h` | 实例物理放置状态 |
| `NetPhys` | `include/dm/design/physical/net_phys.h` | 网络物理路由数据（拥有所有 PhyRouteShape） |
| `FramePhys` | `include/dm/design/physical/frame_phys.h` | 宏单元物理框架（MACRO 尺寸/对称性/阻塞） |
| `PhyRouteShape` | `include/dm/design/physical/phy_route_shape.h` | 物理路由形状基类 |
| `Path` | `include/dm/design/physical/path.h` | 增量路由段（有序 PhyRouteShape 序列） |

#### 3.2.2 路由形状类型

| 形状类 | 描述 | 典型来源 |
|--------|------|----------|
| `PhyRouteRect` | 轴对齐矩形 | DEF ROUTED + RECT |
| `PhyRouteWire` | 中心线 + 宽度 + 延伸（Wire） | DEF ROUTED + RECT |
| `PhyRouteVia` | 标准通孔放置 | DEF ROUTED + VIA |
| `PhyRouteTrapz` | 梯形形状 | DEF POLYGON |
| `PhyRoutePolygon` | 任意多边形 | DEF POLYGON |

每种形状支持：
- **Layer / Mask** 分配（支持多图案）
- **RouteStatus** 标记（ROUTED/FIXED/COVER/LOCKED）
- **RouteType** 分类（Ring/Stripe/FollowPin/Fill/Junction 等）
- **Special** 路由标记（PG 网络）
- **BBox / PointArray** 几何查询

#### 3.2.3 布局规划对象

| 类 | 描述 |
|----|------|
| `SiteArray` | Row 定义（起点、Site 类型、方向、X/Y 数量和步长） |
| `TrackArray` | Track 定义（方向、起始位置、数量、间距、层、掩模、宽度） |
| `PlaceGuide` | 布局约束（Blockage/Halo/Region/MacroDensity） |
| `RouteGuide` | 布线约束（RoutingBlockage/RoutingHalo/MacroObs） |
| `PlaceGuideFunc` | 布局约束功能类型（FENCE/GUIDE/REGION 等） |
| `MacroMajorClass` | 宏单元主分类（Core/Cover/Ring/Block/Pad 等） |
| `MacroSubClass` | 宏单元子分类（80+ 子类型：BlackBox/Soft/Bump/Fill/TSV/Edge/Corners 等） |

#### 3.2.4 设计物理数据查询

```tcl
# 查询模块边界
get_db_boundary

# 查询 Row 信息
get_db_rows

# 查询 Track 信息
get_db_tracks

# 查询 Blockage
get_obj_blockages

# 查询实例
get_obj_insts "inst*"

# 查询实例物理属性
get_attribute [get_obj_insts "U1"] origin

# 查询网络路由信息
get_obj_phyNets

# 查询 Special Net
get_obj_snets
```

---

### 3.3 寄生参数数据模型（`dm/parasitic/`）

基于 **SPEF（Standard Parasitic Exchange Format）** 标准的寄生参数数据模型。

| 类 | 描述 |
|----|------|
| `DesignParasitic` | 顶层寄生参数容器（按 Corner 组织） |
| `DNetParasitic` | 分布式网络寄生参数（Node + XCap + Edge + Pin） |
| `RNetParasitic` | 简化网络寄生参数（ReduceModel 数组） |
| `ExtractNode` | 提取节点（含对地电容） |
| `ExtractExtendNode` | 带有坐标和层信息的提取节点 |
| `ExtractXCap` | 耦合电容（两个节点/网络之间） |
| `ExtractEdge` | 电阻/电感边 |
| `ExtractPin` | 提取引脚（绑定网表引脚到提取节点） |
| `RCTree` | RC 树（支持分层父子结构，用于时序分析） |
| `PiElmoreModel` | PI 模型 + Elmore 延迟 |
| `PiPoleResidueElmoreModel` | PI 模型 + Pole/Residue + Elmore 延迟 |

---

### 3.4 几何类型与空间查询

#### 3.4.1 几何类型

| 类型 | 描述 |
|------|------|
| `Point` (`x, y`) | 二维坐标点（`Coordinate` 类型） |
| `Rect` | 轴对齐矩形（LL + UR） |
| `Polygon` | 任意多边形（`PointArray` 序列） |
| `Trapz` | 梯形 |
| `TriRect` | 直角三角形 |
| `Line` | 线段 |
| `GeoVector` | 几何向量（偏移量） |
| `Transform` | 几何变换（平移 + 8 种方向旋转/镜像） |

#### 3.4.2 空间查询引擎

`RegionQueryHV`（基于层次 Voronoi 树的区域查询引擎）：

- **Insert / Remove / RemoveAll**：对象管理
- **Query(bbox, filter)**：区域查询，支持自定义过滤器和匹配模式
- **HasOverlap**：碰撞检测
- **多线程支持**：构建和查询均可并行化

#### 3.4.3 几何布尔运算

基于 Boost.Geometry，提供完整的布尔操作：
- **Union（并集）**
- **Intersection（交集）**
- **Difference（差集）**
- **Polygon Simplification**（多边形简化）
- **Orthogonal Check**（正交性检查）

---

## 4. 文件格式支持

### 4.1 LEF（Library Exchange Format）

**读写支持**，覆盖 LEF 5.7 和 LEF 5.8 规范。

#### 读取选项

```tcl
# 基础读取
load_lef tech.lef
load_lef cell.lef

# 高级选项
load_lef -tech tech.lef              # 指定为工艺 LEF
load_lef -relax design.lef           # 宽松模式（跳过非致命错误）
load_lef -strict design.lef          # 严格模式（更严格的格式检查）
load_lef -combine_obs design.lef     # 合并 OBS（阻塞形状）
load_lef -split_mustjoinallports_pin design.lef  # 拆分 MUSTJOIN 引脚
```

#### 写入选项

```tcl
# 导出 LEF
dump_lef -file output.lef -tech

# 导出 Abstract LEF（只含端口/物理信息）
dump_lef_abstract -file abstract.lef
dump_lef_abstract -file abstract.lef -pg_pin_layers {M1 M2 M3}
dump_lef_abstract -file abstract.lef -obs_top_layer 5
dump_lef_abstract -file abstract.lef -add_obs_layers {M2 M3}
dump_lef_abstract -file abstract.lef -extract_block_obs
```

#### LEF 解析内容覆盖

| LEF 语句 | 支持 |
|----------|------|
| TECHNOLOGY / UNITS / MANUFACTURINGGRID | ✅ |
| LAYER (Routing/Cut/Masterslice/Overlap/Implant) | ✅ |
| VIA / VIARULE / VIARULE GENERATE | ✅ |
| SITE | ✅ |
| NONDEFAULTRULE | ✅ |
| MACRO / PIN / OBS | ✅ |
| DENSITY / PROPERTY | ✅ |
| LEF58 全部扩展规则 | ✅ |

#### Python API

```python
import datalens

# 加载 LEF 文件
datalens.exchange.load_lef(["tech.lef", "stdcell.lef"])

# 访问工艺数据
tech = datalens.design.get_tech()
layers = tech.get_layers()
for layer in layers:
    print(f"Layer: {layer.name}, Type: {layer.type}, Width: {layer.width}")
```

---

### 4.2 DEF（Design Exchange Format）

**读写支持**，覆盖 DEF 5.6/5.7/5.8 规范。

#### 读取选项

```tcl
# 基础读取
load_def design.def

# Section 部分加载
load_def -section {COMPONENTS NETS} design.def

# 翻转坐标
load_def -flip design.def

# 虚拟连线模式
load_def -virtual_wire design.def

# 严格模式
load_def -strict design.def

# Verilog 限制模式
load_def -verilog_restrict_mode design.def

# 允许新建设计
load_def -allow_new_design design.def

# Site 名称映射
load_def -equal_sites {core core_1x} design.def
```

#### 写入选项

```tcl
# 基础写入
dump_def -file output.def

# Floorplan 模式（只输出边界/Row/Placement）
dump_def -file fp.def -floorplan

# 过滤内容
dump_def -file output.def -no_net            # 不输出普通网络
dump_def -file output.def -no_special_net    # 不输出 Special Net
dump_def -file output.def -no_logical_stdcell # 不输出逻辑标准单元
dump_def -file output.def -no_std_cells      # 不输出标准单元

# Section 选择性输出
dump_def -file output.def -section {COMPONENTS SPECIALNETS}

# 写出 Via 线
dump_def -file output.def -wire_via

# 翻转坐标
dump_def -file output.def -flip

# 路由状态过滤
dump_def -file output.def -route_status {ROUTED FIXED}

# 扫描链 DEF
dump_scan_def -file scan.def
dump_scan_def -file scan.def -expand_insts
```

#### DEF 解析内容覆盖

| DEF 语句 | 支持 |
|----------|------|
| VERSION / DIVIDERCHAR / BUSBITCHARS / DESIGN / UNITS | ✅ |
| DIEAREA / ROWS / TRACKS | ✅ |
| COMPONENTS (含 HALO / PROPERTY / EEQMASTER) | ✅ |
| PINS (含 PORT / LAYER / PLACED/FIXED/COVER) | ✅ |
| NETS / SPECIALNETS (含 SHIELDNET) | ✅ |
| VIAS / NONDEFAULTRULES / REGIONS / GROUPS | ✅ |
| BLOCKAGES (Placement / Routing) | ✅ |
| FILLS / SLOTS | ✅ |
| SCANCHAINS | ✅ |
| GCELLGRID | ✅ |
| FLOORPLAN 模式 | ✅ |
| 层级 DEF（Hierarchical DEF） | ✅ |

---

### 4.3 GDSII

**写支持**（流文件输出）。读取需要通过 `gds2txt` 模块（GDS 转文本工具）。

```tcl
# 导出 GDSII 流文件
dump_gds2 -file output.gds
dump_gds2 -file output.gds -map gds_layer_map.json    # 层映射文件
dump_gds2 -file output.gds -units 1000                # 单位设置
dump_gds2 -file output.gds -output_macro              # 输出 LEF 宏单元几何
```

**JSON 层映射文件格式**：

```json
{
  "map": {
    "M1": 31,
    "M2": 32,
    "VIA1": 41,
    "...": "..."
  }
}
```

---

### 4.4 SPEF（Standard Parasitic Exchange Format）

```tcl
# 读取 SPEF（含对地电容、耦合电容、电阻网络）
load_parasitics parasitic.spef

# 加载 LEF/DEF 后再加载 SPEF
load_lef tech.lef
load_def design.def
load_parasitics parasitic.spef
```

支持解析：
- `*D_NET`（分布式网络：节点电容、耦合电容、电阻边）
- `*R_NET`（简化网络：PI 模型 + Elmore 延迟）
- `*CONN`（连接属性：方向、坐标）
- 变体参数（Variation Parameters）

---

### 4.5 SDF（Standard Delay Format）

```tcl
load_sdf delay.sdf
```

---

### 4.6 Liberty（时序库）

```tcl
load_lib timing.lib
```

---

### 4.7 UPF（Unified Power Format）

```tcl
load_upf power.upf
```

---

## 5. TCL 命令参考

### 5.1 文件读写命令

| 命令 | 功能 | 关键参数 |
|------|------|----------|
| `load_lef` | 加载 LEF 工艺/库文件 | `-relax`, `-strict`, `-tech`, `-combine_obs`, `-split_mustjoinallports_pin` |
| `load_def` | 加载 DEF 设计文件 | `-section`, `-flip`, `-strict`, `-virtual_wire`, `-verilog_restrict_mode`, `-equal_sites`, `-allow_new_design` |
| `dump_lef` | 输出 LEF 文件 | `-file`, `-tech`, `-module` |
| `dump_lef_abstract` | 输出 LEF Abstract 视图 | `-file`, `-pg_pin_layers`, `-obs_top_layer`, `-add_obs_layers`, `-extract_block_obs` |
| `dump_def` | 输出 DEF 文件 | `-file`, `-floorplan`, `-no_net`, `-no_special_net`, `-wire_via`, `-flip`, `-no_logical_stdcell`, `-no_std_cells`, `-section`, `-route_status` |
| `dump_scan_def` | 输出扫描链 DEF | `-file`, `-expand_insts` |
| `dump_gds2` | 输出 GDSII 流文件 | `-file`, `-map`, `-units`, `-output_macro` |
| `load_lib` | 加载 Liberty 时序库 | `filename` |
| `load_parasitics` | 加载 SPEF 寄生参数 | `filename` |
| `load_sdf` | 加载 SDF 延迟文件 | `filename` |
| `load_upf` | 加载 UPF 电源域文件 | `filename` |
| `load_netlist` | 加载 Verilog 网表 | `filename` |

### 5.2 物理设计查询命令

| 命令 | 功能 |
|------|------|
| `get_obj_layers` | 查询工艺层列表 |
| `get_obj_layers <pattern>` | 按名称模式查询工艺层 |
| `get_obj_via_templates` | 查询通孔模板 |
| `get_obj_via_rules` | 查询通孔生成规则 |
| `get_obj_sites` | 查询 Site 定义 |
| `get_obj_rows` | 查询 Row 信息 |
| `get_obj_tracks` | 查询 Track 信息 |
| `get_obj_blockages` | 查询 Blockage 定义 |
| `get_obj_regions` | 查询 Region 定义 |
| `get_db_boundary` | 查询模块/Die 边界 |
| `get_obj_insts` | 查询实例列表 |
| `get_obj_insts <pattern>` | 按模式匹配查询实例 |
| `get_obj_insts -hierarchical` | 查询层级实例 |
| `get_obj_nets` | 查询网络列表 |
| `get_obj_nets <pattern>` | 按模式匹配查询网络 |
| `get_obj_ports` | 查询端口列表 |
| `get_obj_phyNets` | 查询物理网络 |
| `get_obj_snets` | 查询 Special Net（PG 网络） |

### 5.3 数据操作命令

| 命令 | 功能 |
|------|------|
| `get_attribute <obj> <attr>` | 查询对象属性 |
| `set_attribute -object <obj> -name <attr> -value <val>` | 设置对象属性 |
| `add_inst <name> <cell_type>` | 添加实例 |
| `delete_inst -name <name>` | 删除实例 |
| `set_multi_threads -thread_number <n>` | 设置并行线程数 |

### 5.4 批量操作示例

```tcl
# 批量导出所有层的 Pitch 信息
set fp [open "layer_pitch.txt" w]
foreach layer [get_obj_layers] {
    set name [get_attribute $layer name]
    set type [get_attribute $layer type]
    if {$type == "Routing"} {
        set pitch [get_attribute $layer pitch]
        puts $fp "$name: $pitch"
    }
}
close $fp

# 批量导出网络路由数据
set fp [open "route_report.txt" w]
foreach net [get_obj_phyNets] {
    set name [get_attribute $net name]
    set bbox [get_attribute $net bbox]
    puts $fp "$name: $bbox"
}
close $fp
```

---

## 6. Python API 参考（datalens 模块）

### 6.1 加载设计

```python
import datalens

# 加载 LEF/DEF
datalens.exchange.load_lef(["tech.lef", "stdcell.lef"])
datalens.exchange.load_def(["design.def"])

# 加载 Liberty 时序库
datalens.exchange.load_lib(["timing.lib"])

# 获取项目和顶层模块
project = datalens.design.present_project()
top_module = project.present_module()
```

### 6.2 工艺数据查询

```python
tech = datalens.design.get_tech()

# 遍历所有层
for layer in tech.get_layers():
    print(f"Layer: {layer.name}, Type: {layer.type}, Width: {layer.width}")

# 查询特定层
m1 = tech.get_layer_by_name("M1")
print(f"M1: width={m1.width}, pitch={m1.pitch}, direction={m1.direction}")

# 查询通孔模板
for via in tech.get_via_templates():
    print(f"Via: {via.name}, Bottom={via.bottom_layer.name}, Top={via.top_layer.name}")

# 查询 Site
for site in tech.get_sites():
    print(f"Site: {site.name}, Class={site.site_class}, W={site.width}, H={site.height}")
```

### 6.3 实例查询

```python
# 查询所有实例
cells = top_module.get_cells()
for cell in cells:
    origin = cell.origin
    bbox = cell.bbox
    print(f"Cell: {cell.name}, Type: {cell.type}, Origin: ({origin.x}, {origin.y})")

# 按名称模式查询
cells = top_module.get_cells("U*")

# 查询层级实例
cells_hier = top_module.get_cells("*", "", True)

# 查询物理属性
for cell in top_module.get_cells():
    phys = cell.physical
    if phys:
        print(f"  Status: {phys.status}, Orientation: {phys.orient}")
```

### 6.4 网络与引脚查询

```python
# 查询所有端口
ports = top_module.get_ports()
for port in ports:
    print(f"Port: {port.name}, Direction: {port.direction}")

# 查询引脚
pins = top_module.get_pins("*/A")
for pin in pins:
    print(f"Pin: {pin.name}, Net: {pin.net.name}")

# 查询物理网络
for net in top_module.get_nets():
    phys_net = net.physical
    if phys_net and phys_net.is_routed:
        print(f"Net: {net.name}, BBox: {phys_net.bbox}")
        for shape in phys_net.shapes:
            print(f"  Shape: {shape.type}, Layer: {shape.layer.name}")
```

---

## 7. 高级功能

### 7.1 多线程加载

大设计文件加载时启用多线程可显著提升速度（32 线程下 100MB 文件 ~1 秒）：

```tcl
# 设置 32 线程
set_multi_threads -thread_number 32

# 加载设计
load_lef tech.lef
load_def large_design.def
load_parasitics large_design.spef
```

### 7.2 2D→3D 映射

支持将 2D 物理设计数据映射到 3D 封装布局，通过 YAML 配置文件驱动：

```tcl
# 2D 版图数据 → 3D 封装
map_2d_files_to_3d_files -map_yaml config.yaml
```

### 7.3 Chiplet 多芯粒设计

面向 Multi-Die 设计的 Chiplet 数据管理：

```tcl
# 添加芯粒
add_chiplet -name chiplet_a

# 加载芯粒配置
load_chiplets -file chiplets.def

# 设置芯粒物理位置
set_chiplet_location -name chiplet_a -die 1

# 展平芯粒层级
flatten_chiplets
```

### 7.4 Floorplan 分区

```tcl
# 分区模块
partition -module top_module

# 加载 Bump/Pad 位置
load_bump -filename bump.loc
load_pad -filename pad.loc

# 展平分区
flatten_partition
```

---

## 8. 性能与容量

| 指标 | 参数 |
|------|------|
| 最大 Instance 数 | 1 亿 (100M) |
| 百万实例内存占用 | ~2 GB |
| 亿级实例内存占用 | ~200 GB |
| 100MB 文件加载（单线程） | ~10 秒 |
| 100MB 文件加载（32 线程） | ~1 秒 |
| 支持 LEF 文件数上限 | 100 个 |
| 支持 DEF 文件数上限 | 100 个 |

---

## 9. 测试覆盖

| 测试类别 | 覆盖范围 | 状态 |
|----------|----------|------|
| 工艺数据模型 (Tech) | Layer/Via/Site/NDR/全部 DRC Rule | 95% |
| 寄生参数模型 (Parasitic) | SPEF 网络寄生信息 | 85% |
| LEF 读写 | 完整 LEF 5.7/5.8 规范 | 读 ✅ 写 ✅ |
| DEF 读写 | 完整 DEF 5.6/5.7/5.8 规范 | 读 ✅ 写 ✅ |
| GDSII 写入 | GDSII 流文件生成 | 写 ✅（需 gds2txt） |
| 文件交换单元测试 | LEF/DEF/GDS | UT 82% |
| 文件交换系统测试 | LEF/DEF/GDS | ST 78% |

测试目录结构：

```
tests/
├── ut/exchange/lef_def/         # LEF/DEF 单元测试（15+ 测试场景）
├── ut/exchange/gds2/            # GDS2 单元测试
├── st/db_tclio/lef/             # LEF 系统测试（tech_lef/lib_lef/lef58_rule）
├── st/db_tclio/def/             # DEF 系统测试（50+ 测试场景）
├── st/common_case/demo_gds/     # GDS 用例测试
├── smoke/lef/                   # LEF 冒烟测试（LAYER/VIA/MACRO/SITE）
├── smoke/def/                   # DEF 冒烟测试（PIN/VIA/TRACK/NET）
```

---

---

## 10. 常见工作流

### 10.1 标准数字后端加载流程

```tcl
# 1. 设置并行度
set_multi_threads -thread_number 32

# 2. 加载工艺库
load_lef -tech tech.lef
load_lef cell_1.lef
load_lef cell_2.lef
load_lef macro.lef

# 3. 加载设计
load_def design.def

# 4. 加载时序库
load_lib slow.lib
load_lib typical.lib
load_lib fast.lib

# 5. 加载寄生参数
load_parasitics design.spef

# 6. 分析/处理...
# ...

# 7. 导出结果
dump_def -file final.def
dump_lef_abstract -file abstract.lef
dump_gds2 -file final.gds -map layer_map.json
```

### 10.2 工艺信息提取

```tcl
# 加载工艺 LEF
load_lef -tech tech.lef

# 导出所有层信息
foreach layer [get_obj_layers] {
    set name [get_attribute $layer name]
    set type [get_attribute $layer type]
    set width [get_attribute $layer width]
    set pitch [get_attribute $layer pitch]
    set direction [get_attribute $layer direction]
    puts "$name | $type | $width | $pitch | $direction"
}

# 导出所有通孔信息
foreach via [get_obj_via_templates] {
    set name [get_attribute $via name]
    puts "Via: $name"
}
```

### 10.3 物理数据提取

```tcl
# 加载完整设计
load_lef tech.lef
load_lef cells.lef
load_def design.def

# 查询 Die 边界
set bndy [get_db_boundary]
puts "Die Boundary: $bndy"

# 统计 Row 信息
set row_count [llength [get_db_rows]]
puts "Total Rows: $row_count"

# 统计 Track 信息
foreach track [get_db_tracks] {
    set layer [get_attribute $track layer]
    set count [get_attribute $track count]
    set step [get_attribute $track step]
    puts "Track $layer: count=$count, step=$step"
}

# 统计实例数和利用率
set insts [get_obj_insts]
set total_cells [llength $insts]
set total_area 0.0
foreach inst $insts {
    set area [get_attribute $inst area]
    set total_area [expr $total_area + $area]
}
puts "Total Instances: $total_cells"
puts "Total Cell Area: $total_area"
```

---

## 11. 参考资料

| 文档 | 路径 |
|------|------|
| 用户指南 | `USER_GUIDE.md` |
| 开发者指南 | `DEVELOPER_GUIDE.md` |
| 架构文档 | `.claude/ARCHITECTURE.md` |
| 构建指南 | `.claude/BUILD.md` |
| 编码规范 | `.claude/CODING_STANDARDS.md` |
| 测试指南 | `.claude/TESTING.md` |
| 物理数据加载 | `doc/docs/content/20_data_loading/logical_to_physical.md` |
| LEF 数据模型 | `doc/docs/content/30_data_model/lef/` |
| DEF 数据模型 | `doc/docs/content/30_data_model/def/` |
| 项目主页 | [https://gitee.com/edahelper/dizo](https://gitee.com/edahelper/dizo) |

---

## 12. 常见问题

**Q: LEF/DEF 读取失败怎么办？**

A: 检查文件路径和格式兼容性。可以尝试使用 `-relax` 宽松模式加载，或使用 `-strict` 模式查看详细的格式错误信息。

**Q: 大设计加载速度慢怎么办？**

```tcl
# 使用多线程加速
set_multi_threads -thread_number 32
load_lef tech.lef
load_def large_design.def
```

**Q: 如何只加载 DEF 的部分内容？**

```tcl
# 只加载 COMPONENTS 和 NETS section
load_def -section {COMPONENTS NETS} design.def

# 只加载 Floorplan（边界/Row/Placement）
load_def -section {DIEAREA ROWS COMPONENTS} design.def
```

**Q: 如何查看某个层完整的 DRC 规则？**

```tcl
load_lef tech.lef
set m1 [get_obj_layers "M1"]
puts "Width: [get_attribute $m1 width]"
puts "Pitch: [get_attribute $m1 pitch]"
puts "Direction: [get_attribute $m1 direction]"
# 更多规则通过 get_attribute 查询
```

**Q: 运行时提示库找不到？**

```bash
export LD_LIBRARY_PATH=./output/lib:$LD_LIBRARY_PATH
```
