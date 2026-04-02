"""
Baseline 深度分析器 Agent

职责：
1. 解析 baseline 代码结构
2. 提取数据流程（数据加载 -> 预处理 -> 增强 -> 输入）
3. 提取模型架构（骨干网络、头部、损失函数）
4. 提取训练循环（优化器、调度器、验证逻辑）
5. 识别优化插入点

输出格式化的 baseline 分析报告，供其他 Agent 使用
"""

import re
import ast
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path

from evoagentx.agents import Agent
from utils.agent_logger import get_agent_logger, log_agent_method


@dataclass
class DataPipeline:
    """数据流程信息"""
    loader_class: Optional[str] = None
    dataset_class: Optional[str] = None
    transforms: List[str] = field(default_factory=list)
    augmentation: Optional[str] = None
    batch_size: Optional[int] = None
    num_workers: Optional[int] = None
    insertion_points: List[str] = field(default_factory=list)


@dataclass
class ModelArchitecture:
    """模型架构信息"""
    backbone: Optional[str] = None
    backbone_pretrained: bool = False
    head_type: Optional[str] = None
    num_classes: Optional[int] = None
    input_shape: Optional[Tuple] = None
    loss_function: Optional[str] = None
    frozen_layers: List[str] = field(default_factory=list)


@dataclass
class TrainingConfig:
    """训练配置信息"""
    optimizer: Optional[str] = None
    scheduler: Optional[str] = None
    learning_rate: Optional[float] = None
    epochs: Optional[int] = None
    batch_size: Optional[int] = None
    validation_strategy: Optional[str] = None
    early_stopping: bool = False
    gradient_accumulation: int = 1


@dataclass
class OptimizationOpportunity:
    """优化机会"""
    location: str
    category: str  # data_augmentation, loss_function, training_strategy, etc.
    current_implementation: str
    suggestion: str
    expected_impact: str
    difficulty: str  # easy, medium, hard


