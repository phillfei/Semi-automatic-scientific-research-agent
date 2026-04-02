"""
约束检查器 Agent - 防止 AI 跑偏的核心组件

职责：
1. 约束符合性检查 - 是否符合赛题约束（不涉及模型架构等）
2. Baseline 关联性检查 - 是否与 baseline 代码结构相关
3. 可行性检查 - 技术路线是否可行

使用位置：Supervisor 确定方向后，Search 搜索前
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any, ClassVar
from dataclasses import dataclass
from enum import Enum

from evoagentx.agents import Agent
from utils.agent_logger import get_agent_logger, log_agent_method


class CheckStatus(str, Enum):
    """检查结果状态"""
    PASS = "pass"           # 通过
    FAIL = "fail"           # 失败
    WARNING = "warning"     # 警告（需人工确认）
    SKIP = "skip"           # 跳过


@dataclass
class CheckResult:
    """单项检查结果"""
    check_name: str
    status: CheckStatus
    message: str
    details: Dict[str, Any] = None
    suggestions: List[str] = None


class ConstraintAgent(Agent):
    """
    约束检查器 Agent
    
    工作流位置：Supervisor -> ConstraintAgent -> Search -> Engineer
    
    核心检查：
    1. 约束符合性 - 是否违反"不涉及模型架构修改"等硬性约束
    2. Baseline 关联性 - 是否与 baseline 代码的数据流/训练流相关
    3. 可行性 - 技术路线是否可行，资源需求是否合理
    """
    
    # 约束检查清单
    CONSTRAINTS_CHECKLIST: ClassVar[Dict[str, Any]] = {
        "no_architecture_change": {
            "name": "不涉及模型架构修改",
            "description": "优化方向不能涉及修改模型架构、增加层数、更换backbone等",
            "banned_keywords": [
                "backbone", "骨干网络", "网络层数", "网络深度", "网络宽度",
                "attention机制", "注意力机制", "transformer层", "cnn层",
                "增加层", "add layer", "修改结构", "修改模型",
                "resnet", "efficientnet", "swin", "vit",
                "模型架构", "model architecture", "architecture"
            ],
            "banned_patterns": [
                r"添加.*层",
                r"增加.*层",
                r"修改.*结构",
                r"替换.*backbone",
                r"使用.*(resnet|efficientnet|vit)",
            ],
            "severity": "error",  # error/warning
            "required": True
        },
        "data_training_focus": {
            "name": "聚焦数据/训练策略",
            "description": "优化方向应聚焦于数据增强、特征工程、损失函数、训练策略等",
            "allowed_keywords": [
                "数据增强", "augmentation", "mixup", "cutmix", "specaugment",
                "特征工程", "feature engineering",
                "损失函数", "loss function", "focal loss", "label smoothing",
                "训练策略", "optimizer", "scheduler", "学习率", "learning rate",
                "后处理", "post processing", "tta", "test time augmentation",
                "集成", "ensemble", "stacking", "bagging",
                "伪标签", "pseudo label", "半监督", "semi-supervised",
                "交叉验证", "cross validation", "oof", "out-of-fold"
            ],
            "severity": "warning",
            "required": False
        },
        "no_inference_optimization": {
            "name": "不优化推理速度",
            "description": "禁止提出推理速度优化、模型压缩、剪枝、量化等方向",
            "banned_keywords": [
                "推理速度", "inference speed", "latency", "延迟",
                "模型压缩", "model compression", "剪枝", "pruning",
                "量化", "quantization", "蒸馏", "distillation",
                "轻量化", "lightweight", "mobile", "边缘部署"
            ],
            "severity": "error",
            "required": True
        },
        "no_code_refactoring": {
            "name": "不重构代码",
            "description": "禁止提出代码重构、可读性改进等与性能无关的方向",
            "banned_keywords": [
                "代码重构", "code refactoring", "可读性", "readability",
                "代码风格", "code style", "模块化", "modularization",
                "命名规范", "naming convention"
            ],
            "severity": "error",
            "required": True
        }
    }
    
    def __init__(self, llm, strict_mode: bool = False):
        """
        Args:
            llm: LLM 实例
            strict_mode: 严格模式，任何警告都会导致失败
        """
        super().__init__(
            name="ConstraintChecker",
            description="约束检查器，确保优化方向符合约束、与baseline兼容",
            llm=llm,
            system_prompt="""你是约束检查器，负责确保优化方向符合以下原则：

