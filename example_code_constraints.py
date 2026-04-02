"""
代码约束系统使用示例

演示如何使用 EngineerAgentV2 和 CodeConstraintValidator
确保生成的代码严格绑定 baseline，不修改原有代码
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))


def demo_engineer_v2():
    """演示 EngineerAgentV2 代码生成"""
    print("="*70)
    print("示例1: EngineerAgentV2 - 严格绑定 Baseline 的代码生成")
    print("="*70)
    
    # 模拟 baseline 代码
    baseline_code = '''
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class BirdDataset(Dataset):
    def __init__(self, df, transform=None):
        self.df = df
        self.transform = transform
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        audio = load_audio(row['filename'])
        label = row['label']
        
        if self.transform:
            audio = self.transform(audio)
        
        return audio, label
    
    def __len__(self):
        return len(self.df)

class BirdModel(nn.Module):
    def __init__(self, num_classes=100):
        super().__init__()
        self.backbone = torch.hub.load('pytorch/vision', 'resnet50', pretrained=True)
        self.backbone.fc = nn.Linear(2048, num_classes)
    
    def forward(self, x):
        return self.backbone(x)

def train_one_epoch(model, loader, optimizer, criterion):
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
'''
    
    # 模拟优化方向
    direction = {
        "name": "SpecAugment数据增强",
        "category": "data_augmentation",
        "target_module": "Dataset.__getitem__",
        "rationale": "通过时频掩码增强音频数据，提升泛化能力",
        "search_keywords": ["SpecAugment", "audio augmentation", "time mask"]
    }
    
    # 模拟 baseline 分析
    baseline_analysis = {
        "framework": "PyTorch",
        "data_pipeline": {
            "dataset_class": "BirdDataset",
            "transforms": [],
            "insertion_points": ["BirdDataset.__getitem__"]
        },
        "model_architecture": {
            "backbone": "ResNet50",
            "loss_function": "CrossEntropy"
        },
        "modules": ["BirdDataset", "BirdModel", "train_one_epoch"]
    }
    
    # 模拟搜索结果
    search_results = [
        {
            "title": "SpecAugment: A Simple Data Augmentation Method",
            "abstract": "Time and frequency masking for audio..."
        }
    ]
    
    print("\n📋 输入信息:")
    print(f"  优化方向: {direction['name']}")
    print(f"  目标模块: {direction['target_module']}")
    print(f"  Baseline Dataset: {baseline_analysis['data_pipeline']['dataset_class']}")
    
    print("\n📝 EngineerAgentV2 将使用以下策略:")
    print("  1. 分析插入点: BirdDataset.__getitem__")
    print("  2. 推荐模式: 装饰器模式")
    print("  3. 生成增量代码（不修改 baseline）")
    
    print("\n✅ 生成的代码将包含:")
    print("  - 装饰器函数: spec_augment_decorator")
    print("  - 增强方法: apply_spec_augment")
    print("  - 使用示例: 如何在 baseline 中应用")
    print("  - 集成指南: 详细的步骤说明")
    
    print("\n⚠️ 注意: 实际代码生成需要 LLM，这里仅展示流程")
    print("   运行实际代码: python example_enhanced_workflow.py")


def demo_code_validator():
    """演示代码约束验证"""
    print("\n" + "="*70)
    print("示例2: CodeConstraintValidator - 代码约束验证")
    print("="*70)
    
    baseline_code = '''
def train(model, loader, optimizer):
    model.train()
    for x, y in loader:
        pred = model(x)
        loss = criterion(pred, y)
        loss.backward()
        optimizer.step()
'''
    
    # 示例1: 合规代码（使用装饰器）
    good_code = '''
import functools

def augment_decorator(func):
    @functools.wraps(func)
    def wrapper(self, idx):
        data, label = func(self, idx)
        # 添加增强
        data = augment(data)
        return data, label
    return wrapper

# 使用: @augment_decorator
'''
    
    # 示例2: 违规代码（直接修改 baseline）
    bad_code = '''
def train(model, loader, optimizer):
    # 直接修改了 baseline 的 train 函数
    model.train()
    for x, y in loader:
        pred = model(x)
        # 修改了损失计算
        loss = new_fancy_loss(pred, y)  # 这是违规的！
        loss.backward()
        optimizer.step()
'''
    
    from core.code_constraints import validate_code
    
    print("\n📋 验证合规代码:")
    result1 = validate_code(good_code, baseline_code, strict_mode=False)
    print(f"  评分: {result1['score']:.0f}/100")
    print(f"  通过: {'✅' if result1['valid'] else '❌'}")
    if result1['recommendations']:
        print(f"  建议: {result1['recommendations'][0]}")
    
    print("\n📋 验证违规代码:")
    result2 = validate_code(bad_code, baseline_code, strict_mode=False)
    print(f"  评分: {result2['score']:.0f}/100")
    print(f"  通过: {'✅' if result2['valid'] else '❌'}")
    if result2['violations']:
        print(f"  违规: {result2['violations'][0]['message']}")


def demo_incremental_patterns():
    """演示增量修改模式"""
    print("\n" + "="*70)
    print("示例3: 增量修改模式代码示例")
    print("="*70)
    
    patterns = {
        "装饰器模式（数据增强）": '''
# augmentation_patch.py
from functools import wraps

def spec_augment_decorator(cls):
    """SpecAugment 数据增强装饰器"""
    original_getitem = cls.__getitem__
    
    @wraps(original_getitem)
    def new_getitem(self, idx):
        data, label = original_getitem(self, idx)
        data = self.apply_spec_augment(data)
        return data, label
    
    def apply_spec_augment(self, data):
        # 实现 SpecAugment
        return augmented_data
    
    cls.__getitem__ = new_getitem
    cls.apply_spec_augment = apply_spec_augment
    return cls

# 在 baseline 中使用:
# @spec_augment_decorator
# class MyDataset(BaseDataset):
#     pass
''',
        
        "继承扩展（修改损失）": '''
# loss_patch.py
import torch.nn as nn

class FocalLossWrapper(nn.Module):
    """包装 baseline 损失，添加 Focal 权重"""
    
    def __init__(self, base_criterion, gamma=2.0):
        super().__init__()
        self.base_criterion = base_criterion
        self.gamma = gamma
    
    def forward(self, inputs, targets):
        ce_loss = self.base_criterion(inputs, targets)
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma * ce_loss).mean()
        return focal_loss

# 在 baseline 中使用:
# base_criterion = nn.CrossEntropyLoss()
# criterion = FocalLossWrapper(base_criterion, gamma=2.0)
''',
        
        "函数包装（训练策略）": '''
# training_patch.py

def create_wrapped_trainer(base_train_fn):
    """包装训练函数，添加学习率 warmup"""
    
    def wrapped_train(model, loader, optimizer, epoch, **kwargs):
        # 前置处理
        if epoch < 5:
            for param_group in optimizer.param_groups:
                param_group['lr'] *= (epoch + 1) / 5
        
        # 调用原始训练
        result = base_train_fn(model, loader, optimizer, epoch, **kwargs)
        
        return result
    
    return wrapped_train

# 在 baseline 中使用:
# train_one_epoch = create_wrapped_trainer(original_train_one_epoch)
'''
    }
    
    for name, code in patterns.items():
        print(f"\n📦 {name}:")
        print(code)


def demo_integration_guide():
    """演示集成指南结构"""
    print("\n" + "="*70)
    print("示例4: 生成的集成指南结构")
    print("="*70)
    
    guide = {
        "overview": {
            "direction": "SpecAugment数据增强",
            "category": "data_augmentation",
            "integration_mode": "decorator",
            "difficulty": "easy"
        },
        "insertion_points": [
            {
                "file": "dataset.py",
                "location": "BirdDataset.__getitem__",
                "description": "在数据加载时应用增强"
            }
        ],
        "integration_steps": [
            "1. 将 augmentation_patch.py 复制到项目目录",
            "2. 在 dataset.py 顶部导入: from augmentation_patch import spec_augment_decorator",
            "3. 在 BirdDataset 类定义前添加 @spec_augment_decorator",
            "4. 运行测试验证增强是否生效"
        ],
        "alternatives": [
            "继承扩展: class AugmentedBirdDataset(BirdDataset)",
            "回调注入: 在 DataLoader 中使用 collate_fn"
        ],
        "verification": {
            "test_commands": ["python -c 'from dataset import BirdDataset; print(\"OK\")'"],
            "expected_output": "OK"
        }
    }
    
    print("\n📖 集成指南内容:")
    print(f"  优化方向: {guide['overview']['direction']}")
    print(f"  集成模式: {guide['overview']['integration_mode']}")
    print(f"  难度: {guide['overview']['difficulty']}")
    
    print(f"\n  集成步骤:")
    for step in guide['integration_steps']:
        print(f"    {step}")
    
    print(f"\n  备选方案:")
    for alt in guide['alternatives']:
        print(f"    - {alt}")


async def main():
    """主函数"""
    print("\n" + "🛡️" * 35)
    print("  EvoAgentX 代码约束系统演示")
    print("🛡️" * 35)
    
    demo_engineer_v2()
    demo_code_validator()
    demo_incremental_patterns()
    demo_integration_guide()
    
    print("\n" + "="*70)
    print("✅ 演示完成")
    print("="*70)
    print("""
核心要点:
1. EngineerAgentV2 强制使用增量修改模式（装饰器/继承/包装）
2. CodeConstraintValidator 三层验证确保不修改 baseline
3. 生成的代码包含详细的集成指南和使用示例
4. 保存的文件结构清晰，包含 baseline 备份

使用建议:
- 总是查看 INTEGRATION_GUIDE.md 了解如何集成
- 先运行测试代码验证功能
- 保留 baseline_backup.py 以便回滚
- 根据评分和建议改进代码

文档:
- CODE_CONSTRAINTS.md: 详细约束说明和最佳实践
- example_enhanced_workflow.py: 完整工作流示例
""")


if __name__ == "__main__":
    asyncio.run(main())
