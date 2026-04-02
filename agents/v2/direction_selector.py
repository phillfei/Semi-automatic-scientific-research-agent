"""
方向选择器 Agent - 基于项目分析和历史知识库选择优化方向

职责：
1. 接收项目上下文（project_context）
2. 结合历史知识库（搜索报告、精度参数）
3. 避免重复尝试已验证无效的方法
4. 输出符合约束的优化方向

约束：
- 禁止结构优化（加Attention、改网络层等）
- 只允许数据/训练/后处理策略
"""

from typing import Dict, List, Optional, Any, ClassVar
from evoagentx.agents import Agent
from utils.agent_logger import get_agent_logger, log_agent_method


class DirectionSelectorAgent(Agent):
    """
    方向选择器 Agent
    
    基于项目分析结果和历史反馈，智能选择优化方向
    """
    
    # 允许的优化类别（用于分类推断，不用于约束检查）
    ALLOWED_CATEGORIES: ClassVar[Dict[str, Any]] = {
        "data_augmentation": {
            "name": "数据增强",
            "keywords": ["augmentation", "mixup", "cutmix", "specaugment", "randaugment"],
            "target_module": "数据加载"
        },
        "feature_engineering": {
            "name": "特征工程", 
            "keywords": ["feature", "mfcc", "mel spectrogram", "embedding"],
            "target_module": "特征提取"
        },
        "loss_function": {
            "name": "损失函数",
            "keywords": ["focal loss", "label smoothing", "dice loss", "bce"],
            "target_module": "损失函数"
        },
        "training_strategy": {
            "name": "训练策略",
            "keywords": ["scheduler", "warmup", "optimizer", "learning rate", "gradient"],
            "target_module": "训练策略"
        },
        "post_processing": {
            "name": "后处理",
            "keywords": ["tta", "test time augmentation", "ensemble", "pseudo label"],
            "target_module": "后处理"
        }
    }
    
    def __init__(self, llm, project_manager=None):
        super().__init__(
            name="DirectionSelector",
            description="基于项目分析和历史知识库选择优化方向",
            llm=llm,
            system_prompt="""你是方向选择专家，负责基于项目分析和历史反馈选择最优的优化方向。

## 核心原则
1. **基于数据说话**：严格依据EDA发现的问题选择方向
2. **避免重复踩坑**：参考历史反馈，跳过已验证无效的方法
3. **知识库复用**：优先选择已有搜索报告的方向
4. **结构零修改**：绝不选择涉及网络架构修改的方向

## 选择策略
1. 分析project_context中的关键问题
2. 检查历史反馈中各方向的精度提升记录
3. 优先选择知识库中已有论文支持的方向
4. 确保方向之间互补，不重复
"""
        )
        self.logger = get_agent_logger()
        self.project_manager = project_manager
    
    @log_agent_method("name")
    def select_directions(
        self,
        project_context: Dict[str, Any],
        key_findings: List[str],
        baseline_analysis: Dict,
        history: List[Dict] = None,
        max_directions: int = 3
    ) -> Dict:
        """
        主入口：选择优化方向
        
        Args:
            project_context: 项目上下文（竞赛类型、评估指标、数据特点）
            key_findings: EDA发现的关键问题
            baseline_analysis: Baseline代码分析
            history: 历史优化反馈
            max_directions: 最多选择几个方向
            
        Returns:
            {
                "selected_directions": [...],
                "reasoning": "选择理由",
                "excluded_methods": ["已验证无效的方法"]
            }
        """
        print(f"\n🎯 DirectionSelector: 基于分析选择优化方向")
        
        # 1. 从历史中提取已验证的方法及其效果
        method_effectiveness = self._analyze_history(history or [])
        
        # 2. 从知识库获取可用的搜索报告
        available_knowledge = self._get_available_knowledge(project_context.get("project_name", ""))
        
        # 3. 构建选择提示词
        prompt = self._build_selection_prompt(
            project_context=project_context,
            key_findings=key_findings,
            baseline_analysis=baseline_analysis,
            method_effectiveness=method_effectiveness,
            available_knowledge=available_knowledge,
            max_directions=max_directions
        )
        
        # 4. 调用LLM选择方向
        print(f"  📝 基于历史反馈和知识库选择方向...")
        result = self.llm.generate(prompt=prompt)
        
        # 5. 解析结果
        directions = self._parse_directions(result)
        
        # 6. 后处理：补全字段（约束检查由 ConstraintAgent 统一处理）
        selected_directions = self._post_process_directions(directions)
        
        print(f"  选择完成: {len(selected_directions)} 个方向")
        for d in selected_directions:
            print(f"     - {d.get('name')} (类别: {d.get('category', '未知')})")
        
        return {
            "selected_directions": selected_directions,
            "reasoning": directions.get("reasoning", ""),
            "excluded_methods": method_effectiveness.get("failed_methods", [])
        }
    
    def _analyze_history(self, history: List[Dict]) -> Dict:
        """分析历史反馈，提取各方法的有效性"""
        effectiveness = {
            "successful_methods": [],  # 有精度提升的方法
            "failed_methods": [],      # 无效果或负效果的方法
            "method_scores": {}        # 方法 -> 平均提升
        }
        
        for record in history:
            if "directions" in record and "metrics" in record:
                for direction in record.get("directions", []):
                    method_name = direction if isinstance(direction, str) else direction.get("name", "")
                    
                    # 提取精度变化（简化处理，实际需要更复杂的逻辑）
                    metrics = record.get("metrics", {})
                    if isinstance(metrics, dict):
                        # 假设有before/after或delta字段
                        improvement = metrics.get("improvement", metrics.get("delta", 0))
                        
                        if improvement > 0.001:  # 有提升
                            effectiveness["successful_methods"].append(method_name)
                        elif improvement < -0.001:  # 负效果
                            effectiveness["failed_methods"].append(method_name)
                        
                        # 记录分数
                        if method_name not in effectiveness["method_scores"]:
                            effectiveness["method_scores"][method_name] = []
                        effectiveness["method_scores"][method_name].append(improvement)
        
        return effectiveness
    
    def _get_available_knowledge(self, project_name: str) -> List[Dict]:
        """从知识库获取可用的搜索报告"""
        if not self.project_manager or not project_name:
            return []
        
        try:
            reports = self.project_manager.list_search_reports(project_name)
            return [
                {
                    "direction_name": r.get("direction_name"),
                    "keywords": r.get("keywords", []),
                    "use_count": r.get("use_count", 0)
                }
                for r in reports
            ]
        except Exception:
            return []
    
    def _build_selection_prompt(
        self,
        project_context: Dict,
        key_findings: List[str],
        baseline_analysis: Dict,
        method_effectiveness: Dict,
        available_knowledge: List[Dict],
        max_directions: int
    ) -> str:
        """构建方向选择提示词"""
        
        prompt_parts = [
            "# 优化方向选择",
            "",
            "## 项目背景",
            f"竞赛: {project_context.get('competition', '未知')}",
            f"任务类型: {project_context.get('task_type', '未知')}",
            f"评估指标: {project_context.get('evaluation_metric', '未知')}",
            f"数据特点: {project_context.get('data_characteristics', '未知')}",
            "",
            "## EDA发现的关键问题",
        ]
        
        for i, finding in enumerate(key_findings[:5], 1):
            prompt_parts.append(f"{i}. {finding}")
        
        # 历史反馈
        if method_effectiveness.get("successful_methods") or method_effectiveness.get("failed_methods"):
            prompt_parts.extend([
                "",
                "## 历史优化反馈（重要参考）",
                "已验证有效的方法:",
            ])
            for method in method_effectiveness.get("successful_methods", [])[:5]:
                scores = method_effectiveness.get("method_scores", {}).get(method, [])
                avg_score = sum(scores) / len(scores) if scores else 0
                prompt_parts.append(f"  - {method}: 平均提升 {avg_score:+.4f}")
            
            prompt_parts.extend([
                "",
                "已验证无效/负效果的方法（避免选择）:",
            ])
            for method in method_effectiveness.get("failed_methods", [])[:5]:
                prompt_parts.append(f"  - {method}")
        
        # 知识库
        if available_knowledge:
            prompt_parts.extend([
                "",
                "## 可用知识库（已有论文支持）",
            ])
            for k in available_knowledge[:5]:
                prompt_parts.append(f"  - {k.get('direction_name')}: 已使用{k.get('use_count')}次")
        
        # Baseline分析
        if baseline_analysis:
            prompt_parts.extend([
                "",
                "## Baseline代码分析",
                f"框架: {baseline_analysis.get('framework', '未知')}",
                f"当前损失函数: {baseline_analysis.get('model_architecture', {}).get('loss_function', '未知')}",
                f"当前数据增强: {baseline_analysis.get('data_pipeline', {}).get('augmentation', '无')}",
            ])
        
        # 输出要求（约束由 ConstraintAgent 统一检查）
        prompt_parts.extend([
            "",
            "## 方向选择指导",
            "重要：方向名称必须是抽象的类别，不要包含具体技术名称",
            "",
            "错误示例（过于具体，不要这样写）:",
            '   - "Focal Loss优化"  → 应该改为 → "损失函数优化"',
            '   - "SpecAugment增强" → 应该改为 → "时频域数据增强"',
            '   - "Mixup数据增强"   → 应该改为 → "样本混合增强策略"',
            '   - "CosineAnnealing调度" → 应该改为 → "学习率调度优化"',
            "",
            "正确示例（抽象类别，应该这样写）:",
            '   - "损失函数改进"',
            '   - "时频域数据增强"',
            '   - "样本混合策略"',
            '   - "学习率调度优化"',
            '   - "训练策略正则化"',
            '   - "后处理集成方法"',
            "",
            "**原因**: 具体技术由 SearchAgent 后续搜索确定，",
            "         方向选择只确定优化类别和要解决的问题。",
            "",
            "## 允许的抽象类别",
            "1. **数据增强相关**（不要指定具体技术）:",
            "   - 时频域数据增强",
            "   - 样本混合增强策略",
            "   - 时间维度增强方法",
            "",
            "2. **损失函数相关**（不要指定具体损失）:",
            "   - 损失函数改进",
            "   - 类别不平衡处理",
            "   - 边界样本挖掘",
            "",
            "3. **训练策略相关**（不要指定具体调度器）:",
            "   - 学习率调度优化",
            "   - 优化器策略改进",
            "   - 训练过程正则化",
            "   -  warm-up策略",
            "",
            "4. **后处理相关**:",
            "   - 测试时增强",
            "   - 模型集成方法",
            "   - 伪标签策略",
            "",
            "5. **特征工程相关**:",
            "   - 特征表示优化",
            "   - 多尺度特征融合",
            "",
            "## 输出要求",
            f"请输出 {max_directions} 个抽象的优化方向类别，JSON格式:",
            "",
            "```json",
            "{",
            '  "reasoning": "整体选择策略和理由",',
            '  "directions": [',
            "    {",
            '      "name": "抽象的类别名称（如：损失函数改进）",',
            '      "category": "data_augmentation/loss_function/training_strategy/post_processing/feature_engineering",',
            '      "rationale": "为什么选这个类别：当前问题+这个类别如何解决+预期效果",',
            '      "search_keywords": ["搜索用的宽泛关键词", "避免具体技术名"],',
            '      "target_module": "数据加载/损失函数/训练策略/后处理/特征提取",',
            '      "confidence": "high/medium/low",',
            '      "estimated_improvement": "预期提升（如AUC +0.02）"',
            "    }",
            "  ]",
            "}",
            "```",
            "",
            "**注意**: search_keywords 也应该是宽泛的，便于搜索多种可能的技术方案。",
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_directions(self, result: str) -> Dict:
        """解析LLM返回的方向列表"""
        import json
        import re
        
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return parsed
        except Exception as e:
            self.logger.log_agent_error("DirectionSelector", "_parse_directions", e)
        
        # 默认返回
        return {
            "reasoning": "解析失败",
            "directions": []
        }
    
    def _post_process_directions(self, directions_data: Dict) -> List[Dict]:
        """
        后处理方向数据（不检查约束，约束由 ConstraintAgent 统一处理）
        只做字段补全和类别推断
        """
        processed = []
        
        for direction in directions_data.get("directions", []):
            name = direction.get("name", "").lower()
            rationale = direction.get("rationale", "").lower()
            combined = name + " " + rationale
            
            # 推断类别和 target_module（如果缺失）
            category = direction.get("category", "")
            if category not in self.ALLOWED_CATEGORIES:
                for cat_key, cat_info in self.ALLOWED_CATEGORIES.items():
                    if any(kw in combined for kw in cat_info["keywords"]):
                        direction["category"] = cat_key
                        if not direction.get("target_module"):
                            direction["target_module"] = cat_info["target_module"]
                        break
            
            # 确保有 search_keywords
            if not direction.get("search_keywords"):
                direction["search_keywords"] = direction.get("name", "optimization").replace(" ", ", ").split(", ")[:5]
            
            processed.append(direction)
        
        return processed
