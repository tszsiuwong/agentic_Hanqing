# agentic_Hanqing

Dizo EDA 工具的 Python 脚本集与物理设计工程文档。

## 环境

编译好的 Dizo 运行于指定的 Linux 服务器。登录后需加载以下环境变量：

```bash
export LD_LIBRARY_PATH=$HOME/local/python3/lib:$HOME/dizo/third_party/spring_rls/lib:$HOME/dizo/build/dizo/lib:$HOME/dizo/build/dizo/lib/modules/py:$HOME/dizo/build/dizo/parser/tclio/bin:$LD_LIBRARY_PATH
export PYTHONPATH=$HOME/dizo/build/dizo/lib/modules/py
export PATH=$HOME/local/python3/bin:$HOME/local/bin:$HOME/.local/bin:$PATH
```

## 目录

```
.
├── examples/          # Python 示例脚本
│   └── count_instances.py   # 读 Verilog 网表统计 Instance 数量
└── docs/              # 文档
    └── Dizo_物理设计工程师指南.md
```

## 使用

```bash
python3.11 examples/count_instances.py <网表文件.v>
```
