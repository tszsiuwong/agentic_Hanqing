# agentic_Hanqing

Dizo EDA 工具的 Python 脚本集与文档。

## 环境

```bash
export LD_LIBRARY_PATH=$HOME/local/python3/lib:$HOME/dizo/third_party/spring_rls/lib:$HOME/dizo/build/dizo/lib:$HOME/dizo/build/dizo/lib/modules/py:$HOME/dizo/build/dizo/parser/tclio/bin:$LD_LIBRARY_PATH
export PYTHONPATH=$HOME/dizo/build/dizo/lib/modules/py
export PATH=$HOME/local/python3/bin:$HOME/local/bin:$HOME/.local/bin:$PATH
```

## 目录

```
├── examples/              # Python 示例脚本
│   └── count_instances.py
└── docs/
    ├── quickstart.md      # 快速开始
    └── python-api.md      # Python API 速查
```

## 使用

```bash
python3.11 examples/count_instances.py <网表.v>
```
