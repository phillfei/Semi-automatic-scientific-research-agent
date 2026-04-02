"""
工程师Agent V2 - 严格绑定 Baseline 的代码生成器

核心原则：
1. 绝不修改 baseline 原有代码
2. 只使用增量修改模式（装饰器、继承、函数包装）
3. 代码必须能在 baseline 中直接运行
4. 提供详细的集成位置和调用方式
"""

import os
import re
import json
import ast
from typing import Dict, List, Optional, Any, Tuple, ClassVar
from datetime import datetime
from pathlib import Path

from evoagentx.agents import Agent
from evoagentx.tools import PythonInterpreterToolkit, FileToolkit
from utils.agent_logger import get_agent_logger, log_agent_method
from utils.file_encoding import write_python_file


class EngineerAgentV2(Agent):
    """
    工程师Agent V2 - 严格绑定 Baseline
    
    生成策略：
    1. 装饰器模式 - 增强现有函数
    2. 继承扩展 - 扩展现有类
    3. 函数包装 - 包装现有调用
    4. 配置注入 - 通过配置文件修改行为
    
    禁止策略：
    - 直接修改 baseline 源代码
    - 修改函数签名
    - 修改类继承关系
    - 删除或重命名现有功能
    """
    
    # 允许的修改模式
    ALLOWED_PATTERNS: ClassVar[Dict[str, Any]] = {
        "decorator": {
            "name": "装饰器模式",
            "description": "使用装饰器增强现有函数",
            "use_case": "数据增强、日志记录、性能监控",
            "example": """
@augment_decorator
class MyDataset(BaseDataset):
    pass
"""
        },
        "inheritance": {
            "name": "继承扩展",
            "description": "继承基类并覆盖特定方法",
            "use_case": "修改数据加载、自定义损失",
            "example": """
class AugmentedDataset(BaseDataset):
    def __getitem__(self, idx):
        data = super().__getitem__(idx)
        return self.augment(data)
"""
        },
        "wrapper": {
            "name": "函数包装",
            "description": "包装现有函数调用",
            "use_case": "修改损失计算、自定义优化步骤",
            "example": """
def new_forward(model, x):
    output = model.forward(x)
    return post_process(output)
"""
        },
        "callback": {
            "name": "回调注入",
            "description": "通过回调机制插入代码",
            "use_case": "训练过程中的自定义操作",
            "example": """
class CustomCallback:
    def on_batch_end(self, batch, loss):
        # 自定义逻辑
        pass
"""
        }
    }
    
    def __init__(self, llm):
        super().__init__(
            name="EngineerV2",
            description="严格绑定Baseline的代码生成器，使用增量修改模式",
            llm=llm,
            system_prompt="""你是代码生成专家，负责基于baseline 代码生成优化代码。

## 核心原则（必须遵守）

### 1. 绝不修改 Baseline 原有代码
- 禁止修改 baseline 的任何函数/类
- 禁止修改函数签名
- 禁止修改类继承关系
- 禁止删除或重命名现有功能

### 2. 只使用增量修改模式
- 装饰器模式：增强现有函数
- 继承扩展：扩展现有类
- 函数包装：包装现有调用
- 回调注入：通过回调插入代码

### 3. 代码必须可运行
- 所有导入必须在 baseline 环境中可用
- 不能与 baseline 的依赖版本冲突
- 必须提供使用示例

### 4. 明确的集成说明
- 必须指定插入文件和行号范围
- 必须提供调用示例
- 必须说明与 baseline 的交互方式

## 代码生成模板

### 模板1：装饰器模式（数据增强）
```python
# 文件: augmentation_patch.py
# 集成位置: 在原有Dataset 类定义前导入

def augment_decorator(cls):
    '''数据增强装饰器'''
    original_getitem = cls.__getitem__
    
    def new_getitem(self, idx):
        data, label = original_getitem(self, idx)
        # 添加增强逻辑
        data = self.apply_augmentation(data)
        return data, label
    
    cls.__getitem__ = new_getitem
    return cls

# 使用方式（添加到 baseline 文件末尾）:
# @augment_decorator
# class MyDataset(BaseDataset):
#     def apply_augmentation(self, data):
#         # 增强逻辑
#         return augmented_data
```

### 模板2：继承扩展（修改损失）
```python
# 文件: loss_patch.py
# 集成位置: 替换 baseline 中的损失函数实例化

class FocalLossWrapper(BaseLoss):
    '''在baseline 损失基础上添加Focal 权重'''
    
    def __init__(self, base_loss, gamma=2.0):
        super().__init__()
        self.base_loss = base_loss
        self.gamma = gamma
    
    def forward(self, pred, target):
        loss = self.base_loss(pred, target)
        # 添加 focal 权重
        pt = torch.exp(-loss)
        focal_loss = ((1 - pt) ** self.gamma * loss).mean()
        return focal_loss

# 使用方式:
# base_criterion = nn.CrossEntropyLoss()
# criterion = FocalLossWrapper(base_criterion, gamma=2.0)
```

### 模板3：函数包装（训练循环）
```python
# 文件: training_patch.py
# 集成位置: 替换 baseline 中的 train_one_epoch 调用

def create_wrapped_trainer(base_train_fn):
    '''包装训练函数，添加学习率 warmup'''
    
    def wrapped_train(model, loader, optimizer, epoch):
        # 前置处理：warmup
        if epoch < 5:
            for param_group in optimizer.param_groups:
                param_group['lr'] *= (epoch + 1) / 5
        
        # 调用原始训练
        result = base_train_fn(model, loader, optimizer, epoch)
        
        return result
    
    return wrapped_train

# 使用方式:
# train_fn = create_wrapped_trainer(original_train_one_epoch)
```

## 禁止事项

1. 不要假设 baseline 中不存在的API
2. 不要使用与 baseline 冲突的库版本
3. 不要修改全局状态（除非通过配置）
4. 不要改变数据流的基本结构

## 质量检查清单

生成代码后，确认：
- [ ] 可以在不修改 baseline 的情况下使用
- [ ] 所有导入都有明确的来源
- [ ] 提供3种以上的集成方式
- [ ] 包含详细的中文注释
- [ ] 包含使用示例"""
        )
        self.logger = get_agent_logger()
        self.code_toolkit = PythonInterpreterToolkit()
        self.file_toolkit = FileToolkit()
    
    @log_agent_method("name")
    def generate_code_with_baseline(
        self,
        direction: Dict,
        baseline_analysis: Dict,
        search_results: List[Dict],
        original_code: str = ""
    ) -> Dict:
        """
        主入口：基于 baseline 生成优化代码
        
        Args:
            direction: 优化方向信息
            baseline_analysis: baseline 分析结果
            search_results: 搜索结果
            original_code: 原始代码
            
        Returns:
            {
                "main_code": "主代码",
                "test_code": "测试代码",
                "integration_guide": "集成指南",
                "validation": "验证结果"
            }
        """
        print(f"\n👨‍💻 EngineerV2: 生成代码 - {direction.get('name', 'Unknown')}")
        
        # 1. 分析插入点
        insertion_info = self._analyze_insertion_point(
            direction, baseline_analysis
        )
        print(f"  📍 插入点: {insertion_info.get('location', 'Unknown')}")
        print(f"  🔧 推荐模式: {insertion_info.get('recommended_pattern', 'Unknown')}")
        
        # 2. 提取 baseline API 信息
        api_info = self._extract_api_info(original_code, insertion_info)
        
        # 3. 构建增强提示词
        prompt = self._build_generation_prompt(
            direction=direction,
            insertion_info=insertion_info,
            api_info=api_info,
            search_results=search_results,
            baseline_analysis=baseline_analysis
        )
        
        # 4. 调用 LLM 生成代码
        print(f"  📝 生成代码...")
        generated = self.llm.generate(prompt=prompt)
        
        # 5. 解析生成的代码
        main_code = self._extract_code_block(generated, "python")
        
        # 6. 生成测试代码
        test_code = self._generate_test_code(
            direction, main_code, api_info
        )
        
        # 7. 生成集成指南
        integration_guide = self._generate_integration_guide(
            direction, insertion_info, api_info, main_code
        )
        
        # 8. 验证代码
        validation = self._validate_code(main_code, original_code)
        
        print(f"  ✅ 代码生成完成")
        print(f"     代码行数: {len(main_code.split(chr(10)))}")
        print(f"     验证结果: {'通过' if validation.get('valid') else '需检查'}")
        
        return {
            "main_code": main_code,
            "test_code": test_code,
            "integration_guide": integration_guide,
            "validation": validation,
            "insertion_info": insertion_info,
            "api_info": api_info
        }
    
    def _analyze_insertion_point(
        self,
        direction: Dict,
        baseline_analysis: Dict
    ) -> Dict:
        """分析最佳插入点"""
        target_module = direction.get("target_module", "")
        category = direction.get("category", "")
        
        # 获取 baseline 的数据流程
        data_pipeline = baseline_analysis.get("data_pipeline", {})
        model_arch = baseline_analysis.get("model_architecture", {})
        training_config = baseline_analysis.get("training_config", {})
        
        insertion_info = {
            "location": target_module,
            "category": category,
            "recommended_pattern": "inheritance",  # 默认
            "baseline_modules": baseline_analysis.get("modules", []),
            "alternatives": []
        }
        
        # 根据类别确定最佳模式
        if category == "data_augmentation":
            insertion_info["recommended_pattern"] = "decorator"
            insertion_info["insertion_file"] = "dataset.py"
            insertion_info["target_class"] = data_pipeline.get("dataset_class", "Dataset")
            insertion_info["target_method"] = "__getitem__"
            insertion_info["alternatives"] = ["inheritance", "callback"]
            
        elif category == "loss_function":
            insertion_info["recommended_pattern"] = "inheritance"
            insertion_info["insertion_file"] = "model.py"
            insertion_info["target_class"] = "Loss"
            insertion_info["baseline_loss"] = model_arch.get("loss_function", "CrossEntropy")
            insertion_info["alternatives"] = ["wrapper"]
            
        elif category == "training_strategy":
            insertion_info["recommended_pattern"] = "wrapper"
            insertion_info["insertion_file"] = "train.py"
            insertion_info["target_function"] = "train_one_epoch"
            insertion_info["alternatives"] = ["callback"]
            
        elif category == "post_processing":
            insertion_info["recommended_pattern"] = "wrapper"
            insertion_info["insertion_file"] = "inference.py"
            insertion_info["target_function"] = "predict"
            insertion_info["alternatives"] = ["decorator"]
        
        return insertion_info
    
    def _extract_api_info(
        self,
        original_code: str,
        insertion_info: Dict
    ) -> Dict:
        """提取 baseline API 信息"""
        api_info = {
            "imports": [],
            "classes": [],
            "functions": [],
            "signatures": {}
        }
        
        if not original_code:
            return api_info
        
        # 提取导入语句
        import_pattern = r'^(import|from)\s+.+$'
        api_info["imports"] = re.findall(import_pattern, original_code, re.MULTILINE)
        
        # 提取类定义
        class_pattern = r'^class\s+(\w+)\s*\(?'
        api_info["classes"] = re.findall(class_pattern, original_code, re.MULTILINE)
        
        # 提取函数定义
        func_pattern = r'^def\s+(\w+)\s*\('
        api_info["functions"] = re.findall(func_pattern, original_code, re.MULTILINE)
        
        # 提取目标函数的签名
        target = insertion_info.get("target_function") or insertion_info.get("target_method")
        if target:
            sig_pattern = rf'^def\s+{re.escape(target)}\s*\([^)]*\)'
            match = re.search(sig_pattern, original_code, re.MULTILINE)
            if match:
                api_info["signatures"][target] = match.group(0)
        
        return api_info
    
    def _build_generation_prompt(
        self,
        direction: Dict,
        insertion_info: Dict,
        api_info: Dict,
        search_results: List[Dict],
        baseline_analysis: Dict
    ) -> str:
        """构建代码生成提示词"""
        
        # 获取推荐的模式模板
        pattern_name = insertion_info.get("recommended_pattern", "inheritance")
        pattern_info = self.ALLOWED_PATTERNS.get(pattern_name, {})
        
        # 构建参考论文摘要
        papers_summary = ""
        for paper in search_results[:2]:
            papers_summary += f"- {paper.get('title', '')}: {paper.get('abstract', '')[:200]}...\n"
        
        prompt = f"""请基于以下信息生成优化代码。

## 优化方向

名称: {direction.get('name', 'Unknown')}
类别: {direction.get('category', 'Unknown')}
目标模块: {insertion_info.get('location', 'Unknown')}

选择理由:
{direction.get('rationale', '未提供')}

## Baseline 架构信息

框架: {baseline_analysis.get('framework', 'Unknown')}
数据流程: {baseline_analysis.get('data_pipeline', {})}
模型架构: {baseline_analysis.get('model_architecture', {})}

## 集成要求

**推荐模式**: {pattern_info.get('name', 'Unknown')}
**模式说明**: {pattern_info.get('description', '')}
**使用场景**: {pattern_info.get('use_case', '')}

**插入点信息**:
- 目标文件: {insertion_info.get('insertion_file', 'Unknown')}
- 目标类: {insertion_info.get('target_class', 'N/A')}
- 目标方法/函数: {insertion_info.get('target_method') or insertion_info.get('target_function', 'N/A')}
- API签名: {api_info.get('signatures', {})}

**可用 baseline API**:
- 类: {api_info.get('classes', [])[:5]}
- 函数: {api_info.get('functions', [])[:5]}

## 参考论文

{papers_summary}

## 生成要求

1. **使用 {pattern_name} 模式**生成代码
2. **绝不修改 baseline 原有代码**，只提供增量代码
3. 代码必须**直接可用**，包含完整导入语句
4. 提供**3种集成方式**（主推荐 + 2种备选）
5. 添加**详细中文注释**说明每个部分的作用
6. 提供**使用示例**

## 禁止事项

- 不要修改 baseline 的函数签名
- 不要删除或重命名 baseline 的类/函数
- 不要假设 baseline 中不存在的API
- 不要改变数据流的基本结构

## 输出格式

请按以下格式输出：

```python
# 文件: {direction.get('name', 'patch').lower().replace(' ', '_')}_patch.py
# 优化方向: {direction.get('name', 'Unknown')}
# 集成模式: {pattern_name}

[完整的 Python 代码]

# 使用示例:
# [展示如何在 baseline 中使用这段代码]
```

确保代码完整、可运行、有详细注释。"""
        
        return prompt
    
    def _generate_test_code(
        self,
        direction: Dict,
        main_code: str,
        api_info: Dict
    ) -> str:
        """生成测试代码"""
        direction_name = direction.get("name", "unknown")
        
        test_prompt = f"""为以下代码生成 pytest 测试用例：

优化方向: {direction_name}

代码:
```python
{main_code[:2000]}
```

要求:
1. 测试主要功能
2. 测试边界条件
3. 包含中文注释说明测试目的
4. 使用 pytest 框架

输出完整的测试代码。"""
        
        try:
            test_response = self.llm.generate(prompt=test_prompt)
            test_code = self._extract_code_block(test_response, "python")
            return test_code
        except Exception as e:
            self.logger.log_agent_error("EngineerV2", "generate_test", e)
            return f"# 测试代码生成失败: {e}"
    
    def _generate_integration_guide(
        self,
        direction: Dict,
        insertion_info: Dict,
        api_info: Dict,
        main_code: str
    ) -> Dict:
        """生成集成指南"""
        
        guide = {
            "overview": {
                "direction": direction.get("name"),
                "category": direction.get("category"),
                "integration_mode": insertion_info.get("recommended_pattern"),
                "difficulty": "medium"
            },
            "insertion_points": [
                {
                    "file": insertion_info.get("insertion_file", "unknown.py"),
                    "location": insertion_info.get("location", "Unknown"),
                    "description": f"在{insertion_info.get('target_class') or insertion_info.get('target_function', 'Unknown')} 中集成"
                }
            ],
            "integration_steps": [],
            "alternatives": [],
            "verification": {
                "test_commands": ["python -c 'import patch'"],
                "expected_output": "无错误"
            }
        }
        
        # 根据模式生成具体步骤
        pattern = insertion_info.get("recommended_pattern")
        
        if pattern == "decorator":
            guide["integration_steps"] = [
                "1. 将生成的代码保存为单独的 .py 文件",
                "2. 在baseline 的dataset 文件顶部导入装饰器",
                "3. 在Dataset 类定义前添加 @decorator",
                "4. 运行测试验证增强是否生效"
            ]
            guide["alternatives"] = [
                "继承扩展: 创建 AugmentedDataset 继承基类",
                "回调注入: 在 DataLoader 中使用 collate_fn"
            ]
            
        elif pattern == "inheritance":
            guide["integration_steps"] = [
                "1. 将生成的代码保存为 loss_patch.py",
                "2. 在baseline 的训练脚本中导入新的 Loss 类",
                "3. 替换原有的损失函数实例化",
                "4. 验证损失计算是否正确"
            ]
            guide["alternatives"] = [
                "包装器模式: 包装现有损失函数",
                "配置注入: 通过配置文件修改损失参数"
            ]
            
        elif pattern == "wrapper":
            guide["integration_steps"] = [
                "1. 将生成的代码保存为 train_patch.py",
                "2. 在训练脚本中导入包装函数",
                "3. 将原有的 train_one_epoch 函数传递给包装器",
                "4. 使用包装后的函数进行训练"
            ]
            guide["alternatives"] = [
                "回调注入: 使用 Trainer 回调机制",
                "装饰器模式: 装饰训练函数"
            ]
        
        return guide
    
    def _validate_code(self, code: str, original_code: str) -> Dict:
        """验证生成的代码"""
        validation = {
            "valid": True,
            "checks": {},
            "warnings": []
        }
        
        # 1. 语法检查
        try:
            ast.parse(code)
            validation["checks"]["syntax"] = "pass"
        except SyntaxError as e:
            validation["checks"]["syntax"] = f"fail: {e}"
            validation["valid"] = False
        
        # 2. 检查是否修改了 baseline（通过对比）
        if original_code:
            original_lines = set(original_code.split('\n'))
            new_lines = set(code.split('\n'))
            
            # 检查是否有大量相同代码（可能直接复制了 baseline）
            overlap = len(original_lines & new_lines)
            if overlap > len(original_lines) * 0.8:
                validation["warnings"].append("代码可能直接复制了 baseline，请确保是增量修改")
        
        # 3. 检查是否包含关键元素
        if "import" not in code:
            validation["warnings"].append("缺少导入语句")
        
        if "def " not in code and "class " not in code:
            validation["warnings"].append("缺少函数或类定义")
        
        # 4. 检查增量修改模式的使用
        patterns_found = []
        if "@" in code and "decorator" in code.lower():
            patterns_found.append("decorator")
        if "class " in code and "super()" in code:
            patterns_found.append("inheritance")
        if "wrapper" in code.lower() or "wrap" in code.lower():
            patterns_found.append("wrapper")
        
        if not patterns_found:
            validation["warnings"].append("未检测到明确的增量修改模式（装饰器/继承/包装）")
        
        validation["checks"]["patterns"] = patterns_found
        
        return validation
    
    def _extract_code_block(self, text: str, language: str = "python") -> str:
        """提取代码块"""
        # 查找 markdown 代码块
        pattern = rf'```{language}\s*(.*?)```'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # 如果没有代码块标记，尝试提取整个文本
        return text.strip()
    
    @log_agent_method("name")
    def save_generated_code(
        self,
        generated_items: List[Dict],
        output_dir: str = "./output",
        original_code: str = ""
    ) -> List[str]:
        """
        保存生成的代码（增量修改模式）
        
        保存结构：
        output/
        └── timestamp_direction/
            ├── {direction}_patch.py       # 主代码
            ├── {direction}_test.py        # 测试代码
            ├── INTEGRATION_GUIDE.md       # 集成指南
            ├── baseline_backup.py         # baseline 备份
            └── integration_example.py     # 集成示例
        """
        os.makedirs(output_dir, exist_ok=True)
        saved_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for i, item in enumerate(generated_items, 1):
            direction_name = item.get('direction', f'direction_{i}')
            direction_slug = direction_name.replace(' ', '_').replace('/', '_')[:30]
            
            project_dir = os.path.join(output_dir, f"{timestamp}_{i}_{direction_slug}")
            os.makedirs(project_dir, exist_ok=True)
            
            # 1. 保存主代码（增量优化代码，绝不包含 baseline 代码， UTF-8）
            patch_filename = f"{direction_slug}_patch.py"
            patch_path = os.path.join(project_dir, patch_filename)
            
            patch_content = f'''# -*- coding: utf-8 -*-
"""
==============================================================================
{direction_name} - 增量优化代码
==============================================================================

【重要说明】
1. 本文件只包含新增的优化代码，绝不包含原始 baseline 代码
2. 使用增量修改模式（装饰器/继承/包装），不修改原有代码
3. 集成方式: {item.get("insertion_info", {}).get("recommended_pattern", "unknown")}
4. 目标位置: {item.get("insertion_info", {}).get("location", "unknown")}

【使用方法】
1. 将此文件保存到您的项目目录
2. 按照 INTEGRATION_GUIDE.md 的说明集成到 baseline
3. 原始 baseline 备份在 baseline_backup.py
==============================================================================

"""

{item['main_code']}'''
            
            write_python_file(patch_path, patch_content, ensure_utf8_header=False)
            saved_files.append(patch_path)
            
            # 2. 保存集成指南（JSON格式 - UTF-8）
            guide_path = os.path.join(project_dir, "INTEGRATION_GUIDE.json")
            with open(guide_path, 'w', encoding='utf-8') as f:
                json.dump(item['integration_guide'], f, indent=2, ensure_ascii=False)
            saved_files.append(guide_path)
            
            # 3. 保存集成指南（Markdown格式 - UTF-8）
            readme_path = os.path.join(project_dir, "INTEGRATION_GUIDE.md")
            readme_content = self._generate_readme(item, direction_name, patch_filename)
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            saved_files.append(readme_path)
            
            # 4. 保存测试代码（UTF-8）
            test_filename = f"{direction_slug}_test.py"
            test_path = os.path.join(project_dir, test_filename)
            test_content = f'''# -*- coding: utf-8 -*-
"""
测试代码 - {direction_name}

运行方式: pytest {test_filename} -v
编码: UTF-8
"""

{item['test_code']}'''
            write_python_file(test_path, test_content, ensure_utf8_header=False)
            saved_files.append(test_path)
            
            # 5. 备份原始 baseline 代码（UTF-8，用于对比）
            if original_code:
                backup_path = os.path.join(project_dir, "baseline_backup.py")
                backup_content = f'''# -*- coding: utf-8 -*-
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
优化代码在 {patch_filename} 中，不要直接修改此文件
==============================================================================

"""

{original_code}'''
                write_python_file(backup_path, backup_content, ensure_utf8_header=False)
                saved_files.append(backup_path)
            
            # 6. 创建集成示例（UTF-8）
            example_path = os.path.join(project_dir, "integration_example.py")
            example_content = f'''# -*- coding: utf-8 -*-
"""
==============================================================================
集成示例 - {direction_name}
==============================================================================

本文件展示如何将优化代码集成到 baseline 中
运行方式: python integration_example.py
编码: UTF-8
==============================================================================

"""

{self._generate_integration_example(item)}'''
            write_python_file(example_path, example_content, ensure_utf8_header=False)
            saved_files.append(example_path)
            
            print(f"    📦 {direction_name}")
            print(f"       💾 {patch_filename}")
            print(f"       📖 INTEGRATION_GUIDE.md")
            print(f"       🧪 {test_filename}")
        
        return saved_files
    
    def _generate_readme(self, item: Dict, direction_name: str, patch_filename: str) -> str:
        """生成 README（UTF-8 格式）"""
        guide = item.get('integration_guide', {})
        overview = guide.get('overview', {})
        
        readme = f"""# {direction_name} - 集成指南

## 📋 概述

| 项目 | 内容 |
|------|------|
| **优化方向** | {direction_name} |
| **类别** | {overview.get('category', 'Unknown')} |
| **集成模式** | {overview.get('integration_mode', 'Unknown')} |
| **难度** | {overview.get('difficulty', 'medium')} |

## 📁 文件说明

| 文件 | 说明 | 编码 |
|------|------|------|
| `{patch_filename}` | **新增优化代码**（在 baseline 基础上增量添加） | UTF-8 |
| `baseline_backup.py` | **原始 baseline 代码备份**（用于对比） | UTF-8 |
| `integration_example.py` | **集成示例代码**（展示如何使用） | UTF-8 |
| `*_test.py` | **测试代码**（验证优化效果） | UTF-8 |
| `INTEGRATION_GUIDE.json` | **结构化集成信息**（程序可读） | UTF-8 |

## ⚠️ 重要说明

### 1. 绝不修改 baseline 代码
- `{patch_filename}` **只包含新增的优化代码**
- **不包含**任何 baseline 原有代码
- 使用**增量修改模式**（装饰器/继承/包装）

### 2. 集成方式
本优化使用**{overview.get('integration_mode', 'Unknown')} 模式**：
- ✅ 不修改 baseline 原有代码
- ✅ 通过增量方式添加功能
- ✅ 可随时移除，不影响原有功能

### 3. 编码说明
所有文件均使用 **UTF-8 编码**，确保中文注释正常显示。

## 🎯 插入点
"""
        for point in guide.get('insertion_points', []):
            readme += f"""
### {point.get('file', 'Unknown')}
- **位置**: `{point.get('location', 'Unknown')}`
- **说明**: {point.get('description', '')}
"""
        
        readme += """
## 📝 集成步骤
"""
        for i, step in enumerate(guide.get('integration_steps', []), 1):
            readme += f"{i}. {step}\n"
        
        readme += "\n## 💡 备选方案\n\n"
        for alt in guide.get('alternatives', []):
            readme += f"- {alt}\n"
        
        readme += f"""
## ✅ 验证

运行以下命令验证集成是否成功：

```bash
{chr(10).join(guide.get('verification', {}).get('test_commands', []))}
```

**预期输出**: `{guide.get('verification', {}).get('expected_output', '无错误')}`

## 🔄 回滚方法

如需恢复原始 baseline：

```bash
# 使用备份文件恢复
cp baseline_backup.py your_original_file.py
```

## 🐞 问题排查

| 问题 | 解决方案 |
|------|----------|
| 中文乱码 | 确保文件以 UTF-8 编码打开 |
| 导入错误 | 检查 {patch_filename} 是否在 Python 路径中 |
| 集成失败 | 查看 integration_example.py 中的示例 |

---
*本指南由 EvoAgentX 自动生成*
"""
        return readme
    
    def _generate_integration_example(self, item: Dict) -> str:
        """生成集成示例代码"""
        guide = item.get('integration_guide', {})
        pattern = guide.get('overview', {}).get('integration_mode', 'unknown')
        
        example = f'"""\n集成示例: {pattern} 模式\n\n展示如何在 baseline 中使用生成的代码。\n"""\n\n'
        
        if pattern == "decorator":
            example += """
# === 方式1: 使用装饰器 ===

# 在 baseline 的 dataset.py 中添加
from your_patch import augment_decorator

@augment_decorator
class MyDataset(BaseDataset):
    # 原有代码不变
    pass


# === 方式2: 继承扩展 ===

from your_patch import AugmentedDataset

# 替换原有的 Dataset 实例化
dataset = AugmentedDataset(...)  # 代替 MyDataset(...)


# === 方式3: 运行时装饰 ===

from your_patch import augment_decorator
import baseline_module

# 运行时应用装饰器
baseline_module.MyDataset = augment_decorator(baseline_module.MyDataset)
"""
        elif pattern == "inheritance":
            example += """
# === 方式1: 继承扩展 ===

# 在 baseline 的 train.py 中
from your_patch import FocalLossWrapper
import torch.nn as nn

# 替换损失函数
criterion = FocalLossWrapper(
    base_loss=nn.CrossEntropyLoss(),
    gamma=2.0
)


# === 方式2: 配置注入 ===

# 如果 baseline 支持配置:
config = {
    'loss': 'FocalLossWrapper',
    'loss_params': {'gamma': 2.0}
}
"""
        elif pattern == "wrapper":
            example += """
# === 方式1: 函数包装 ===

# 在 baseline 的 train.py 中
from your_patch import create_wrapped_trainer

# 包装训练函数
wrapped_train = create_wrapped_trainer(original_train_one_epoch)

# 使用包装后的函数
for epoch in range(epochs):
    wrapped_train(model, loader, optimizer, epoch)


# === 方式2: 回调注入 ===

# 如果 baseline 使用 Trainer 类
from your_patch import CustomCallback

trainer = Trainer(callbacks=[CustomCallback()])
"""
        else:
            example += "# 请参考 INTEGRATION_GUIDE.md 中的说明"
        
        return example