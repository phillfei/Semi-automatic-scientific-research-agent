# 生成的文件结构示例

## 输出目录结构

```
output/
└── 20260401_143000_1_specaugment_data_aug/
    ├── specaugment_data_aug_patch.py      # ✅ 新增优化代码（UTF-8）
    ├── specaugment_data_aug_test.py       # 🧪 测试代码（UTF-8）
    ├── baseline_backup.py                 # 💾 原始 baseline 备份（UTF-8）
    ├── integration_example.py             # 📖 集成示例（UTF-8）
    ├── INTEGRATION_GUIDE.md               # 📚 集成指南（UTF-8）
    └── INTEGRATION_GUIDE.json             # 🔧 结构化信息（UTF-8）
```

---

## 文件内容示例

### 1. `specaugment_data_aug_patch.py`（优化代码 - 绝不包含 baseline）

```python
# -*- coding: utf-8 -*-
"""
==============================================================================
SpecAugment数据增强 - 增量优化代码
==============================================================================

【重要说明】
1. 本文件只包含新增的优化代码，绝不包含原始 baseline 代码
2. 使用增量修改模式（装饰器/继承/包装），不修改原有代码
3. 集成方式: decorator
4. 目标位置: Dataset.__getitem__

【使用方法】
1. 将此文件保存到您的项目目录
2. 按照 INTEGRATION_GUIDE.md 的说明集成到 baseline
3. 原始 baseline 备份在 baseline_backup.py

==============================================================================
"""

import numpy as np
import torch
from functools import wraps


def spec_augment_decorator(cls):
    """
    SpecAugment 数据增强装饰器
    
    在 Dataset.__getitem__ 中应用时频掩码增强
    
    使用方式:
        @spec_augment_decorator
        class MyDataset(BaseDataset):
            pass
    """
    original_getitem = cls.__getitem__
    
    @wraps(original_getitem)
    def new_getitem(self, idx):
        # 1. 调用原始方法获取数据
        data, label = original_getitem(self, idx)
        
        # 2. 应用 SpecAugment 增强（仅训练时）
        if self.training and hasattr(self, 'apply_spec_augment'):
            data = self.apply_spec_augment(data)
        
        return data, label
    
    # 添加增强方法
    def apply_spec_augment(self, spectrogram):
        """
        应用 SpecAugment 增强
        
        Args:
            spectrogram: 输入频谱图 (mel_bins, time_steps)
        
        Returns:
            augmented: 增强后的频谱图
        """
        # 时间掩码
        time_mask_param = 10
        num_time_masks = 2
        
        for _ in range(num_time_masks):
            t = np.random.randint(0, time_mask_param)
            t0 = np.random.randint(0, spectrogram.shape[1] - t)
            spectrogram[:, t0:t0+t] = 0
        
        # 频率掩码
        freq_mask_param = 10
        num_freq_masks = 2
        
        for _ in range(num_freq_masks):
            f = np.random.randint(0, freq_mask_param)
            f0 = np.random.randint(0, spectrogram.shape[0] - f)
            spectrogram[f0:f0+f, :] = 0
        
        return spectrogram
    
    # 替换方法
    cls.__getitem__ = new_getitem
    cls.apply_spec_augment = apply_spec_augment
    
    return cls


# 便捷的装饰器别名
spec_augment = spec_augment_decorator


if __name__ == "__main__":
    # 使用示例
    print("SpecAugment 装饰器已加载")
    print("使用方法: @spec_augment_decorator")
```

---

### 2. `baseline_backup.py`（原始 baseline 备份）

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
优化代码在 specaugment_data_aug_patch.py 中，不要直接修改此文件
==============================================================================
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


class BirdDataset(Dataset):
    """鸟类声音数据集"""
    
    def __init__(self, df, transform=None):
        self.df = df
        self.transform = transform
    
    def __getitem__(self, idx):
        """获取单个样本"""
        row = self.df.iloc[idx]
        audio = load_audio(row['filename'])
        label = row['label']
        
        if self.transform:
            audio = self.transform(audio)
        
        return audio, label
    
    def __len__(self):
        return len(self.df)


class BirdModel(nn.Module):
    """鸟类声音分类模型"""
    
    def __init__(self, num_classes=100):
        super().__init__()
        self.backbone = torch.hub.load(
            'pytorch/vision', 
            'resnet50', 
            pretrained=True
        )
        self.backbone.fc = nn.Linear(2048, num_classes)
    
    def forward(self, x):
        return self.backbone(x)


