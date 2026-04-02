"""
增强版工作流使用示例

演示如何使用新的防跑偏机制：
1. BaselineAnalyzer - 深度代码分析
2. SmartEDA - 智能数据探索
3. ConstraintAgent - 约束检查
4. 增强版 Supervisor - 基于分析结果确定方向
"""

import asyncio
from pathlib import Path

# 确保路径正确
import sys
sys.path.insert(0, str(Path(__file__).parent))

from agents import create_llm
from core.enhanced_workflow import run_enhanced_workflow


async def demo_baseline_analysis():
    """演示 Baseline 分析"""
    print("="*70)
    print("示例1: BaselineAnalyzer - 深度代码分析")
    print("="*70)
    
    # 示例代码
    sample_code = '''
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import pandas as pd

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

class BirdModel(nn.Module):
    def __init__(self, num_classes=100):
        super().__init__()
        self.backbone = torch.hub.load('pytorch/vision', 'resnet50', pretrained=True)
        self.backbone.fc = nn.Linear(2048, num_classes)
    
    def forward(self, x):
        return self.backbone(x)

def train():
    dataset = BirdDataset(df)
    loader = DataLoader(dataset, batch_size=32, num_workers=4)
    
    model = BirdModel()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    
    for epoch in range(10):
        for x, y in loader:
            pred = model(x)
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
'''
    
    from agents.v2.baseline_analyzer import BaselineAnalyzer
    
    llm = create_llm(temperature=0.3)
    analyzer = BaselineAnalyzer(llm)
    
    analysis = analyzer.analyze(sample_code)
    
    print("\n分析结果:")
    print(f"  框架: {analysis['framework']}")
    print(f"  数据流程: {analysis['data_pipeline'].get('dataset_class')}")
    print(f"  Backbone: {analysis['model_architecture'].get('backbone')}")
    print(f"  损失函数: {analysis['model_architecture'].get('loss_function')}")
    print(f"  优化器: {analysis['training_config'].get('optimizer')}")
    print(f"\n  检测到的优化机会:")
    for op in analysis['optimization_opportunities']:
        print(f"    - {op['location']}: {op['suggestion']}")


async def demo_constraint_check():
    """演示约束检查"""
    print("\n" + "="*70)
    print("示例2: ConstraintAgent - 约束检查")
    print("="*70)
    
    # 测试方向 - 一个合规，一个违规
    test_directions = [
        {
            "name": "SpecAugment数据增强",
            "rationale": "通过时频掩码增强音频数据",
            "target_module": "Dataset.__getitem__",
            "search_keywords": ["SpecAugment", "audio augmentation"]
        },
        {
            "name": "添加ResNet101骨干网络",
            "rationale": "使用更深的网络提升特征提取能力",
            "target_module": "Model.backbone",
            "search_keywords": ["ResNet101", "deep learning"]
        },
        {
            "name": "优化推理速度",
            "rationale": "通过模型剪枝减少计算量",
            "target_module": "inference",
            "search_keywords": ["pruning", "speed"]
        }
    ]
    
    from agents.v2.constraint_agent import ConstraintAgent
    
    llm = create_llm(temperature=0.3)
    checker = ConstraintAgent(llm)
    
    # 模拟 baseline 分析
    baseline_analysis = {
        "modules": ["BirdDataset", "BirdModel", "train"],
        "data_pipeline": {"dataset_class": "BirdDataset"},
        "model_architecture": {"backbone": "ResNet50"}
    }
    
    result = checker.validate_directions(
        directions=test_directions,
        baseline_analysis=baseline_analysis
    )
    
    print(f"\n检查结果:")
    print(f"  总方向: {len(test_directions)}")
    print(f"  通过: {len(result['valid_directions'])}")
    print(f"  拒绝: {len(result['rejected_directions'])}")
    
    print(f"\n  有效方向:")
    for d in result['valid_directions']:
        print(f"    ✅ {d.get('name')}")
    
    print(f"\n  被拒绝方向:")
    for r in result['rejected_directions']:
        print(f"    ❌ {r['direction'].get('name')}")
        for reason in r['reasons'][:2]:
            print(f"       - {reason}")


