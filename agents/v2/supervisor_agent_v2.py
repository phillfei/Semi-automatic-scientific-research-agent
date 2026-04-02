"""
Supervisor Agent V2 - 使用配置系统
支持动态行为和特性开关
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from evoagentx.agents import Agent
from evoagentx.tools import Toolkit

from config.feature_flags import feature_enabled, Feature
from config.config_manager import get_config
from config.agent_profiles import get_profile
from utils.agent_logger import get_agent_logger, log_agent_method


class SupervisorAgentV2(Agent):
    """
    Supervisor Agent V2 - 配置化版本
    
    特性：
    - 提示词模板化，支持变量替换
    - 功能模块化（EDA、历史分析可开关）
    - 行为可配置（方向数量、关键词过滤等）
    - 支持自定义提示词（用于增强版工作流）
    """
    
    def __init__(self, llm, project_manager=None, profile_name: str = "Supervisor", custom_prompt: str = None):
        # 先加载配置（不赋值给self）
        profile = get_profile(profile_name)
        config = get_config()
        
        # 从配置获取行为参数
        behaviors = profile.get_behavior('behaviors', {}) if profile else {}
        max_directions = behaviors.get('max_directions', 3)
        enable_eda = feature_enabled(Feature.SUPERVISOR_EDA) and behaviors.get('enable_eda', True)
        enable_history = feature_enabled(Feature.SUPERVISOR_HISTORY) and behaviors.get('enable_history', True)
        banned_keywords = behaviors.get('banned_keywords', [])
        
        # 构建系统提示词
        if custom_prompt:
            system_prompt = custom_prompt
        else:
            # 使用本地变量构建提示词
            if not profile:
                system_prompt = "你是主管Agent"
            else:
                variables = {
                    'max_directions': max_directions,
                    'data_type': '未知',
                    'project_type': config.get('custom.project_type', '通用')
                }
                system_prompt = profile.get_system_prompt(**variables)
        
        # 先调用父类初始化（Pydantic v2 要求）
        super().__init__(
            name=profile.name if profile else "Supervisor",
            description=profile.description if profile else "主管Agent",
            llm=llm,
            system_prompt=system_prompt
        )
        
        # 父类初始化完成后再赋值给 self
        self.profile = profile
        self.config = config
        self.logger = get_agent_logger()
        self.project_manager = project_manager
        self.max_directions = max_directions
        self.enable_eda = enable_eda
        self.enable_history = enable_history
        self.banned_keywords = banned_keywords
    
    def _build_system_prompt(self) -> str:
        """从配置构建系统提示词"""
        if not self.profile:
            return "你是主管Agent"
        
        # 获取变量
        variables = {
            'max_directions': self.max_directions,
            'data_type': '未知',
            'project_type': self.config.get('custom.project_type', '通用')
        }
        
        # 使用配置模板
        return self.profile.get_system_prompt(**variables)
    
    @log_agent_method("name")
    def initialize_project(self, project_name, html_content="", data_sample_content="",
                          data_sample_path="", data_sample_folder="", data_sample_info="",
                          code_content="", instruction=""):
        """
        初始化项目 - 两步流程
        1. HTML提取 + EDA分析（project_context）
        2. DirectionSelector基于历史知识库选择方向
        """
        print(f"\n🎯 Supervisor: 开始深度研究项目 '{project_name}'")
        
        # ========== 步骤1: 提取HTML关键信息 + EDA分析 ==========
        print("\n📋 步骤1: 提取赛题信息并进行EDA分析...")
        
        # 1.1 提取HTML关键信息
        project_context = self._extract_project_context(html_content)
        
        # 1.2 EDA分析
        eda_results = None
        key_findings = []
        if self.enable_eda:
            eda_results = self._perform_eda(
                data_sample_content, data_sample_path, data_sample_folder, data_sample_info
            )
            if eda_results:
                key_findings = self._extract_key_findings(eda_results)
                print(f"  ✅ EDA完成: 发现 {len(key_findings)} 个关键问题")
        
        # 1.3 Baseline代码分析
        baseline_analysis = self._quick_analyze_baseline(code_content)
        
        # ========== 步骤2: DirectionSelector选择优化方向 ==========
        print("\n🎯 步骤2: DirectionSelector基于分析选择优化方向...")
        
        # 2.1 加载历史反馈
        historical_feedback = []
        if self.enable_history and self.project_manager:
            historical_feedback = self._load_historical_feedback(project_name)
            if historical_feedback:
                print(f"  📊 已加载 {len(historical_feedback)} 条历史反馈")
        
        # 2.2 调用DirectionSelectorAgent
        from agents.v2.direction_selector import DirectionSelectorAgent
        direction_selector = DirectionSelectorAgent(self.llm, self.project_manager)
        
        selection_result = direction_selector.select_directions(
            project_context=project_context,
            key_findings=key_findings,
            baseline_analysis=baseline_analysis,
            history=historical_feedback,
            max_directions=self.max_directions
        )
        
        selected_directions = selection_result.get("selected_directions", [])
        
        print(f"  ✅ 选择完成: {len(selected_directions)} 个优化方向")
        for d in selected_directions:
            print(f"     - {d.get('name')} (置信度 {d.get('confidence', 'medium')})")
        
        # 构建最终分析结果
        analysis = {
            "project_name": project_name,
            "project_context": project_context,
            "eda_results": eda_results,
            "key_findings": key_findings,
            "baseline_analysis": baseline_analysis,
            "optimization_directions": selected_directions,
            "directions": selected_directions,  # 兼容旧字段
            "selection_reasoning": selection_result.get("reasoning", ""),
            "excluded_methods": selection_result.get("excluded_methods", [])
        }
        
        return analysis
    
    def _extract_project_context(self, html_content: str) -> Dict:
        """从HTML提取项目上下文"""
        import re
        
        # 简化提取：取前2000字符，移除HTML标签
        text = html_content[:3000] if html_content else ""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # 尝试提取关键信息（简化版）
        context = {
            "competition": "BirdCLEF+ 2026" if "birdclef" in text.lower() else "未知竞赛",
            "task_type": "Audio Classification" if "audio" in text.lower() or "bird" in text.lower() else "未知任务",
            "evaluation_metric": "AUC/mAP" if "auc" in text.lower() or "map" in text.lower() else "未知",
            "data_characteristics": "Audio data with bird species labels",
            "raw_html_summary": text[:500]
        }
        
        return context
    
    def _extract_key_findings(self, eda_results) -> List[str]:
        """从EDA结果提取关键发现"""
        findings = []
        
        if hasattr(eda_results, 'issues') and eda_results.issues:
            for issue in eda_results.issues[:3]:
                findings.append(issue.get('message', ''))
        
        if hasattr(eda_results, 'optimization_suggestions') and eda_results.optimization_suggestions:
            for sugg in eda_results.optimization_suggestions[:3]:
                findings.append(f"{sugg.get('category', '')}: {sugg.get('suggestion', '')}")
        
        if hasattr(eda_results, 'audio_features') and eda_results.audio_features:
            af = eda_results.audio_features
            if af.class_imbalance_ratio > 10:
                findings.append(f"严重类别不平衡: 比例 {af.class_imbalance_ratio:.1f}:1")
        
        return findings
    
    def _quick_analyze_baseline(self, code_content: str) -> Dict:
        """快速分析baseline代码"""
        import re
        
        return {
            "framework": "PyTorch" if "import torch" in code_content else "TensorFlow" if "tensorflow" in code_content else "Unknown",
            "has_augmentation": bool(re.search(r'augment|Augment|Mixup|CutMix', code_content)),
            "loss_function": "CrossEntropy" if "CrossEntropyLoss" in code_content else "Unknown",
            "code_length": len(code_content)
        }
    
    def _load_historical_feedback(self, project_name: str) -> List[Dict]:
        """加载历史反馈"""
        if not self.project_manager:
            return []
        
        history_limit = self.config.get('agent.supervisor_history_limit', 5)
        
        try:
            history = self.project_manager.get_history(project_name, limit=history_limit)
            feedback_list = [
                h for h in history 
                if 'metrics' in h or 'test_results' in h or 'generated_items_count' in h
            ]
            self.logger.log_step(
                "Supervisor", "_load_historical_feedback", 
                f"加载 {len(feedback_list)} 条历史反馈"
            )
            return feedback_list
        except Exception as e:
            self.logger.log_agent_error("Supervisor", "_load_historical_feedback", e)
            return []
    
    def _perform_eda(self, data_sample, data_sample_path, data_sample_folder, data_sample_info):
        """执行 EDA - 根据配置调整深度"""
        # 检查高级 EDA 特性
        advanced_eda = feature_enabled(Feature.ADVANCED_EDA)
        sample_size = self.config.get('agent.supervisor_eda_sample_size', 5)
        
        results = {"files_analyzed": [], "summary": "", "details": {}, "advanced": advanced_eda}
        
        try:
            # 分析文件夹...
            if data_sample_folder:
                folder = Path(data_sample_folder)
                if folder.exists():
                    files = [f for f in folder.rglob("*") if f.is_file()]
                    results["details"]["folder_path"] = str(data_sample_folder)
                    results["details"]["total_files"] = len(files)
                    
                    # 文件类型分布
                    ext_counts = {}
                    for f in files:
                        ext = f.suffix.lower()
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1
                    results["details"]["file_types"] = ext_counts
                    
                    # 采样分析
                    sample_files = []
                    extensions = [".csv", ".json", ".txt", ".ogg", ".wav", ".mp3", ".npz", ".npy"]
                    for ext in extensions:
                        candidates = [f for f in files if f.suffix.lower() == ext]
                        if candidates:
                            sample_files.extend(candidates[:2])
                        if len(sample_files) >= sample_size:
                            break
                    
                    for sf in sample_files[:sample_size]:
                        file_eda = self._analyze_single_file(sf, advanced=advanced_eda)
                        if file_eda:
                            results["files_analyzed"].append(file_eda)
            
            # 分析单个文件...
            elif data_sample_path:
                path = Path(data_sample_path)
                if path.exists():
                    file_eda = self._analyze_single_file(path, advanced=advanced_eda)
                    if file_eda:
                        results["files_analyzed"].append(file_eda)
            
            # 分析文本内容...
            elif data_sample:
                text_eda = self._analyze_text_sample(data_sample)
                if text_eda:
                    results["files_analyzed"].append(text_eda)
            
            # 生成摘要
            if results["files_analyzed"]:
                summaries = [
                    f"{fa.get('filename', 'unknown')}: {fa.get('summary', '')}"
                    for fa in results["files_analyzed"]
                ]
                results["summary"] = "; ".join(summaries)
            
            return results
            
        except Exception as e:
            self.logger.log_agent_error("Supervisor", "_perform_eda", e)
            return {"error": str(e), "summary": "EDA分析失败"}
    
    def _analyze_single_file(self, file_path: Path, advanced: bool = False) -> Optional[Dict]:
        """分析单个文件 - 根据 advanced 参数调整深度"""
        ext = file_path.suffix.lower()
        result = {"filename": file_path.name, "type": ext, "summary": ""}
        
        try:
            if ext in [".csv", ".txt"]:
                import pandas as pd
                if ext == ".csv":
                    df = pd.read_csv(file_path, nrows=1000)
                else:
                    df = pd.read_csv(file_path, sep=None, engine='python', nrows=1000)
                
                result["shape"] = list(df.shape)
                result["columns"] = list(df.columns.astype(str))
                result["summary"] = f"表格数据 {df.shape[0]}行x{df.shape[1]}列"
                
                # 高级分析
                if advanced:
                    result["dtypes"] = {str(k): str(v) for k, v in df.dtypes.to_dict().items()}
                    result["missing_ratio"] = {
                        str(k): round(v, 4) 
                        for k, v in (df.isnull().mean()).to_dict().items() if v > 0
                    }
                    result["describe"] = df.describe(include='all').to_dict()
                
            elif ext in [".ogg", ".wav", ".mp3"]:
                import soundfile as sf
                info = sf.info(str(file_path))
                result["duration"] = round(info.duration, 2)
                result["sample_rate"] = info.samplerate
                result["channels"] = info.channels
                result["summary"] = f"音频文件 时长{result['duration']}s 采样率{info.samplerate}Hz"
                
                # 高级音频分析
                if advanced:
                    try:
                        y, sr = sf.read(str(file_path), dtype='float32')
                        if y.ndim == 2:
                            y = y.mean(axis=1)
                        result["rms"] = round(float((y ** 2).mean() ** 0.5), 6)
                        result["max_amp"] = round(float(y.max()), 6)
                        result["min_amp"] = round(float(y.min()), 6)
                    except Exception:
                        pass
                        
            elif ext in [".npz", ".npy"]:
                import numpy as np
                if ext == ".npy":
                    arr = np.load(file_path, allow_pickle=True)
                    result["shape"] = list(arr.shape) if hasattr(arr, 'shape') else [len(arr)]
                    result["dtype"] = str(arr.dtype)
                    result["summary"] = f"Numpy数组 shape={result['shape']}"
                else:
                    data = np.load(file_path, allow_pickle=True)
                    result["files"] = list(data.files)
                    result["summary"] = f"NPZ文件 包含{len(data.files)}个数组"
                    
        except Exception as e:
            result["summary"] = f"文件解析失败: {e}"
            result["error"] = str(e)
        
        return result
    
    def _analyze_text_sample(self, text: str) -> Dict:
        """分析文本样本"""
        lines = text.strip().split('\n')
        result = {
            "filename": "text_sample",
            "type": "text",
            "line_count": len(lines),
            "char_count": len(text),
            "summary": f"文本样本 {len(lines)}行 {len(text)}字符"
        }
        
        # 尝试判断是否是CSV
        if len(lines) > 1:
            first_line = lines[0]
            comma_count = first_line.count(',')
            if comma_count > 2:
                result["likely_format"] = "CSV"
                result["summary"] += f", 可能是CSV格式({comma_count}个逗号)"
        
        return result
    
    def _build_research_prompt(self, html, data_sample, data_sample_path, data_sample_folder,
                               data_sample_info, code, instruction, history, eda_results):
        """构建研究提示词 - 结构化分析流程"""
        
        # 构建已完成的分析结果摘要（避免LLM重复分析）
        analysis_summary = []
        
        # 1. HTML关键信息提取结果
        if html:
            analysis_summary.extend([
                "## 已完成分析 - 赛题关键信息",
                self._extract_html_key_info(html),
                ""
            ])
        
        # 2. EDA分析结果（已保存，无需重复分析）
        if eda_results:
            analysis_summary.extend([
                "## 已完成分析 - 数据探索(EDA)",
                self._format_eda_summary(eda_results),
                ""
            ])
        
        # 3. 历史优化反馈（知识库 + 精度参数）
        if history:
            analysis_summary.extend([
                "## 历史优化反馈与知识库",
                self._format_history_feedback(history),
                ""
            ])
        
        # 构建主提示词
        prompt_parts = [
            "# 代码优化项目深度研究分析",
            "",
            "## 你的任务",
            f"基于以下已完成的分析结果，确定 {self.max_directions} 个优化方向。",
            "",
            "## 约束条件（必须遵守）",
            "1. **禁止结构优化** - 不允许：",
            "   - 添加/修改网络层（如加Attention模块、Transformer层、CNN层）",
            "   - 修改网络深度/宽度",
            "   - 更换Backbone架构",
            "   - 添加新的模型组件",
            "",
            "2. **允许优化范围** - 仅限：",
            "   - 数据增强策略（SpecAugment、Mixup、CutMix等）",
            "   - 特征工程方法",
            "   - 损失函数改进（Focal Loss、Label Smoothing等）",
            "   - 训练策略优化（学习率调度、优化器参数、Warmup等）",
            "   - 后处理技术（TTA、集成方法、伪标签等）",
            "",
        ]
        
        # 添加已完成的分析结果
        prompt_parts.extend(analysis_summary)
        
        # 用户指令
        if instruction:
            prompt_parts.extend([
                "## 用户特殊要求",
                instruction,
                ""
            ])
        
        # Baseline代码（精简）
        if code:
            prompt_parts.extend([
                "## Baseline代码参考（识别可插入优化点）",
                f"```python\n{code[:2000]}\n```",
                ""
            ])
        
        # 输出格式要求
        prompt_parts.extend([
            "## 输出格式（必须严格遵循）",
            "",
            "```json",
            "{",
            '  "optimization_analysis": {',
            '    "project_context": {',
            '      "competition": "竞赛名称",',
            '      "task_type": "任务类型",',
            '      "data_characteristics": "数据特点总结",',
            '      "evaluation_metric": "评估指标"',
            '    },',
            '    "key_findings": [',
            '      "从EDA发现的关键问题",',
            '      "从EDA发现的关键问题"',
            '    ],',
            f'    "optimization_directions": [',
            "      {",
            '        "name": "优化方向名称（简洁，15字以内）",',
            '        "rationale": "详细理由：当前问题+此方法如何解決+预期效果",',
            '        "search_keywords": ["关键词", "关键词", "关键词"],',
            '        "target_module": "数据加载/损失函数/训练策略/后处理",',
            '        "estimated_impact": "预期提升（如AUC +0.02）"',
            "      }",
            f"      // 共 {self.max_directions} 个方向",
            "    ]",
            '  }',
            "}",
            "```",
            "",
            "## 注意事项",
            "1. 必须基于已提供的EDA结果，不要重复分析数据",
            "2. 如果有历史反馈，参考之前的精度参数避免重复尝试无效方法",
            "3. 每个方向必须有明确的实现路径，不能是泛泛的概念",
            "4. search_keywords 必须具体，便于搜索相关论文"
        ])
        
        return "\n".join(prompt_parts)
    
    def _extract_html_key_info(self, html: str) -> str:
        """提取HTML关键信息"""
        # 提取关键部分：竞赛类型、评估指标、数据描述
        key_sections = []
        
        # 简单的文本提取和截断
        text = html[:3000] if html else ""
        
        # 移除HTML标签
        import re
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return f"""竞赛页面关键信息（已提取）：
{text[:1500]}
...
（关键信息：竞赛类型、评估指标、数据规模、时间限制等已包含）"""
    
    def _format_eda_summary(self, eda_results) -> str:
        """格式化EDA摘要"""
        lines = ["数据探索分析结果："]
        
        if hasattr(eda_results, 'data_type'):
            lines.append(f"- 数据类型: {eda_results.data_type}")
        
        if hasattr(eda_results, 'file_count'):
            lines.append(f"- 文件数量: {eda_results.file_count}")
        
        if hasattr(eda_results, 'audio_features') and eda_results.audio_features:
            af = eda_results.audio_features
            lines.append(f"- 音频统计: 平均时长 {af.duration_mean:.1f}s, 采样率 {af.sample_rate_mode}Hz")
            if af.class_imbalance_ratio > 1:
                lines.append(f"- 类别不平衡: 比例 {af.class_imbalance_ratio:.1f}:1")
        
        if hasattr(eda_results, 'issues') and eda_results.issues:
            lines.append("- 发现的问题:")
            for issue in eda_results.issues[:3]:
                lines.append(f"  * {issue.get('message', '')}")
        
        if hasattr(eda_results, 'optimization_suggestions') and eda_results.optimization_suggestions:
            lines.append("- 系统建议:")
            for sugg in eda_results.optimization_suggestions[:3]:
                lines.append(f"  * {sugg.get('category', '')}: {sugg.get('suggestion', '')}")
        
        return "\n".join(lines)
    
    def _format_history_feedback(self, history: list) -> str:
        """格式化历史反馈"""
        lines = ["历史优化记录："]
        
        for i, h in enumerate(history[-3:], 1):  # 最近3条
            lines.append(f"\n{i}. 任务: {h.get('task_id', '未知')[:8]}...")
            
            # 提取精度参数
            if 'metrics' in h:
                lines.append(f"   精度: {h.get('metrics', {})}")
            
            # 提取优化方向
            if 'directions' in h:
                lines.append(f"   方向: {', '.join(h.get('directions', [])[:2])}")
            
            # 提取搜索结果复用信息
            if 'search_reports' in h:
                lines.append(f"   知识库: {len(h.get('search_reports', []))} 份报告")
        
        if not history:
            lines.append("（无历史记录 - 新项目）")
        
        return "\n".join(lines)
    
    def _parse_analysis(self, result: str) -> Dict:
        """解析分析结果"""
        import json
        import re
        
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                directions = parsed.get('optimization_directions', [])
                parsed["directions"] = directions
                return parsed
        except Exception as e:
            self.logger.log_agent_error("Supervisor", "_parse_analysis", e)
        
        return {
            "research_summary": result[:500],
            "directions": [],
            "optimization_directions": []
        }
    
    def _post_process_directions(self, analysis: Dict, eda_results) -> Dict:
        """后处理优化方向 - 根据配置过滤和调整"""
        directions = analysis.get("optimization_directions", analysis.get("directions", []))
        
        # 字段映射：LLM 可能返回不同的字段名，统一为标准字段
        for d in directions:
            # name / title 映射
            if "name" not in d and "title" in d:
                d["name"] = d["title"]
            if "name" not in d and "direction" in d:
                d["name"] = d["direction"]
            
            # rationale / description / reason 映射
            if "rationale" not in d:
                if "description" in d:
                    d["rationale"] = d["description"]
                elif "reason" in d:
                    d["rationale"] = d["reason"]
                else:
                    d["rationale"] = "优化模型性能"
            
            # search_keywords / keywords 映射
            if "search_keywords" not in d:
                if "keywords" in d:
                    d["search_keywords"] = d["keywords"]
                elif "key_words" in d:
                    d["search_keywords"] = d["key_words"]
                else:
                    # 从name 自动生成关键词
                    d["search_keywords"] = d.get("name", "optimization").replace(" ", ", ").split(", ")[:5]
            
            # target_module / module / target 映射
            if "target_module" not in d:
                if "module" in d:
                    d["target_module"] = d["module"]
                elif "target" in d:
                    d["target_module"] = d["target"]
                else:
                    # 根据方向内容推断
                    name_lower = d.get("name", "").lower()
                    if any(kw in name_lower for kw in ["数据", "增强", "augment", "预处理"]):
                        d["target_module"] = "数据加载"
                    elif any(kw in name_lower for kw in ["损失", "loss", "focal", "label"]):
                        d["target_module"] = "损失函数"
                    elif any(kw in name_lower for kw in ["训练", "优化器", "学习率", "scheduler"]):
                        d["target_module"] = "训练策略"
                    elif any(kw in name_lower for kw in ["tta", "后处理", "集成", "ensemble"]):
                        d["target_module"] = "后处理"
                    else:
                        d["target_module"] = "模型训练"
        
        # 过滤 banned keywords
        if self.banned_keywords:
            valid_directions = []
            for d in directions:
                name = d.get("name", "").lower()
                rationale = d.get("rationale", "").lower()
                combined = name + " " + rationale
                
                if any(bk.lower() in combined for bk in self.banned_keywords):
                    continue
                valid_directions.append(d)
            directions = valid_directions
        
        # 限制数量
        directions = directions[:self.max_directions]
        
        # 如果为空，补充默认方向
        if not directions:
            directions = self._generate_default_directions(analysis.get("data_type", ""))
        
        analysis["optimization_directions"] = directions
        analysis["directions"] = directions
        return analysis
    
    def _generate_default_directions(self, data_type: str) -> List[Dict]:
        """生成默认优化方向"""
        is_audio = "音频" in data_type or "audio" in data_type.lower()
        is_image = "图像" in data_type or "image" in data_type.lower()
        
        if is_audio:
            return [
                {
                    "name": "音频数据增强策略",
                    "rationale": "通过SpecAugment等增强提升泛化能力",
                    "search_keywords": ["audio augmentation", "SpecAugment"],
                    "target_module": "数据加载"
                }
            ]
        elif is_image:
            return [
                {
                    "name": "图像数据增强",
                    "rationale": "通过Mixup、CutMix提升泛化",
                    "search_keywords": ["Mixup", "CutMix", "image augmentation"],
                    "target_module": "数据加载"
                }
            ]
        else:
            return [
                {
                    "name": "数据增强与正则化",
                    "rationale": "减少过拟合",
                    "search_keywords": ["data augmentation", "regularization"],
                    "target_module": "数据加载"
                }
            ]