1. **不涉及模型架构修改**：不修改网络层数、不更换backbone、不添加attention机制
2. **聚焦数据/训练策略**：关注数据增强、特征工程、损失函数、训练策略、后处理
3. **不优化推理速度**：不涉及模型压缩、剪枝、量化
4. **不重构代码**：不涉及代码风格、可读性改进
5. **与Baseline兼容**：优化必须能在baseline代码结构上实现

你的任务是：
- 检查每个优化方向是否符合约束
- 评估方向与baseline的关联性
- 给出明确的通过/失败/警告判定
- 对失败的方向给出修改建议"""
        )
        self.logger = get_agent_logger()
        self.strict_mode = strict_mode
        
        # 约束检查统计
        self.check_stats = {
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
    
    @log_agent_method("name")
    def validate_directions(
        self,
        directions: List[Dict],
        baseline_analysis: Optional[Dict] = None,
        competition_info: Optional[Dict] = None
    ) -> Dict:
        """
        主入口：校验优化方向
        
        Args:
            directions: Supervisor 生成的优化方向列表
            baseline_analysis: BaselineAnalyzer 的分析结果
            competition_info: 赛题信息（评估指标、数据类型等）
            
        Returns:
            {
                "valid_directions": [...],  # 通过校验的方向
                "rejected_directions": [...],  # 被拒绝的方向及原因
                "check_results": [...],  # 详细检查结果
                "summary": str  # 总结报告
            }
        """
        print(f"\n[Constraint] 开始校验 {len(directions)} 个优化方向")
        
        valid_directions = []
        rejected_directions = []
        all_results = []
        
        for i, direction in enumerate(directions, 1):
            print(f"  检查方向 {i}/{len(directions)}: {direction.get('name', '未知')}")
            
            # 执行三重校验
            results = self._triple_check(
                direction=direction,
                baseline_analysis=baseline_analysis,
                competition_info=competition_info
            )
            
            all_results.append({
                "direction": direction,
                "checks": results
            })
            
            # 判断整体结果
            if self._is_direction_valid(results):
                valid_directions.append(direction)
                print(f"    [OK] 通过")
            else:
                rejected_directions.append({
                    "direction": direction,
                    "reasons": self._collect_failures(results)
                })
                print(f"    [FAIL] 失败")
        
        # 生成总结报告
        summary = self._generate_summary(valid_directions, rejected_directions)
        
        return {
            "valid_directions": valid_directions,
            "rejected_directions": rejected_directions,
            "check_results": all_results,
            "summary": summary,
            "stats": self.check_stats
        }
    
    def _triple_check(
        self,
        direction: Dict,
        baseline_analysis: Optional[Dict],
        competition_info: Optional[Dict]
    ) -> List[CheckResult]:
        """执行三重校验"""
        results = []
        
        # 1. 约束符合性检查
        results.extend(self._check_constraints(direction))
        
        # 2. Baseline 关联性检查
        if baseline_analysis:
            results.append(self._check_baseline_relevance(direction, baseline_analysis))
        else:
            results.append(CheckResult(
                check_name="baseline_relevance",
                status=CheckStatus.SKIP,
                message="未提供baseline分析，跳过关联性检查"
            ))
        
        # 3. 可行性检查
        results.append(self._check_feasibility(direction, competition_info))
        
        self.check_stats["total_checks"] += len(results)
        
        return results
    
    def _check_constraints(self, direction: Dict) -> List[CheckResult]:
        """检查约束符合性"""
        results = []
        
        name = direction.get("name", "")
        rationale = direction.get("rationale", "")
        text = f"{name} {rationale}".lower()
        
        for constraint_id, constraint in self.CONSTRAINTS_CHECKLIST.items():
            # 检查 banned keywords
            found_banned = []
            for keyword in constraint.get("banned_keywords", []):
                if keyword.lower() in text:
                    found_banned.append(keyword)
            
            # 检查 banned patterns
            for pattern in constraint.get("banned_patterns", []):
                if re.search(pattern, text, re.IGNORECASE):
                    found_banned.append(f"匹配模式: {pattern}")
            
            if found_banned:
                status = CheckStatus.FAIL if constraint.get("severity") == "error" else CheckStatus.WARNING
                
                results.append(CheckResult(
                    check_name=constraint_id,
                    status=status,
                    message=f"违反约束: {constraint['name']}",
                    details={"found": found_banned},
                    suggestions=[
                        f"避免使用以下词汇: {', '.join(found_banned[:3])}",
                        f"建议方向: 聚焦于数据增强、损失函数、训练策略等",
                        f"参考: {constraint['description']}"
                    ]
                ))
                
                if status == CheckStatus.FAIL:
                    self.check_stats["failed"] += 1
                else:
                    self.check_stats["warnings"] += 1
            else:
                results.append(CheckResult(
                    check_name=constraint_id,
                    status=CheckStatus.PASS,
                    message=f"符合约束: {constraint['name']}"
                ))
                self.check_stats["passed"] += 1
        
        return results
    
    def _check_baseline_relevance(
        self,
        direction: Dict,
        baseline_analysis: Dict
    ) -> CheckResult:
        """检查与 baseline 的关联性"""
        direction_name = direction.get("name", "")
        target_module = direction.get("target_module", "")
        
        # 获取 baseline 中的模块
        baseline_modules = baseline_analysis.get("modules", [])
        data_pipeline = baseline_analysis.get("data_pipeline", {})
        
        # 检查 target_module 是否在 baseline 中存在
        relevance_score = 0
        issues = []
        
        # 简单的关键词匹配
        module_keywords = {
            "数据加载": ["data", "loader", "dataset", "dataloader"],
            "数据增强": ["augment", "transform"],
            "特征工程": ["feature", "extract"],
            "损失函数": ["loss", "criterion"],
            "训练策略": ["train", "optimizer", "scheduler"],
            "后处理": ["post", "tta", "ensemble"]
        }
        
        if target_module:
            # 检查是否匹配 baseline 模块
            matched = False
            for module_type, keywords in module_keywords.items():
                if any(kw in target_module.lower() for kw in keywords):
                    if module_type in str(baseline_modules).lower() or \
                       any(kw in str(data_pipeline).lower() for kw in keywords):
                        relevance_score += 1
                        matched = True
            
            if not matched:
                issues.append(f"目标模块 '{target_module}' 与 baseline 结构关联性不明确")
        else:
            issues.append("未指定目标模块")
        
        # 使用 LLM 进行更深入的关联性分析
        if self.llm:
            prompt = f"""分析以下优化方向与 baseline 代码的关联性：

