# Dizo 快速开始

## 加载设计

```tcl
load_lef tech.lef              # 工艺库
load_lef cells.lef             # 单元库
load_def design.def            # 设计

load_lib timing.lib            # 时序库（可选）
load_parasitics design.spef    # 寄生参数（可选）
load_sdf delay.sdf             # SDF（可选）
load_upf power.upf             # 电源域（可选）
```

## 导出数据

```tcl
dump_def -file output.def
dump_lef -file output.lef
dump_lef_abstract -file abstract.lef
dump_gds2 -file output.gds -map layer_map.json
```

## 基本查询

```tcl
get_obj_insts                  # 所有实例
get_obj_insts "U*"             # 按名称匹配
get_obj_nets                   # 所有网络
get_obj_ports                  # 所有端口
get_obj_layers                 # 工艺层
get_db_boundary                # Die 边界
get_db_rows                    # Row 信息
get_db_tracks                  # Track 信息
get_attribute <obj> <attr>     # 查询属性
```

## Python 加载

```python
import datalens
datalens.exchange.load_lef(["tech.lef", "cells.lef"])
datalens.exchange.load_def(["design.def"])
project = datalens.design.present_project()
top = project.present_module()
```

## 多线程加速

```tcl
set_multi_threads -thread_number 32
load_lef tech.lef
load_def large_design.def
```