def train_one_epoch(model, loader, optimizer, criterion):
    """训练一个 epoch"""
    model.train()
    total_loss = 0
    
    for x, y in loader:
        optimizer.zero_grad()
        pred = model(x)
        loss = criterion(pred, y)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    return total_loss / len(loader)
```

---

### 3. `integration_example.py`（集成示例）

```python
# -*- coding: utf-8 -*-
"""
==============================================================================
集成示例 - SpecAugment数据增强
==============================================================================

本文件展示如何将优化代码集成到 baseline 中
运行方式: python integration_example.py
==============================================================================
"""

# === 方式1: 使用装饰器（推荐）===

from specaugment_data_aug_patch import spec_augment_decorator

# 假设这是您的原始 baseline Dataset
class BirdDataset:
    def __init__(self, df):
        self.df = df
    
    def __getitem__(self, idx):
        # 原有代码保持不变
        row = self.df.iloc[idx]
        audio = load_audio(row['filename'])
        label = row['label']
        return audio, label

# 应用装饰器进行增强
@spec_augment_decorator
class AugmentedBirdDataset(BirdDataset):
    """增强版 Dataset - 原有代码不变，只添加新功能"""
    pass


# === 方式2: 运行时装饰 ===

from specaugment_data_aug_patch import spec_augment_decorator

# 在运行时应用装饰器
OriginalDataset = BirdDataset
AugmentedDataset = spec_augment_decorator(OriginalDataset)

# 现在可以使用增强版 Dataset
dataset = AugmentedDataset(df)


# === 方式3: 继承扩展 ===

from specaugment_data_aug_patch import spec_augment_decorator

class CustomBirdDataset(BirdDataset):
    """自定义 Dataset，继承并增强"""
    
    def __init__(self, df, augment=True):
        super().__init__(df)
        self.augment = augment

# 应用装饰器
CustomBirdDataset = spec_augment_decorator(CustomBirdDataset)


if __name__ == "__main__":
    print("✅ 集成示例加载成功")
    print("📖 请参考 INTEGRATION_GUIDE.md 获取详细说明")
```

---

### 4. `INTEGRATION_GUIDE.md`（集成指南）

```markdown
# SpecAugment数据增强 - 集成指南

## 📋 概述

| 项目 | 内容 |
|------|------|
| **优化方向** | SpecAugment数据增强 |
| **类别** | data_augmentation |
| **集成模式** | decorator |
| **难度** | easy |

## 📁 文件说明

| 文件 | 说明 | 编码 |
|------|------|------|
| `specaugment_data_aug_patch.py` | **新增优化代码**（在 baseline 基础上增量添加） | UTF-8 |
| `baseline_backup.py` | **原始 baseline 代码备份**（用于对比） | UTF-8 |
| `integration_example.py` | **集成示例代码**（展示如何使用） | UTF-8 |
| `*_test.py` | **测试代码**（验证优化效果） | UTF-8 |

## ⚠️ 重要说明

### 1. 绝不修改 baseline 代码
- `specaugment_data_aug_patch.py` **只包含新增的优化代码**
- **不包含**任何 baseline 原有代码
- 使用**增量修改模式**（装饰器/继承/包装）

### 2. 编码说明
所有文件均使用 **UTF-8 编码**，确保中文注释正常显示。

## 🎯 插入点

### dataset.py
- **位置**: `BirdDataset.__getitem__`
- **说明**: 在数据加载时应用增强

## 📝 集成步骤

1. 将 `specaugment_data_aug_patch.py` 复制到项目目录
2. 在 `dataset.py` 顶部导入: `from specaugment_data_aug_patch import spec_augment_decorator`
3. 在 `BirdDataset` 类定义前添加 `@spec_augment_decorator`
4. 运行测试验证增强是否生效

## ✅ 验证

```bash
python -c "from specaugment_data_aug_patch import spec_augment_decorator; print('OK')"
```

**预期输出**: `OK`
```

---

## 关键特性

### ✅ 绝不重写 baseline
- `*_patch.py` **只包含优化代码**
- `baseline_backup.py` **完整备份原始代码**
- 两者**绝不混合**

### ✅ UTF-8 编码
- 所有文件头部有 `# -*- coding: utf-8 -*-`
- 中文注释正常显示
- 无乱码问题

### ✅ 清晰区分
- 文件命名明确标识用途
- README 中有详细的文件说明表
- 每个文件头部有用途说明