class BaselineAnalyzer(Agent):
    """
    Baseline 深度分析器
    
    分析 baseline 代码，提取关键信息供后续 Agent 使用
    """
    
    def __init__(self, llm):
        super().__init__(
            name="BaselineAnalyzer",
            description="Baseline代码深度分析器，提取数据流、模型架构、训练循环",
            llm=llm,
            system_prompt="""你是代码分析专家，负责深度解析机器学习项目的 baseline 代码。

你的任务是：
1. 识别代码中的数据加载流程（Dataset -> DataLoader -> Transforms）
2. 提取模型架构信息（Backbone、Head、Loss Function）
3. 分析训练循环（Optimizer、Scheduler、Validation）
4. 发现潜在的优化插入点
5. 评估代码的可扩展性

分析原则：
- 只分析代码实际实现，不臆测
- 提取具体的类名、函数名、参数值
- 识别 PyTorch、TensorFlow、Keras 等框架特征
- 标注关键的扩展点（如可以插入数据增强的位置）"""
        )
        self.logger = get_agent_logger()
    
    @log_agent_method("name")
    def analyze(self, code: str, file_path: Optional[str] = None) -> Dict:
        """
        主入口：分析 baseline 代码
        
        Args:
            code: baseline 代码字符串
            file_path: 代码文件路径（可选，用于上下文）
            
        Returns:
            完整的 baseline 分析报告
        """
        print(f"\n📊 BaselineAnalyzer: 开始分析代码")
        print(f"  代码长度: {len(code)} 字符")
        
        if not code or len(code) < 100:
            print("  ⚠️ 代码为空或太短，跳过分析")
            return self._create_empty_analysis()
        
        # 多维度分析
        analysis = {
            "code_stats": self._analyze_code_stats(code),
            "data_pipeline": self._analyze_data_pipeline(code),
            "model_architecture": self._analyze_model_architecture(code),
            "training_config": self._analyze_training_config(code),
            "optimization_opportunities": self._identify_optimization_opportunities(code),
            "framework": self._detect_framework(code),
            "modules": self._extract_module_names(code),
            "raw_code_preview": code[:1000]  # 保留代码预览供后续使用
        }
        
        # 使用 LLM 进行深度分析（如果代码较复杂）
        if len(code) > 500:
            llm_analysis = self._llm_deep_analysis(code, analysis)
            analysis["llm_insights"] = llm_analysis
        
        print(f"  分析完成")
        print(f"     框架: {analysis['framework']}")
        print(f"     数据流程: {len(analysis['data_pipeline'].get('transforms', []))} 个 transform")
        print(f"     优化机会: {len(analysis['optimization_opportunities'])} 个")
        
        return analysis
    
    def _analyze_code_stats(self, code: str) -> Dict:
        """基础代码统计"""
        lines = code.split('\n')
        
        return {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "function_count": len(re.findall(r'^(def\s+\w+)', code, re.MULTILINE)),
            "class_count": len(re.findall(r'^(class\s+\w+)', code, re.MULTILINE)),
            "import_count": len(re.findall(r'^(import|from)', code, re.MULTILINE))
        }
    
    def _analyze_data_pipeline(self, code: str) -> Dict:
        """分析数据流程"""
        pipeline = {
            "loader_class": None,
            "dataset_class": None,
            "transforms": [],
            "augmentation": None,
            "batch_size": None,
            "num_workers": None,
            "insertion_points": []
        }
        
        # 检测 Dataset 类
        dataset_match = re.search(r'class\s+(\w+Dataset)\s*\(', code)
        if dataset_match:
            pipeline["dataset_class"] = dataset_match.group(1)
        
        # 检测 DataLoader
        dataloader_match = re.search(r'DataLoader\s*\(', code)
        if dataloader_match:
            pipeline["loader_class"] = "DataLoader"
            
            # 提取 batch_size
            bs_match = re.search(r'batch_size\s*=\s*(\d+)', code)
            if bs_match:
                pipeline["batch_size"] = int(bs_match.group(1))
            
            # 提取 num_workers
            nw_match = re.search(r'num_workers\s*=\s*(\d+)', code)
            if nw_match:
                pipeline["num_workers"] = int(nw_match.group(1))
        
        # 检测 transforms
        transform_patterns = [
            r'(\w+Transform)\s*\(',
            r'(transforms\.\w+)',
            r'(Resize|Normalize|ToTensor|RandomCrop|RandomFlip)',
            r'(A\.\w+)'  # Albumentations
        ]
        
        for pattern in transform_patterns:
            matches = re.findall(pattern, code)
            pipeline["transforms"].extend(matches)
        
        pipeline["transforms"] = list(set(pipeline["transforms"]))
        
        # 检测数据增强
        aug_keywords = ["augment", "Augment", "Mixup", "CutMix", "SpecAugment", "Random"]
        for kw in aug_keywords:
            if kw in code:
                pipeline["augmentation"] = f"Detected: {kw}"
                break
        
        # 确定插入点
        if pipeline["dataset_class"]:
            pipeline["insertion_points"].append(f"{pipeline['dataset_class']}.transform")
        if pipeline["loader_class"]:
            pipeline["insertion_points"].append("DataLoader.collate_fn")
        
        return pipeline
    
    def _analyze_model_architecture(self, code: str) -> Dict:
        """分析模型架构"""
        arch = {
            "backbone": None,
            "backbone_pretrained": False,
            "head_type": None,
            "num_classes": None,
            "input_shape": None,
            "loss_function": None,
            "frozen_layers": []
        }
        
        # 检测 backbone
        backbone_patterns = [
            (r'resnet(\d+)', 'ResNet'),
            (r'efficientnet[_-]?(\w+)', 'EfficientNet'),
            (r'vit[_-]?(\w+)', 'ViT'),
            (r'swin[_-]?(\w+)', 'Swin'),
            (r'convnext[_-]?(\w+)', 'ConvNeXt'),
            (r'densenet(\d+)', 'DenseNet'),
            (r'mobilenet[_-]?(\w+)', 'MobileNet'),
            (r'regnet[_-]?(\w+)', 'RegNet')
        ]
        
        for pattern, name in backbone_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                arch["backbone"] = f"{name}{match.group(1).upper() if match.group(1) else ''}"
                # 检查是否使用预训练
                if re.search(r'pretrained\s*=\s*True', code):
                    arch["backbone_pretrained"] = True
                break
        
        # 检测损失函数
        loss_patterns = [
            (r'CrossEntropyLoss', 'CrossEntropy'),
            (r'BCEWithLogitsLoss', 'BCEWithLogits'),
            (r'MSELoss', 'MSE'),
            (r'FocalLoss', 'Focal'),
            (r'DiceLoss', 'Dice'),
            (r'TripletLoss', 'Triplet')
        ]
        
        for pattern, name in loss_patterns:
            if re.search(pattern, code):
                arch["loss_function"] = name
                break
        
        # 检测 num_classes
        nc_match = re.search(r'num_classes\s*=\s*(\d+)', code)
        if nc_match:
            arch["num_classes"] = int(nc_match.group(1))
        
        # 检测冻结层
        freeze_match = re.search(r'\.requires_grad\s*=\s*False', code)
        if freeze_match:
            # 尝试提取被冻结的层
            freeze_layers = re.findall(r'(layer\d+|backbone|encoder)\.', code, re.IGNORECASE)
            arch["frozen_layers"] = list(set(freeze_layers))
        
        # 检测输入尺寸
        input_match = re.search(r'input_size\s*=\s*\((\d+),\s*(\d+)\)', code)
        if input_match:
            arch["input_shape"] = (int(input_match.group(1)), int(input_match.group(2)))
        
        return arch
    
    def _analyze_training_config(self, code: str) -> Dict:
        """分析训练配置"""
        config = {
            "optimizer": None,
            "scheduler": None,
            "learning_rate": None,
            "epochs": None,
            "batch_size": None,
            "validation_strategy": None,
            "early_stopping": False,
            "gradient_accumulation": 1
        }
        
        # 检测优化器
        optimizer_patterns = [
            (r'Adam\s*\(', 'Adam'),
            (r'AdamW\s*\(', 'AdamW'),
            (r'SGD\s*\(', 'SGD'),
            (r'RMSprop\s*\(', 'RMSprop')
        ]
        
        for pattern, name in optimizer_patterns:
            if re.search(pattern, code):
                config["optimizer"] = name
                break
        
        # 检测学习率调度器
        scheduler_patterns = [
            (r'CosineAnnealingLR', 'CosineAnnealing'),
            (r'StepLR', 'Step'),
            (r'ReduceLROnPlateau', 'ReduceOnPlateau'),
            (r'OneCycleLR', 'OneCycle'),
            (r'ExponentialLR', 'Exponential')
        ]
        
        for pattern, name in scheduler_patterns:
            if re.search(pattern, code):
                config["scheduler"] = name
                break
        
        # 提取学习率
        lr_match = re.search(r'lr\s*[=:]\s*([\d\.e-]+)', code)
        if lr_match:
            try:
                config["learning_rate"] = float(lr_match.group(1))
            except:
                pass
        
        # 提取 epochs
        epoch_match = re.search(r'epochs?\s*[=:]\s*(\d+)', code, re.IGNORECASE)
        if epoch_match:
            config["epochs"] = int(epoch_match.group(1))
        
        # 检测早停
        if re.search(r'EarlyStopping|early_stop|patience', code, re.IGNORECASE):
            config["early_stopping"] = True
        
        # 检测验证策略
        if re.search(r'GroupKFold|group', code):
            config["validation_strategy"] = "GroupKFold"
        elif re.search(r'StratifiedKFold|stratified', code):
            config["validation_strategy"] = "StratifiedKFold"
        elif re.search(r'KFold', code):
            config["validation_strategy"] = "KFold"
        
        return config
    
    def _identify_optimization_opportunities(self, code: str) -> List[Dict]:
        """识别优化机会"""
        opportunities = []
        
        # 检查数据增强
        if not re.search(r'augment|Augment|Mixup|SpecAugment', code, re.IGNORECASE):
            opportunities.append({
                "location": "data_pipeline.augmentation",
                "category": "data_augmentation",
                "current_implementation": "未检测到数据增强",
                "suggestion": "添加数据增强（SpecAugment、Mixup等）",
                "expected_impact": "提升模型泛化能力，减少过拟合",
                "difficulty": "easy"
            })
        
        # 检查损失函数
        if re.search(r'CrossEntropyLoss', code) and not re.search(r'FocalLoss|LabelSmoothing', code):
            opportunities.append({
                "location": "model.loss_function",
                "category": "loss_function",
                "current_implementation": "使用标准 CrossEntropy",
                "suggestion": "尝试 Focal Loss 或 Label Smoothing",
                "expected_impact": "改善类别不平衡问题",
                "difficulty": "easy"
            })
        
        # 检查学习率调度
        if not re.search(r'Scheduler|scheduler|lr_scheduler', code):
            opportunities.append({
                "location": "training.scheduler",
                "category": "training_strategy",
                "current_implementation": "未使用学习率调度",
                "suggestion": "添加 CosineAnnealing 或 ReduceLROnPlateau",
                "expected_impact": "更稳定的收敛，可能达到更好的局部最优",
                "difficulty": "easy"
            })
        
        # 检查验证策略
        if not re.search(r'GroupKFold|StratifiedKFold', code):
            opportunities.append({
                "location": "training.validation",
                "category": "training_strategy",
                "current_implementation": "使用简单分割或随机分割",
                "suggestion": "使用 GroupKFold 或 StratifiedKFold",
                "expected_impact": "更可靠的验证分数",
                "difficulty": "medium"
            })
        
        # 检查 TTA
        if not re.search(r'tta|TTA|test.*time.*augment', code, re.IGNORECASE):
            opportunities.append({
                "location": "inference.tta",
                "category": "post_processing",
                "current_implementation": "未使用 TTA",
                "suggestion": "添加 Test Time Augmentation",
                "expected_impact": "提升推理阶段的预测稳定性",
                "difficulty": "medium"
            })
        
        return opportunities
    
    def _detect_framework(self, code: str) -> str:
        """检测使用的深度学习框架"""
        if re.search(r'import\s+torch', code):
            return "PyTorch"
        elif re.search(r'import\s+tensorflow', code):
            return "TensorFlow"
        elif re.search(r'from\s+keras', code):
            return "Keras"
        elif re.search(r'import\s+jax', code):
            return "JAX"
        else:
            return "Unknown"
    
    def _extract_module_names(self, code: str) -> List[str]:
        """提取关键模块名称"""
        modules = []
        
        # 提取类名
        class_matches = re.findall(r'class\s+(\w+)', code)
        modules.extend(class_matches)
        
        # 提取主要函数名
        func_matches = re.findall(r'^def\s+(train|validate|test|forward|__init__|main)\s*\(', 
                                   code, re.MULTILINE)
        modules.extend(func_matches)
        
        return list(set(modules))
    
    def _llm_deep_analysis(self, code: str, initial_analysis: Dict) -> Dict:
        """使用 LLM 进行深度分析"""
        # 构建提示词
        prompt = f"""请深度分析以下机器学习代码的结构：

代码统计：
- 总行数: {initial_analysis['code_stats']['total_lines']}
- 函数数: {initial_analysis['code_stats']['function_count']}
- 类数: {initial_analysis['code_stats']['class_count']}
- 框架: {initial_analysis['framework']}

代码片段（前2000字符）：
```python
{code[:2000]}
```

请分析：
1. 数据流程的详细步骤（从文件加载到输入模型）
2. 模型架构的层次结构
3. 训练循环的关键步骤
4. 识别3-5个具体的优化插入点（包括行号附近的代码片段）
5. 评估代码的可扩展性（高/中/低）及原因

输出JSON格式：
{{
  "data_flow_steps": ["步骤1", "步骤2", ...],
  "model_hierarchy": "模型层次描述",
  "training_loop_steps": ["步骤1", "步骤2", ...],
  "insertion_points": [
    {{
      "location": "具体位置描述",
      "code_context": "附近的代码片段",
      "suggestion": "可以插入的优化"
    }}
  ],
  "extensibility": "high/medium/low",
  "extensibility_reason": "可扩展性评估原因"
}}"""
        
        try:
            response = self.llm.generate(prompt=prompt)
            
            # 提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            self.logger.log_agent_error("BaselineAnalyzer", "llm_analysis", e)
        
        return {}
    
    def _create_empty_analysis(self) -> Dict:
        """创建空的分析报告"""
        return {
            "code_stats": {},
            "data_pipeline": {},
            "model_architecture": {},
            "training_config": {},
            "optimization_opportunities": [],
            "framework": "Unknown",
            "modules": [],
            "error": "No code provided or code too short"
        }
    
    @log_agent_method("name")
    def get_insertion_point_info(self, analysis: Dict, location: str) -> Dict:
        """
        获取特定插入点的详细信息
        
        Args:
            analysis: baseline 分析报告
            location: 插入点位置（如 "data_pipeline.augmentation"）
            
        Returns:
            插入点的详细信息
        """
        data_pipeline = analysis.get("data_pipeline", {})
        model_arch = analysis.get("model_architecture", {})
        
        if location == "data_pipeline.augmentation":
            return {
                "exists": data_pipeline.get("augmentation") is not None,
                "dataset_class": data_pipeline.get("dataset_class"),
                "current_transforms": data_pipeline.get("transforms", []),
                "suggested_approach": f"在 {data_pipeline.get('dataset_class', 'Dataset')} 的 __getitem__ 方法中添加增强逻辑"
            }
        
        elif location == "model.loss_function":
            return {
                "exists": model_arch.get("loss_function") is not None,
                "current_loss": model_arch.get("loss_function"),
                "suggested_approach": "替换 criterion 的定义"
            }
        
        elif location == "training.scheduler":
            training = analysis.get("training_config", {})
            return {
                "exists": training.get("scheduler") is not None,
                "current_scheduler": training.get("scheduler"),
                "optimizer": training.get("optimizer"),
                "suggested_approach": f"在 {training.get('optimizer', 'optimizer')} 后添加 scheduler"
            }
        
        return {"exists": False, "error": "Unknown location"}
