# 层级网表分析

`tests/st/db_tclio/base/basic_tcl/test.v` — Dizo 自带层级测试用例。

## 模块结构

```
top (3 ports, 9 nets)
├── u1 (ANDX1)
├── u2 (ANDX1)
├── hinst_sub → sub (4 ports, 7 nets)
│   ├── u1 (ANDX1)
│   ├── u2 (ANDX1)
│   └── hinst_sub2 → sub2 (2 ports, 5 nets)
│       ├── u1 (ANDX1)
│       └── hinst_sub3 → sub3 (2 ports, 3 nets)
│           └── u (ANDX1)
└── top_sub4 → sub4 (2 ports, 3 nets)
    └── u (ANDX1)
```

| Module | Leaf | Hier | Ports | Nets |
|--------|------|------|-------|------|
| top | 2 | 2 | 3 | 9 |
| sub | 2 | 1 | 4 | 7 |
| sub2 | 1 | 1 | 2 | 5 |
| sub3 | 1 | 0 | 2 | 3 |
| sub4 | 1 | 0 | 2 | 3 |
| **Total** | **7** | — | — | — |

## 基础统计

| 指标 | 数值 |
|------|------|
| 叶节点 Instance | 7 (全 ANDX1) |
| 模块数 | 5 |
| 最大深度 | 4 (top→sub→sub2→sub3) |

![单元分布](cells.png)  ![功能分类](cell_functions.png)

## 连接度

Degree 均值 2.1，Fanout 均值 0.8。因为层级网表含多端口模块，内部连接被封装在各模块内，导致顶层的连接度偏低。Rent 因样本太小无法拟合。

![连接度](connectivity.png)

## 验证结论

层级遍历修复生效：修复前读到 4 个实例（仅顶层），修复后读到 7 个叶子实例（遍历全部 5 个模块）。`is_hier()` 正确过滤了层级块。
