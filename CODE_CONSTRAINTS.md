# 代码约束系统 - 严格绑定 Baseline

## 概述

为了确保生成的代码**绝对不修改 baseline**，我们实现了多层约束验证系统。

## 🛡️ 三层防护机制

```
┌─────────────────────────────────────────────────────────────┐
│  第一层: EngineerAgentV2 生成策略                            │
│  - 强制使用增量修改模式（装饰器/继承/包装）                    │
│  - 禁止生成修改 baseline 的代码                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  第二层: 内部验证                                            │
│  - 检查增量修改模式                                          │
│  - 验证语法正确性                                            │
│  - 检查 API 兼容性                                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  第三层: CodeConstraintValidator                            │
│  - 检测禁止的修改模式                                        │
│  - 对比 baseline 检查重名                                    │
│  - 检查导入冲突                                              │
│  - 评分系统                                                  │
└─────────────────────────────────────────────────────────────┘
```

## 🚫 禁止的修改模式

### 1. 直接修改 baseline 代码
```python
# ❌ 禁止：直接修改 baseline 函数
def train(model, loader):  # baseline 原有函数
    # 新代码直接修改了这个函数的实现
    loss = new_loss_function(output, target)  # 这是禁止的！

# ✅ 正确：使用装饰器
@loss_decorator
def train(model, loader):
    pass  # 原有代码不变
```

### 2. 修改函数签名
```python
# ❌ 禁止：改变函数参数
def train(model, loader, new_param):  # 添加了新参数
    pass

# ✅ 正确：保持签名，通过配置传入
def train(model, loader, config=None):
    new_param = config.get('new_param') if config else None
```

### 3. 破坏 API 兼容性
```python
# ❌ 禁止：删除或重命名
class NewModel:  # 与 baseline 的 Model 重名
    pass

# ✅ 正确：继承扩展
class AugmentedModel(BaseModel):
    pass
```

## ✅ 推荐的增量修改模式

### 模式1：装饰器模式（数据增强）

```python
# augmentation_patch.py
from functools import wraps

def spec_augment_decorator(cls):
    """SpecAugment 数据增强装饰器"""
    original_getitem = cls.__getitem__
    
    @wraps(original_getitem)
    def new_getitem(self, idx):
        # 1. 调用原始方法获取数据
        data, label = original_getitem(self, idx)
        
        # 2. 应用增强
        data = self.apply_spec_augment(data)
        
        return data, label
    
    # 3. 添加增强方法
    def apply_spec_augment(self, data):
        # SpecAugment 实现
        return augmented_data
    
    cls.__getitem__ = new_getitem
    cls.apply_spec_augment = apply_spec_augment
    
    return cls

# 使用方式（添加到 baseline 文件末尾）:
# @spec_augment_decorator
# class MyDataset(BaseDataset):
#     pass
```

**优点**：
- 完全不修改原有代码
- 可以动态应用/移除
- 保持原有类名和接口

### 模式2：继承扩展（修改损失）

```python
# loss_patch.py
import torch.nn as nn

class FocalLossWrapper(nn.Module):
    """
    包装 baseline 的损失函数，添加 Focal 权重
    
    使用方式：替换原有的损失函数实例化
    """
    
    def __init__(self, base_criterion, gamma=2.0, alpha=None):
        super().__init__()
        self.base_criterion = base_criterion
        self.gamma = gamma
        self.alpha = alpha
    
    def forward(self, inputs, targets):
        # 1. 计算基础损失
        ce_loss = self.base_criterion(inputs, targets)
        
        # 2. 计算 Focal 权重
        pt = torch.exp(-ce_loss)
        focal_weight = (1 - pt) ** self.gamma
        
        # 3. 应用权重
        focal_loss = focal_weight * ce_loss
        
        if self.alpha is not None:
            focal_loss = self.alpha * focal_loss
        
        return focal_loss.mean()

# 使用方式:
# base_criterion = nn.CrossEntropyLoss()
# criterion = FocalLossWrapper(base_criterion, gamma=2.0)
```

**优点**：
- 完全兼容原有接口
- 可以链式包装多个损失
- 易于参数调整

### 模式3：函数包装（训练循环）

```python
# training_patch.py

def create_wrapped_trainer(base_train_fn):
    """
    创建包装后的训练函数
    
    Args:
        base_train_fn: baseline 原有的训练函数
        
    Returns:
        包装后的训练函数
    """
    
    def wrapped_train(model, loader, optimizer, epoch, **kwargs):
        # 1. 前置处理：学习率 warmup
        if epoch < 5:
            for param_group in optimizer.param_groups:
                param_group['lr'] *= (epoch + 1) / 5
        
        # 2. 调用原始训练函数
        result = base_train_fn(model, loader, optimizer, epoch, **kwargs)
        
        # 3. 后置处理：记录额外指标
        if isinstance(result, dict):
            result['custom_metric'] = calculate_custom_metric(model)
        
        return result
    
    return wrapped_train

# 使用方式:
# original_train = train_one_epoch
# train_one_epoch = create_wrapped_trainer(original_train)
```

