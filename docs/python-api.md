# Python API 速查

## 加载文件

```python
import datalens

datalens.exchange.load_lef(["tech.lef", "cells.lef"])
datalens.exchange.load_def(["design.def"])
datalens.exchange.load_netlist(["design.v"])
datalens.exchange.load_lib(["timing.lib"])
datalens.exchange.load_spef(["parasitic.spef"])
```

## 设计导航

```python
project = datalens.design.present_project()
project.make_unique()
top = project.present_module()

# 实例操作
inst = top.inst("U1")                # 按名称查找
inst.insts                            # 子实例列表
inst.ref_name                         # 引用的 Cell
inst.is_hier()                        # 是否层级实例
for inst in top.inst_iter(): ...      # 迭代直接子实例

# 子模块
sub = top.module("sub_name")
```

## 查询与统计

```python
from datalens.design import HierFilterType

# 数量统计
top.inst_count(HierFilterType.ALL)    # 所有直接子实例
top.inst_count(HierFilterType.LEAF)   # 叶子（Standard Cell）
top.inst_count(HierFilterType.HIER)   # 层级块
top.port_count()
top.net_count()

# 模式匹配
top.get_cells("U*")                                # 通配符
top.get_cells("*", "is_hierarchical")              # 只查层级
top.get_cells("*", "!is_hierarchical")             # 只查叶子
top.get_cells("*", "", True)                       # 递归所有层级
top.get_cells("h_sub/*")                           # 层级路径

# 端口和引脚
top.get_ports("*", "direction == in")
top.get_pins("*/A")
```

## 实例属性

```python
inst = top.inst("U1")
# 身份
inst.name              # 实例名
inst.ref_name          # Cell 类型
inst.full_name         # 带层级的完整路径

# 物理属性（需加载 LEF/DEF）
inst.bbox()            # 边界框 Rect
inst.location()        # 坐标 Point(x, y)
inst.orient()          # 方向 Orient.N/E/S/W 等

# Pin 与 Net
for pin in inst.pin_iter():
    print(pin.name, pin.net.name)
```

## 网络查询

```python
net = top.net("net_name")
net.pins                     # 连接的 Pin 列表
for pin in net.pin_iter(): ...
net.fanin_pins()             # 驱动 pin
net.fanout_pins()            # 负载 pin 列表
```

## 工艺查询

```python
tech = datalens.design.get_tech()

# 遍历层
for layer in tech.get_layers():
    print(layer.name, layer.type, layer.width)

# 按名称查找
m1 = tech.get_layer_by_name("M1")

# 通孔模板
for via in tech.get_via_templates():
    print(via.name, via.bottom_layer.name, via.top_layer.name)

# Site
for site in tech.get_sites():
    print(site.name, site.width, site.height)
```

## 几何类型

```python
from datalens.geometry import Point, Rect

pt = Point(x, y)
rect = Rect(left, bottom, right, top)
rect.left, rect.right, rect.bottom, rect.top
rect.width, rect.height
rect.area
rect.is_overlap(other_rect)
```

## 遍历所有模块

```python
for mod in datalens.design.module_iter():
    print(mod.name, mod.port_count(), mod.net_count())
```

## 清理

```python
project.destroy()
```
