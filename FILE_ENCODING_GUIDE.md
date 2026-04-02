# 文件编码与结构指南

## 📁 生成的文件结构

```
output/
└── 20260401_143000_1_优化方向名称/
    ├── {direction}_patch.py         # ✅ 新增优化代码（UTF-8）
    ├── {direction}_test.py          # 🧪 测试代码（UTF-8）
    ├── baseline_backup.py           # 💾 原始 baseline 备份（UTF-8）
    ├── integration_example.py       # 📖 集成示例（UTF-8）
    ├── INTEGRATION_GUIDE.md         # 📚 集成指南（UTF-8）
    └── INTEGRATION_GUIDE.json       # 🔧 结构化信息（UTF-8）
```

## 🔤 UTF-8 编码保证

### 所有文件使用 UTF-8 编码

每个 Python 文件头部都有编码声明：

```python
# -*- coding: utf-8 -*-
"""
==============================================================================
{方向名称} - 增量优化代码
==============================================================================

【重要说明】
1. 本文件只包含新增的优化代码，绝不包含原始 baseline 代码
2. 使用增量修改模式（装饰器/继承/包装），不修改原有代码
3. 所有中文注释使用 UTF-8 编码
==============================================================================
"""
```

### 编码验证

系统会自动验证文件编码：

```python
from utils.file_encoding import ensure_utf8

# 验证文件编码
is_utf8 = ensure_utf8("path/to/file.py")
print(f"UTF-8 验证: {'通过' if is_utf8 else '失败'}")
```

## ✂️ 代码分离原则

### 绝不混合代码

| 文件 | 内容 | 说明 |
|------|------|------|
| `*_patch.py` | **只包含优化代码** | 新增功能，独立文件 |
| `baseline_backup.py` | **只包含原始代码** | 完整备份，用于对比 |

**禁止行为** ❌：
- 在 `*_patch.py` 中复制 baseline 代码然后修改
- 将优化代码混入 baseline_backup.py
- 生成包含完整 baseline 的"优化版本"

**正确做法** ✅：
- `*_patch.py` 只包含装饰器、包装器、继承类等增量代码
- 通过导入和引用的方式与 baseline 交互
- 保持 baseline_backup.py 原封不动

## 📖 文件详细说明

### 1. `{direction}_patch.py` - 优化代码

**内容**：
- 只包含新增的优化代码
- 使用增量修改模式（装饰器/继承/包装/回调）
- 绝不包含 baseline 原有代码

**示例**：
```python
# -*- coding: utf-8 -*-
"""
==============================================================================
SpecAugment数据增强 - 增量优化代码
==============================================================================

【重要说明】
1. 本文件只包含新增的优化代码，绝不包含原始 baseline 代码
2. 使用增量修改模式（装饰器），不修改原有代码
==============================================================================
"""

from functools import wraps

def spec_augment_decorator(cls):
    """SpecAugment 数据增强装饰器"""
    original_getitem = cls.__getitem__
    
    @wraps(original_getitem)
    def new_getitem(self, idx):
        data, label = original_getitem(self, idx)
        data = self.apply_spec_augment(data)  # 新增功能
        return data, label
    
    cls.__getitem__ = new_getitem
    return cls
```

### 2. `baseline_backup.py` - 原始 Baseline 备份

**内容**：
- 原始 baseline 代码的完整备份
- 不做任何修改，原封不动
- 用于对比和回滚

**示例**：
```python
# -*- coding: utf-8 -*-
"""
==============================================================================
原始 Baseline 代码备份
==============================================================================

【说明】
此文件是原始 baseline 代码的完整备份，用于：
1. 对比优化前后的代码变化
2. 需要时恢复原始代码
3. 理解优化代码与 baseline 的关系

【重要】
优化代码在 *_patch.py 中，不要直接修改此文件
==============================================================================
"""

import torch
import torch.nn as nn

class BirdDataset(Dataset):
    # 原始 baseline 代码，原封不动
    def __init__(self, df):
        self.df = df
    
    def __getitem__(self, idx):
        # 原始实现
        pass
```

### 3. `integration_example.py` - 集成示例

**内容**：
- 展示如何将优化代码集成到 baseline
- 提供多种集成方式
- 可直接运行的示例代码

### 4. `INTEGRATION_GUIDE.md` - 集成指南

**内容**：
- 详细的集成步骤
- 文件说明表
- 验证方法
- 回滚指南

## 🔄 回滚方法

### 方法1：使用备份文件

```bash
# 恢复原始 baseline
cp baseline_backup.py your_original_file.py
```

### 方法2：移除优化代码

```python
# 移除装饰器（恢复原始 Dataset）
from baseline_module import OriginalDataset

# 不再导入优化代码
# from optimization_patch import augment_decorator

# 使用原始版本
dataset = OriginalDataset(...)
```

## ✅ 编码检查工具

### 检查目录下所有文件编码

```python
from utils.file_encoding import check_directory_encoding

results = check_directory_encoding("./output")
for filepath, encoding, confidence in results:
    print(f"{filepath}: {encoding} ({confidence:.2%})")
```

### 转换文件为 UTF-8

```python
from utils.file_encoding import convert_to_utf8

success = convert_to_utf8("path/to/file.py")
```

### 写入 UTF-8 文件

```python
from utils.file_encoding import write_python_file

content = '''
# 中文注释
def hello():
    return "你好"
'''

write_python_file("output.py", content)
# 自动添加 # -*- coding: utf-8 -*-
```

## 🧪 验证示例

运行测试脚本验证编码：

```bash
python test_file_encoding.py
```

输出示例：
```
🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪
  文件编码测试
🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪

======================================================================
测试: write_python_file
======================================================================
✅ 写入文件: True
   检测编码: utf-8
✅ 读取内容成功: True
   第一行: # -*- coding: utf-8 -*-

======================================================================
测试: EngineerV2 输出文件结构
======================================================================

📁 检查目录: /tmp/...
   ✅ test_patch.py: utf-8 (置信度: 100.00%)
   ✅ baseline_backup.py: utf-8 (置信度: 100.00%)
   ✅ integration_example.py: utf-8 (置信度: 100.00%)
```

## ⚠️ 常见问题

### Q: 文件打开后中文显示乱码？

**A**: 确保使用 UTF-8 编码打开文件：

```python
# 正确方式
with open('file.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 错误方式（使用系统默认编码）
with open('file.py', 'r') as f:  # 可能使用 GBK
    content = f.read()
```

### Q: 如何确认文件是 UTF-8 编码？

**A**: 
1. 查看文件第一行是否有 `# -*- coding: utf-8 -*-`
2. 使用工具检查：`python -c "import chardet; print(chardet.detect(open('file.py', 'rb').read()))"`
3. 使用 VS Code 等编辑器查看右下角编码显示

### Q: 为什么需要 baseline_backup.py？

**A**: 
1. **对比**：理解优化代码与 baseline 的关系
2. **回滚**：需要时快速恢复原始代码
3. **审计**：追溯修改历史
4. **学习**：了解优化是如何在 baseline 基础上实现的