优化方向: {direction_name}
目标模块: {target_module}
Baseline 模块: {baseline_modules}

请判断：
1. 该优化方向是否能在 baseline 结构上实现？
2. 需要在 baseline 的哪个位置插入代码？
3. 是否与现有代码冲突？

输出JSON格式：
{{
  "relevance_score": 0-100,
  "can_integrate": true/false,
  "insertion_point": "插入位置建议",
  "potential_conflicts": ["可能的冲突"],
  "suggestions": ["改进建议"]
}}"""
            
            try:
                response = self.llm.generate(prompt=prompt)
                # 解析 JSON
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                    relevance_score = analysis.get("relevance_score", 50)
                    
                    if not analysis.get("can_integrate", True):
                        issues.append("无法在 baseline 结构上实现")
                    
                    if analysis.get("potential_conflicts"):
                        issues.extend(analysis["potential_conflicts"])
            except Exception as e:
                self.logger.log_agent_error("ConstraintAgent", "llm_analysis", e)
        
        # 确定状态
        if issues:
            status = CheckStatus.WARNING if relevance_score > 50 else CheckStatus.FAIL
            return CheckResult(
                check_name="baseline_relevance",
                status=status,
                message=f"Baseline 关联性检查: 得分 {relevance_score}/100",
                details={"score": relevance_score, "issues": issues},
                suggestions=[
                    "明确指定在 baseline 代码中的插入位置",
                    "确保优化方向与现有代码结构兼容"
                ]
            )
        else:
            return CheckResult(
                check_name="baseline_relevance",
                status=CheckStatus.PASS,
                message=f"与 baseline 关联性良好: 得分 {relevance_score}/100"
            )
    
    def _check_feasibility(
        self,
        direction: Dict,
        competition_info: Optional[Dict]
    ) -> CheckResult:
        """检查可行性"""
        issues = []
        
        # 检查是否有明确的实现思路
        if not direction.get("search_keywords"):
            issues.append("未提供搜索关键词")
        
        if not direction.get("rationale"):
            issues.append("未提供选择理由")
        
        # 检查资源需求（简化版）
        name = direction.get("name", "").lower()
        high_resource_keywords = ["多尺度", "多模型", "集成", "ensemble", "stacking"]
        
        resource_warning = any(kw in name for kw in high_resource_keywords)
        
        if issues:
            return CheckResult(
                check_name="feasibility",
                status=CheckStatus.WARNING,
                message="可行性检查发现问题",
                details={"issues": issues},
                suggestions=["补充缺失的信息", "提供更详细的实现思路"]
            )
        elif resource_warning:
            return CheckResult(
                check_name="feasibility",
                status=CheckStatus.WARNING,
                message="该方向可能需要较多计算资源",
                details={"resource_intensive": True},
                suggestions=["确认计算资源是否充足", "考虑简化方案"]
            )
        else:
            return CheckResult(
                check_name="feasibility",
                status=CheckStatus.PASS,
                message="可行性检查通过"
            )
    
    def _is_direction_valid(self, results: List[CheckResult]) -> bool:
        """判断方向是否有效"""
        has_fail = any(r.status == CheckStatus.FAIL for r in results)
        
        if self.strict_mode:
            # 严格模式：任何警告也视为失败
            has_warning = any(r.status == CheckStatus.WARNING for r in results)
            return not has_fail and not has_warning
        else:
            return not has_fail
    
    def _collect_failures(self, results: List[CheckResult]) -> List[str]:
        """收集失败原因"""
        failures = []
        for result in results:
            if result.status in [CheckStatus.FAIL, CheckStatus.WARNING]:
                failures.append(f"{result.check_name}: {result.message}")
        return failures
    
    def _generate_summary(
        self,
        valid_directions: List[Dict],
        rejected_directions: List[Dict]
    ) -> str:
        """生成总结报告"""
        total = len(valid_directions) + len(rejected_directions)
        
        summary = f"""
