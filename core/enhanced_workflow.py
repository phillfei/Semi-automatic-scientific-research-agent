"""
增强版工作流 - 集成防跑偏机制

工作流顺序：
1. BaselineAnalyzer - 分析代码结构
2. SmartEDA - 探索数据特征
3. Supervisor V2 - 基于分析结果确定方向
4. ConstraintAgent - 校验方向
5. Search - 搜索技术方案
6. Engineer V2 - 绑定baseline生成代码
"""

import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from evoagentx.workflow import WorkFlow
from evoagentx.agents import AgentManager

# 导入新组件
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.v2.baseline_analyzer import BaselineAnalyzer
from agents.v2.constraint_agent import ConstraintAgent
from agents.v2.supervisor_agent_v2 import SupervisorAgentV2
from data.smart_eda import SmartEDA
from config.prompts_v2 import get_supervisor_prompt_v2


class EnhancedOptimizationWorkflow:
    """
    增强版优化工作流
    
    特点：
    - 深度 baseline 分析
    - 智能 EDA
    - 约束检查防止跑偏
    - 代码生成绑定 baseline
    """
    
    def __init__(self, llm, project_manager=None, enable_constraint_check: bool = True):
        self.llm = llm
        self.project_manager = project_manager
        self.enable_constraint_check = enable_constraint_check
        
        # 初始化各组件
        self.baseline_analyzer = BaselineAnalyzer(llm)
        self.smart_eda = SmartEDA()
        self.constraint_agent = ConstraintAgent(llm) if enable_constraint_check else None
        
        # 结果存储
        self.baseline_analysis = None
        self.eda_report = None
        self.constraint_check_results = None
    
    async def run(
        self,
        project_name: str,
        html_content: str = "",
        code_content: str = "",
        data_path: str = "",
        instruction: str = ""
    ) -> Dict[str, Any]:
        """
        执行增强版工作流
        
        Args:
            project_name: 项目名称
            html_content: 赛题HTML内容
            code_content: baseline代码
            data_path: 数据路径
            instruction: 用户指令
            
        Returns:
            完整的工作流结果
        """
        print(f"\n{'='*70}")
        print(f"🚀 增强版优化工作流: {project_name}")
        print(f"{'='*70}")
        
        results = {
            "project_name": project_name,
            "baseline_analysis": None,
            "eda_report": None,
            "directions": None,
            "constraint_check": None,
            "search_results": None,
            "generated_code": None
        }
        
        # ===== 步骤1: Baseline 分析 =====
        print("\n📊 步骤1: 分析 Baseline 代码结构...")
        if code_content:
            self.baseline_analysis = self.baseline_analyzer.analyze(code_content)
            results["baseline_analysis"] = self.baseline_analysis
            print(f"  ✅ 框架: {self.baseline_analysis.get('framework', 'Unknown')}")
            print(f"     优化机会: {len(self.baseline_analysis.get('optimization_opportunities', []))} 个")
        else:
            print("  ⚠️ 未提供代码，跳过分析")
        
        # ===== 步骤2: 智能 EDA =====
        print("\n🔬 步骤2: 智能数据探索...")
        if data_path and Path(data_path).exists():
            self.eda_report = self.smart_eda.explore(data_path)
            results["eda_report"] = self.smart_eda.to_dict()
            print(f"  ✅ 数据类型: {self.eda_report.data_type}")
            print(f"     洞察: {len(self.eda_report.insights)} 个")
            print(f"     建议: {len(self.eda_report.optimization_suggestions)} 个")
        else:
            print("  ⚠️ 未提供数据路径，跳过EDA")
        
        # ===== 步骤3: Supervisor 确定方向（V2） =====
        print("\n🎯 步骤3: Supervisor 确定优化方向...")
        
        # 构建增强版提示词
        prompt_vars = {
            "max_directions": 3,
            "data_type": self.eda_report.data_type if self.eda_report else "未知",
            "evaluation_metric": "AUC/准确率",  # 可从赛题HTML提取
            "baseline_analysis": self._format_baseline_for_prompt(self.baseline_analysis),
            "eda_results": self._format_eda_for_prompt(self.eda_report),
            "html_content": html_content[:5000] if html_content else "",
            "instruction": instruction,
            "code_content": code_content[:3000] if code_content else ""
        }
        
        # 创建增强版 Supervisor
        supervisor = SupervisorAgentV2(
            llm=self.llm,
            project_manager=self.project_manager,
            custom_prompt=get_supervisor_prompt_v2(**prompt_vars)
        )
        
        analysis = supervisor.initialize_project(
            project_name=project_name,
            html_content=html_content,
            data_sample_content="",
            data_sample_path=data_path,
            data_sample_folder=data_path if Path(data_path).is_dir() else "",
            data_sample_info=self._format_eda_summary(self.eda_report),
            code_content=code_content,
            instruction=instruction
        )
        
        directions = analysis.get("optimization_directions", [])
        print(f"  ✅ 确定 {len(directions)} 个优化方向")
        for d in directions:
            print(f"     - {d.get('name', '未知')} (目标: {d.get('target_module', '未指定')})")
        
        results["directions"] = directions
        
        # ===== 步骤4: 约束检查 =====
        if self.enable_constraint_check and directions:
            print("\n🔒 步骤4: 约束检查...")
            
            check_result = self.constraint_agent.validate_directions(
                directions=directions,
                baseline_analysis=self.baseline_analysis,
                competition_info={"html": html_content}
            )
            
            self.constraint_check_results = check_result
            results["constraint_check"] = check_result
            
            valid_directions = check_result.get("valid_directions", [])
            rejected = check_result.get("rejected_directions", [])
            
            print(f"  ✅ 通过: {len(valid_directions)} 个")
            if rejected:
                print(f"  ❌ 拒绝: {len(rejected)} 个")
                for r in rejected:
                    print(f"     - {r['direction'].get('name')}: {r['reasons'][0] if r['reasons'] else '未知原因'}")
            
            # 更新方向列表为通过校验的方向
            directions = valid_directions
        
        # ===== 步骤5: 搜索（复用现有 SearchAgent）=====
        if directions:
            print("\n🔍 步骤5: 搜索技术方案...")
            
            # 导入 SearchAgent
            from agents.search_agent import SearchAgent
            search_agent = SearchAgent(llm=self.llm, project_manager=self.project_manager)
            
            # 构建搜索任务
            tasks = []
            for direction in directions[:3]:  # 最多3个方向
                tasks.append({
                    "direction_name": direction.get("name", "未知方向"),
                    "keywords": direction.get("search_keywords", []),
                    "rationale": direction.get("rationale", "")
                })
            
            search_result = await asyncio.to_thread(
                search_agent.parallel_search,
                tasks=tasks,
                total_time_limit=5,
                project_name=project_name
            )
            
            results["search_results"] = search_result.get("search_results", [])
            print(f"  ✅ 搜索完成: {len(results['search_results'])} 份报告")
        
        # ===== 步骤6: 代码生成（使用 EngineerAgentV2 - 严格绑定 baseline）=====
        if directions and results.get("search_results"):
            print("\n👨‍💻 步骤6: 生成优化代码（严格绑定 baseline）...")
            
            from agents.v2.engineer_agent_v2 import EngineerAgentV2
            engineer = EngineerAgentV2(llm=self.llm)
            
            generated_items = []
            for i, direction in enumerate(directions, 1):
                print(f"  生成方向 {i}/{len(directions)}: {direction.get('name')}")
                
                code_result = await asyncio.to_thread(
                    engineer.generate_code_with_baseline,
                    direction=direction,
                    baseline_analysis=self.baseline_analysis,
                    search_results=results["search_results"],
                    original_code=code_content
                )
                
                # 验证代码是否符合约束（EngineerV2 内部验证）
                validation = code_result.get("validation", {})
                if validation.get("valid"):
                    print(f"    ✅ 基础验证通过")
                else:
                    warnings = validation.get("warnings", [])
                    print(f"    ⚠️ 代码警告: {warnings[0] if warnings else '需要检查'}")
                
                # 额外的代码约束验证
                from core.code_constraints import validate_code
                constraint_validation = validate_code(
                    generated_code=code_result.get("main_code", ""),
                    baseline_code=code_content,
                    strict_mode=False
                )
                
                if constraint_validation.get("valid"):
                    print(f"    ✅ 约束验证通过 (评分: {constraint_validation.get('score', 0):.0f}/100)")
                else:
                    print(f"    ❌ 约束验证失败")
                    violations = constraint_validation.get("violations", [])
                    for v in violations[:2]:
                        print(f"       - [{v['level']}] {v['message']}")
                
                # 合并验证结果
                code_result["constraint_validation"] = constraint_validation
                
                generated_items.append({
                    "direction": direction.get("name"),
                    **code_result
                })
            
            # 保存代码
            if generated_items:
                saved_files = await asyncio.to_thread(
                    engineer.save_generated_code,
                    generated_items=generated_items,
                    original_code=code_content
                )
                print(f"  ✅ 生成完成: {len(generated_items)} 组代码")
                print(f"     保存文件: {len(saved_files)} 个")
            
            results["generated_code"] = {
                "generated_items": generated_items,
                "total_count": len(generated_items)
            }
        
        print(f"\n{'='*70}")
        print(f"✨ 工作流执行完成")
        print(f"{'='*70}")
        
        return results
    
    def _format_baseline_for_prompt(self, analysis: Dict) -> str:
        """格式化 baseline 分析用于提示词"""
        if not analysis:
            return "未提供baseline分析"
        
        lines = []
        
        # 框架
        framework = analysis.get("framework", "Unknown")
        lines.append(f"框架: {framework}")
        
        # 数据流程
        data = analysis.get("data_pipeline", {})
        if data:
            lines.append(f"数据流程: {data.get('dataset_class', 'Unknown')} → DataLoader")
            lines.append(f"  Transforms: {', '.join(data.get('transforms', [])[:5])}")
            lines.append(f"  插入点: {', '.join(data.get('insertion_points', []))}")
        
        # 模型
        model = analysis.get("model_architecture", {})
        if model:
            lines.append(f"模型: {model.get('backbone', 'Unknown')} (预训练: {model.get('backbone_pretrained')})")
            lines.append(f"  损失函数: {model.get('loss_function', 'Unknown')}")
        
        # 训练
        train = analysis.get("training_config", {})
        if train:
            lines.append(f"训练: {train.get('optimizer', 'Unknown')} + {train.get('scheduler', 'None')}")
        
        # 优化机会
        opportunities = analysis.get("optimization_opportunities", [])
        if opportunities:
            lines.append(f"检测到的优化机会:")
            for op in opportunities[:3]:
                lines.append(f"  - {op.get('location')}: {op.get('suggestion')}")
        
        return "\n".join(lines)
    
    def _format_eda_for_prompt(self, report) -> str:
        """格式化 EDA 报告用于提示词"""
        if not report:
            return "未提供EDA分析"
        
        lines = [f"数据类型: {report.data_type}"]
        
        # 音频特征
        if report.audio_features:
            af = report.audio_features
            lines.append(f"音频统计: 平均时长 {af.duration_mean:.1f}s, 采样率 {af.sample_rate_mode}Hz")
            if af.class_distribution:
                lines.append(f"类别分布: {len(af.class_distribution)} 类, 不平衡比 {af.class_imbalance_ratio:.1f}:1")
        
        # 图像特征
        if report.image_features:
            imgf = report.image_features
            lines.append(f"图像尺寸: {imgf.size_mean[0]:.0f}x{imgf.size_mean[1]:.0f}")
        
        # 表格特征
        if report.tabular_features:
            tf = report.tabular_features
            lines.append(f"表格: {tf.n_rows} 行 x {tf.n_columns} 列")
        
        # 问题
        if report.issues:
            lines.append("检测到的问题:")
            for issue in report.issues[:3]:
                lines.append(f"  - {issue.get('message')}")
        
        # 建议
        if report.optimization_suggestions:
            lines.append("系统建议:")
            for sugg in report.optimization_suggestions[:3]:
                lines.append(f"  - {sugg.get('category')}: {sugg.get('suggestion')}")
        
        return "\n".join(lines)
    
    def _format_eda_summary(self, report) -> str:
        """格式化 EDA 摘要"""
        if not report:
            return ""
        
        summary = f"数据类型: {report.data_type}, 文件数: {report.file_count}"
        
        if report.audio_features and report.audio_features.class_distribution:
            summary += f", 类别数: {len(report.audio_features.class_distribution)}"
        
        return summary


# 便捷函数
async def run_enhanced_workflow(
    llm,
    project_name: str,
    html_content: str = "",
    code_content: str = "",
    data_path: str = "",
    instruction: str = "",
    enable_constraint_check: bool = True
) -> Dict:
    """
    便捷函数：运行增强版工作流
    
    示例：
        results = await run_enhanced_workflow(
            llm=llm,
            project_name="birdclef",
            html_content=html_content,
            code_content=code_content,
            data_path="./data/train",
            instruction="优化音频分类模型",
            enable_constraint_check=True
        )
    """
    workflow = EnhancedOptimizationWorkflow(
        llm=llm,
        enable_constraint_check=enable_constraint_check
    )
    
    return await workflow.run(
        project_name=project_name,
        html_content=html_content,
        code_content=code_content,
        data_path=data_path,
        instruction=instruction
    )