async def demo_smart_eda():
    """演示智能 EDA"""
    print("\n" + "="*70)
    print("示例3: SmartEDA - 智能数据探索")
    print("="*70)
    
    from data.smart_eda import SmartEDA
    
    # 创建一个临时测试目录结构
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建模拟数据
        test_dir = Path(tmpdir) / "test_data"
        test_dir.mkdir()
        
        # 创建 CSV 标签文件
        import pandas as pd
        labels = pd.DataFrame({
            'filename': [f'audio_{i}.ogg' for i in range(100)],
            'label': ['class_A'] * 80 + ['class_B'] * 20  # 不平衡
        })
        labels.to_csv(test_dir / "labels.csv", index=False)
        
        eda = SmartEDA(max_sample_size=50)
        report = eda.explore(str(test_dir))
        
        print(f"\nEDA 结果:")
        print(f"  数据类型: {report.data_type}")
        print(f"  文件数: {report.file_count}")
        
        if report.insights:
            print(f"\n  洞察:")
            for insight in report.insights:
                print(f"    - {insight}")
        
        if report.issues:
            print(f"\n  发现的问题:")
            for issue in report.issues[:3]:
                print(f"    - {issue.get('message')}")
        
        if report.optimization_suggestions:
            print(f"\n  优化建议:")
            for sugg in report.optimization_suggestions[:3]:
                print(f"    - {sugg.get('category')}: {sugg.get('suggestion')}")


async def demo_full_workflow():
    """演示完整工作流"""
    print("\n" + "="*70)
    print("示例4: 完整增强版工作流")
    print("="*70)
    
    # 示例 baseline 代码
    sample_code = '''
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class AudioDataset(Dataset):
    def __init__(self, df):
        self.df = df
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        audio = load_audio(row['filename'])
        label = row['label']
        return audio, label

class AudioModel(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.backbone = torch.hub.load('pytorch/vision', 'resnet50', pretrained=True)
        self.backbone.fc = nn.Linear(2048, num_classes)
    
    def forward(self, x):
        return self.backbone(x)

def train():
    dataset = AudioDataset(df)
    loader = DataLoader(dataset, batch_size=32)
    
    model = AudioModel(num_classes=100)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    
    for epoch in range(10):
        for x, y in loader:
            pred = model(x)
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
'''
    
    # 示例赛题 HTML
    sample_html = """
    <h1>BirdCLEF 2026</h1>
    <p>鸟类声音识别竞赛</p>
    <p>评估指标: Macro AUC</p>
    <p>数据: 音频文件 (.ogg)</p>
    """
    
    print("\n工作流配置:")
    print(f"  项目: BirdCLEF Demo")
    print(f"  代码长度: {len(sample_code)} 字符")
    print(f"  启用约束检查: True")
    
    print("\n⚠️ 注意: 完整工作流需要有效的 LLM 和较长的运行时间")
    print("   这里仅展示结构，实际运行请使用:")
    print("   ```python")
    print("   results = await run_enhanced_workflow(")
    print("       llm=llm,")
    print("       project_name='birdclef',")
    print("       html_content=html_content,")
    print("       code_content=code_content,")
    print("       data_path='./data/train',")
    print("       instruction='优化音频分类模型',")
    print("       enable_constraint_check=True")
    print("   )")
    print("   ```")


async def main():
    """主函数"""
    print("\n" + "🚀" * 35)
    print("  EvoAgentX 增强版工作流演示")
    print("🚀" * 35)
    
    # 运行各个演示
    await demo_baseline_analysis()
    await demo_constraint_check()
    await demo_smart_eda()
    await demo_full_workflow()
    
    print("\n" + "="*70)
    print("✅ 演示完成")
    print("="*70)
    print("""
使用建议:
1. BaselineAnalyzer: 在传入代码后自动分析，提取架构信息
2. ConstraintAgent: 在 Supervisor 后自动校验方向
3. SmartEDA: 传入数据路径自动探索
4. 增强版工作流: 使用 run_enhanced_workflow() 一键执行

配置文件示例 (evo_config.yaml):
```yaml
features:
  constraint_check: true      # 启用约束检查
  baseline_analysis: true     # 启用baseline分析
  smart_eda: true             # 启用智能EDA

agent:
  supervisor_max_directions: 3
  constraint_strictness: "medium"  # low/medium/high
```
""")


if __name__ == "__main__":
    asyncio.run(main())