约束检查结果总结
================
总方向数: {total}
通过: {len(valid_directions)}
拒绝: {len(rejected_directions)}

通过的方向:
"""
        for d in valid_directions:
            summary += f"  [OK] {d.get('name', '未知')}\n"
        
        if rejected_directions:
            summary += "\n被拒绝的方向:\n"
            for item in rejected_directions:
                summary += f"  [FAIL] {item['direction'].get('name', '未知')}\n"
                for reason in item['reasons']:
                    summary += f"     - {reason}\n"
        
        return summary
    
    @log_agent_method("name")
    def generate_correction_suggestions(
        self,
        rejected_direction: Dict,
        check_results: List[CheckResult]
    ) -> List[str]:
        """
        为被拒绝的方向生成修改建议
        
        Args:
            rejected_direction: 被拒绝的方向
            check_results: 该方向的检查结果
            
        Returns:
            修改建议列表
        """
        suggestions = []
        
        # 收集所有建议
        for result in check_results:
            if result.suggestions:
                suggestions.extend(result.suggestions)
        
        # 使用 LLM 生成综合建议
        if self.llm:
            prompt = f"""针对以下被拒绝的优化方向，提供具体的修改建议：

方向名称: {rejected_direction.get('name')}
选择理由: {rejected_direction.get('rationale')}
失败原因: {self._collect_failures(check_results)}

请提供：
1. 如何修改方向名称使其符合约束
2. 如何调整实现思路使其与baseline兼容
3. 推荐的替代方向（如果适用）

输出格式：
- 建议1: ...
- 建议2: ..."""
            
            try:
                response = self.llm.generate(prompt=prompt)
                # 解析建议
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('-') or line.startswith('建议'):
                        suggestions.append(line.lstrip('- ').strip())
            except Exception as e:
                self.logger.log_agent_error("ConstraintAgent", "generate_suggestions", e)
        
        return suggestions