**优点**：
- 无需修改训练循环代码
- 可以组合多个包装器
- 易于调试和回滚

### 模式4：回调注入（训练过程）

```python
# callback_patch.py

class CustomTrainingCallback:
    """
    自定义训练回调
    
    在训练的不同阶段插入自定义逻辑
    """
    
    def on_epoch_begin(self, epoch, logs=None):
        """每个 epoch 开始时调用"""
        pass
    
    def on_batch_end(self, batch, logs=None):
        """每个 batch 结束时调用"""
        # 例如：梯度裁剪
        if logs and 'grad_norm' in logs:
            torch.nn.utils.clip_grad_norm_(
                logs['model'].parameters(), 
                max_norm=1.0
            )
    
    def on_epoch_end(self, epoch, logs=None):
        """每个 epoch 结束时调用"""
        pass

# 使用方式（如果 baseline 支持回调）:
# callbacks = [CustomTrainingCallback()]
# trainer = Trainer(callbacks=callbacks)
```

## 🔍 代码约束验证

### 验证维度

```python
from core.code_constraints import validate_code

result = validate_code(
    generated_code=generated_code,
    baseline_code=baseline_code,
    strict_mode=False  # True = 任何警告都视为失败
)

# 结果包含:
# - valid: 是否通过验证
# - score: 代码质量评分 (0-100)
# - violations: 违规列表
# - recommendations: 改进建议
```

### 验证规则

| 规则 | 级别 | 说明 |
|------|------|------|
| direct_modification | ERROR | 直接修改 baseline 代码 |
| signature_change | ERROR | 修改函数签名 |
| class_override | ERROR | 类名与 baseline 重名 |
| function_override | WARNING | 函数名与 baseline 重名 |
| global_state | WARNING | 修改全局变量 |
| import_conflict | WARNING | 导入可能冲突的库 |
| hardcoded_path | WARNING | 硬编码路径 |

### 评分系统

```
基础分: 100
- ERROR: -20 分
- WARNING: -10 分
- INFO: -2 分

增量模式加分:
- 装饰器: +10
- 继承: +10
- 包装器: +10
- 回调: +10

最终得分 = 基础分 * 0.6 + 模式分 * 0.4
```

## 📋 使用示例

### 完整代码生成流程

```python
from agents.v2.engineer_agent_v2 import EngineerAgentV2
from core.code_constraints import validate_code

# 1. 创建 Engineer
engineer = EngineerAgentV2(llm)

# 2. 生成代码
code_result = engineer.generate_code_with_baseline(
    direction={
        "name": "SpecAugment数据增强",
        "category": "data_augmentation",
        "target_module": "Dataset.__getitem__"
    },
    baseline_analysis=baseline_analysis,
    search_results=search_results,
    original_code=baseline_code
)

# 3. 额外验证（可选）
validation = validate_code(
    code_result["main_code"],
    baseline_code,
    strict_mode=True
)

if validation["valid"]:
    print(f"✅ 验证通过，评分: {validation['score']:.0f}/100")
else:
    print("❌ 验证失败:")
    for v in validation["violations"]:
        print(f"  - [{v['level']}] {v['message']}")
```

## ⚙️ 配置

```yaml
# evo_config.yaml

features:
  strict_code_validation: true  # 启用严格验证

agent:
  engineer_code_style: "incremental"  # 强制增量模式
  
workflow:
  enable_code_constraint_check: true  # 启用约束检查
  code_validation_strict_mode: false  # 是否严格模式
```

## 🎯 最佳实践

1. **总是使用增量模式**：装饰器 > 继承 > 包装 > 回调
2. **保持 API 兼容**：不修改函数签名，不删除功能
3. **明确集成位置**：提供具体的文件和行号
4. **提供多种集成方式**：主推荐 + 备选方案
5. **包含使用示例**：展示如何在 baseline 中使用

## 🚨 常见错误

### 错误1：直接复制 baseline 代码然后修改
```python
# ❌ 错误
class Dataset:  # 与 baseline 重名
    def __getitem__(self, idx):
        # 复制了 baseline 的代码然后修改
        ...

# ✅ 正确
@augment_decorator  # 使用装饰器增强
class Dataset(BaseDataset):
    pass
```

### 错误2：修改全局配置
```python
# ❌ 错误
BATCH_SIZE = 64  # 修改了全局变量

# ✅ 正确
def train(config):
    batch_size = config.get('batch_size', 64)  # 通过参数传入
```

### 错误3：假设 baseline 结构
```python
# ❌ 错误
model.backbone.layer4[0].conv1.weight  # 假设具体的层结构

# ✅ 正确
model.get_backbone()  # 使用公共 API
```
