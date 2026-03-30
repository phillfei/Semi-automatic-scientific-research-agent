"""
主管Agent - 基于 EvoAgentX
负责：深度研究、确定方向、协调全局
"""

from evoagentx.agents import Agent
from utils.agent_logger import get_agent_logger, log_agent_method
import time
from pathlib import Path


class SupervisorAgent(Agent):
    """主管Agent"""
    
    def __init__(self, llm, project_manager=None):
        super().__init__(
            name="Supervisor",
            description="主管Agent，负责深度研究、确定优化方向、协调全局",
            llm=llm,
            system_prompt="""你是主管Agent，负责：
1. 深度分析用户上传的HTML规划和代码
2. 进行EDA数据分析（如果有数据文件）
3. 确定最多3个优化方向
4. 协调其他Agent工作
5. 基于历史反馈做决策

**重要限制 - 优化方向选择原则**：
1. **禁止**从调整模型结构（如修改网络层数、改变模型架构、设计新模型）入手
2. 优化方向应聚焦于：数据增强、特征工程、损失函数、训练策略、集成方法、后处理等
3. 优先选择数据层面和训练策略层面的优化，而非模型架构层面的修改
4. 保持模型骨干网络不变，关注数据流和训练流程的改进

输出格式：
- 研究总结
- 优化方向（最多3个，每个包含名称、理由、关键词）
- EDA分析结果（如有数据）"""
        )
        self.project_manager = project_manager
        self.logger = get_agent_logger()
    
    @log_agent_method("name")
    def initialize_project(self, project_name, html_content="", data_sample_content="",
                          data_sample_path="", data_sample_folder="", data_sample_info="",
                          code_content="", instruction=""):
        """初始化项目"""
        print(f"\n🎯 Supervisor: 开始深度研究项目 '{project_name}'")
        
        # 加载历史反馈
        historical_feedback = []
        if self.project_manager:
            historical_feedback = self._load_historical_feedback(project_name)
            if historical_feedback:
                print(f"  📊 已加载 {len(historical_feedback)} 条历史反馈")
        
        # 执行真实EDA
        eda_results = self._perform_eda(
            data_sample_content, data_sample_path, data_sample_folder, data_sample_info
        )
        if eda_results:
            print(f"  ✅ EDA完成: {eda_results.get('summary', '')[:100]}")
        
        # 构建提示词
        prompt = self._build_research_prompt(
            html_content, data_sample_content, data_sample_path, data_sample_folder,
            data_sample_info, code_content, instruction, historical_feedback, eda_results
        )
        
        # 调用LLM进行深度研究
        start_time = time.time()
        result = self.llm.generate(prompt=prompt)
        duration_ms = (time.time() - start_time) * 1000
        
        self.logger.log_llm_call("Supervisor", len(prompt), len(result), duration_ms)
        
        # 解析结果
        analysis = self._parse_analysis(result)
        
        # 后处理：确保方向符合要求
        analysis = self._post_process_directions(analysis, eda_results)
        
        print(f"  ✅ 确定 {len(analysis.get('directions', []))} 个优化方向")
        return analysis
    
    def _load_historical_feedback(self, project_name):
        """加载历史反馈"""
        if not self.project_manager:
            return []
        try:
            history = self.project_manager.get_history(project_name, limit=5)
            feedback_list = [h for h in history if 'metrics' in h or 'test_results' in h or 'generated_items_count' in h]
            self.logger.log_step("Supervisor", "_load_historical_feedback", 
                                f"加载 {len(feedback_list)} 条历史反馈")
            return feedback_list
        except Exception as e:
            self.logger.log_agent_error("Supervisor", "_load_historical_feedback", e)
            return []
    
    def _perform_eda(self, data_sample, data_sample_path, data_sample_folder, data_sample_info):
        """执行真实EDA分析"""
        results = {"files_analyzed": [], "summary": "", "details": {}}
        
        try:
            # 分析文件夹
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
                    
                    # 采样分析几个文件
                    sample_files = []
                    for ext in [".csv", ".json", ".txt", ".ogg", ".wav", ".mp3", ".npz", ".npy", ".parquet", ".xlsx"]:
                        candidates = [f for f in files if f.suffix.lower() == ext]
                        if candidates:
                            sample_files.extend(candidates[:2])
                        if len(sample_files) >= 5:
                            break
                    if not sample_files:
                        sample_files = files[:5]
                    
                    for sf in sample_files:
                        file_eda = self._analyze_single_file(sf)
                        if file_eda:
                            results["files_analyzed"].append(file_eda)
            
            # 分析单个文件
            elif data_sample_path:
                path = Path(data_sample_path)
                if path.exists():
                    file_eda = self._analyze_single_file(path)
                    if file_eda:
                        results["files_analyzed"].append(file_eda)
            
            # 分析文本内容
            elif data_sample:
                text_eda = self._analyze_text_sample(data_sample)
                if text_eda:
                    results["files_analyzed"].append(text_eda)
            
            # 生成摘要
            if results["files_analyzed"]:
                summaries = []
                for fa in results["files_analyzed"]:
                    summaries.append(f"{fa.get('filename', 'unknown')}: {fa.get('summary', '')}")
                results["summary"] = "; ".join(summaries)
            
            return results
            
        except Exception as e:
            self.logger.log_agent_error("Supervisor", "_perform_eda", e)
            return {"error": str(e), "summary": "EDA分析失败"}
    
    def _analyze_single_file(self, file_path):
        """分析单个文件"""
        path = Path(file_path)
        ext = path.suffix.lower()
        result = {"filename": path.name, "type": ext, "summary": ""}
        
        try:
            if ext in [".csv", ".txt"]:
                import pandas as pd
                if ext == ".csv":
                    df = pd.read_csv(path, nrows=1000)
                else:
                    df = pd.read_csv(path, sep=None, engine='python', nrows=1000)
                result["shape"] = list(df.shape)
                result["columns"] = list(df.columns.astype(str))
                result["dtypes"] = {str(k): str(v) for k, v in df.dtypes.to_dict().items()}
                result["missing_ratio"] = {str(k): round(v, 4) for k, v in (df.isnull().mean()).to_dict().items() if v > 0}
                result["describe"] = df.describe(include='all').to_dict()
                result["head"] = df.head(5).to_dict('records')
                result["summary"] = f"表格数据 {df.shape[0]}行x{df.shape[1]}列, 列: {list(df.columns)}"
                
            elif ext == ".json":
                import pandas as pd
                import json
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    df = pd.json_normalize(data)
                    df = df.head(1000)
                    result["shape"] = list(df.shape)
                    result["columns"] = list(df.columns.astype(str))
                    result["summary"] = f"JSON列表数据 {len(data)}条记录, 展开后{df.shape[1]}列"
                else:
                    result["summary"] = f"JSON对象数据, 顶层键: {list(data.keys()) if isinstance(data, dict) else '非对象'}"
                    
            elif ext in [".parquet", ".xlsx"]:
                import pandas as pd
                if ext == ".parquet":
                    df = pd.read_parquet(path)
                else:
                    df = pd.read_excel(path)
                df = df.head(1000)
                result["shape"] = list(df.shape)
                result["columns"] = list(df.columns.astype(str))
                result["summary"] = f"表格数据 {df.shape[0]}行x{df.shape[1]}列"
                
            elif ext in [".ogg", ".wav", ".mp3"]:
                import soundfile as sf
                info = sf.info(str(path))
                result["duration"] = round(info.duration, 2)
                result["sample_rate"] = info.samplerate
                result["channels"] = info.channels
                result["frames"] = info.frames
                result["summary"] = f"音频文件 时长{result['duration']}s 采样率{info.samplerate}Hz 通道{info.channels}"
                
                # 读取部分数据计算波形统计
                try:
                    y, sr = sf.read(str(path), dtype='float32')
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
                    arr = np.load(path, allow_pickle=True)
                    result["shape"] = list(arr.shape) if hasattr(arr, 'shape') else [len(arr)]
                    result["dtype"] = str(arr.dtype)
                    result["summary"] = f"Numpy数组 shape={result['shape']} dtype={arr.dtype}"
                else:
                    data = np.load(path, allow_pickle=True)
                    result["files"] = list(data.files)
                    result["summary"] = f"NPZ文件 包含{len(data.files)}个数组: {data.files}"
                    
        except Exception as e:
            result["summary"] = f"文件解析失败: {e}"
            result["error"] = str(e)
        
        return result
    
    def _analyze_text_sample(self, text):
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
            tab_count = first_line.count('\t')
            if comma_count > 2 or tab_count > 2:
                result["likely_format"] = "CSV/TSV"
                result["summary"] += f", 首行{comma_count}个逗号分隔符"
        
        return result
    
    def _build_research_prompt(self, html, data_sample, data_sample_path, data_sample_folder,
                               data_sample_info, code, instruction, history, eda_results):
        """构建研究提示词"""
        prompt = f"""请对以下代码优化项目进行深度研究分析。

## 分析要求
1. 必须结合HTML赛题介绍的内容，深入分析项目特点、评估指标、数据特性
2. 必须基于下方提供的真实EDA结果进行分析，不要编造数据
3. 优化方向必须聚焦于**提升模型精度**或**提升任务性能**（如AUC、F1、准确率等），严禁提出"推理速度优化"、"代码重构"、"内存占用减少"等与精度/性能无关的方向
4. **重要限制**：优化方向**禁止**从调整模型结构入手（如修改网络层数、改变模型架构、设计新模型骨干），应聚焦于数据增强、特征工程、损失函数、训练策略、集成方法、后处理等
5. 每个优化方向必须具体、可落地，且与项目数据类型强相关

## 用户指令
{instruction}

## HTML规划/赛题介绍（必须仔细阅读并分析项目特点）
{html[:4000] if html else '无'}

## 事例数据文件信息
"""
        if data_sample_info:
            prompt += f"{data_sample_info}\n\n"
        elif data_sample_folder:
            prompt += f"数据文件夹路径: {data_sample_folder}\n\n"
        elif data_sample_path:
            prompt += f"文件路径: {data_sample_path}\n\n"
        
        if data_sample:
            prompt += f"""文件内容（前2000字符）:
```
{data_sample[:2000]}
```

"""
        elif not data_sample_info:
            prompt += "无文本内容数据\n\n"
        
        # 加入真实EDA结果
        if eda_results and eda_results.get("files_analyzed"):
            prompt += "## 真实EDA分析结果（基于实际数据文件读取）\n"
            prompt += f"总体摘要: {eda_results.get('summary', '')}\n\n"
            if eda_results.get("details", {}).get("file_types"):
                prompt += f"文件夹文件类型分布: {eda_results['details']['file_types']}\n"
                prompt += f"总文件数: {eda_results['details'].get('total_files', 'N/A')}\n\n"
            for i, fa in enumerate(eda_results["files_analyzed"][:5], 1):
                prompt += f"### 文件{i}: {fa.get('filename')}\n"
                prompt += f"- 类型: {fa.get('type')}\n"
                prompt += f"- 摘要: {fa.get('summary')}\n"
                # 加入关键细节
                for key in ["shape", "columns", "duration", "sample_rate", "channels", "rms", "dtype"]:
                    if key in fa:
                        prompt += f"- {key}: {fa[key]}\n"
                prompt += "\n"
        
        prompt += f"""## 代码内容
```python
{code[:3000] if code else '无'}
```

"""
        if history:
            prompt += "## 历史优化反馈\n"
            for i, h in enumerate(history[:3], 1):
                prompt += f"{i}. 任务: {h.get('task_id', '未知')}\n"
                if 'generated_items_count' in h:
                    prompt += f"   生成方向数: {h.get('generated_items_count', 0)}\n"
                if 'directions' in h:
                    prompt += f"   方向: {', '.join(str(d) for d in h.get('directions', []) if d)}\n"
                prompt += "\n"
        
        prompt += """

## 推荐优化方向类型（仅供参考，请结合项目实际选择，避免模型架构修改）
- 数据增强策略（如音频增强、Mixup、CutMix、SpecAugment等）
- 特征工程优化（如频谱特征提取优化、时域特征增强、嵌入特征改进）
- **注意：避免**模型架构修改（如增加网络层数、修改骨干网络结构）
- 损失函数优化（如Focal Loss、Label Smoothing、对比学习损失）
- 训练策略优化（如学习率调度、优化器选择、早停策略、梯度累积）
- 半监督/伪标签策略（如一致性正则化、自训练、知识蒸馏）
- 集成学习策略（如模型融合、Stacking、多折集成、快照集成）
- 交叉验证与评估策略（如GroupKFold、StratifiedKFold、OOF预测）
- 标签处理策略（如噪声标签修正、类别重平衡、标签平滑）
- 后处理优化（如测试时增强TTA、预测校准、阈值优化）

请提供：
1. **研究总结**：项目目标、现状、技术难点
2. **项目特点分析**：基于HTML内容分析竞赛/项目的核心特点、评估指标偏好、数据陷阱
3. **数据类型识别**：明确判断数据任务类型及依据
4. **优化方向**（最多3个，必须聚焦精度/性能提升，**禁止模型架构修改**）：
   - 方向名称（具体技术名称，禁止泛泛而谈）
   - 选择理由（结合EDA结果和项目特点，**明确说明为何不涉及模型结构修改**）
   - 搜索关键词（3-5个）
   - 预期修改的代码模块（**应为数据加载、损失函数、训练流程、后处理等非模型结构模块**）
   - 预期对精度/性能的影响
5. **EDA分析**：基于真实EDA结果的数据特征、质量问题、优化建议

输出JSON格式：
{
  "research_summary": "总结",
  "project_characteristics": "项目特点分析",
  "data_type": "音频分类/图像识别/表格预测/NLP等",
  "data_type_reason": "判断依据",
  "optimization_directions": [
    {
      "name": "具体技术方向名称",
      "rationale": "结合EDA和项目特点的理由（明确说明为何不修改模型结构）",
      "search_keywords": ["关键词1", "关键词2"],
      "target_module": "预期修改的代码模块（数据加载/损失函数/训练流程/后处理等，禁止模型结构）",
      "expected_impact": "预期精度/性能影响"
    }
  ],
  "eda_analysis": "基于真实数据的分析结果"
}"""
        return prompt
    
    def _post_process_directions(self, analysis, eda_results):
        """后处理优化方向，确保符合要求"""
        directions = analysis.get("optimization_directions", analysis.get("directions", []))
        
        # 过滤掉不符合要求的方向（禁止模型架构修改和性能无关方向）
        banned_keywords = ["推理速度", "inference speed", "latency", "延迟", "内存占用", "memory usage",
                          "代码重构", "code refactoring", "可读性", "readability",
                          "模型架构", "model architecture", "骨干网络", "backbone", "网络层数", "网络深度",
                          "增加层", "add layer", "修改结构", "修改模型", "注意力机制", "attention mechanism",
                          "Transformer层", "CNN层", "全连接层", "网络宽度", "模型复杂度"]
        
        valid_directions = []
        for d in directions:
            name = d.get("name", "")
            rationale = d.get("rationale", "")
            combined = name.lower() + " " + rationale.lower()
            
            if any(bk in combined for bk in banned_keywords):
                continue
            valid_directions.append(d)
        
        # 如果过滤后没有方向，补充默认方向
        if not valid_directions:
            data_type = analysis.get("data_type", "")
            is_audio = "音频" in data_type or "audio" in data_type.lower()
            is_tabular = "表格" in data_type or "tabular" in data_type.lower() or "预测" in data_type
            is_image = "图像" in data_type or "image" in data_type.lower()
            
            if is_audio:
                valid_directions = [
                    {
                        "name": "音频数据增强策略",
                        "rationale": "通过SpecAugment、时间拉伸、 pitch shift等增强提升模型泛化能力",
                        "search_keywords": ["audio augmentation", "SpecAugment", "bird sound classification"],
                        "target_module": "数据加载/预处理",
                        "expected_impact": "提升验证集精度和泛化能力"
                    },
                    {
                        "name": "频谱特征工程优化",
                        "rationale": "优化梅尔频谱参数和特征提取策略，更好地表征鸟类鸣叫特征",
                        "search_keywords": ["mel spectrogram optimization", "audio feature extraction", "bird sound features"],
                        "target_module": "特征提取模块",
                        "expected_impact": "提升分类准确率和AUC"
                    }
                ]
            elif is_tabular:
                valid_directions = [
                    {
                        "name": "特征工程与选择优化",
                        "rationale": "基于EDA发现的关键特征构建高阶特征并筛选",
                        "search_keywords": ["feature engineering", "feature selection", "tabular data"],
                        "target_module": "特征工程模块",
                        "expected_impact": "提升模型预测精度"
                    },
                    {
                        "name": "集成学习与模型融合",
                        "rationale": "通过多模型集成降低方差，提升预测稳定性",
                        "search_keywords": ["ensemble learning", "model stacking", "tabular ensemble"],
                        "target_module": "模型训练/预测",
                        "expected_impact": "提升AUC和F1分数"
                    }
                ]
            elif is_image:
                valid_directions = [
                    {
                        "name": "数据增强与Mixup策略",
                        "rationale": "通过高级增强和Mixup提升模型泛化",
                        "search_keywords": ["Mixup", "CutMix", "image augmentation"],
                        "target_module": "数据加载/预处理",
                        "expected_impact": "提升验证精度和泛化能力"
                    },
                    {
                        "name": "测试时增强TTA策略",
                        "rationale": "通过多尺度、多裁剪测试增强提升预测稳定性",
                        "search_keywords": ["test time augmentation", "TTA", "multi-scale inference"],
                        "target_module": "预测推理模块",
                        "expected_impact": "提升预测稳定性和准确率"
                    }
                ]
            else:
                valid_directions = [
                    {
                        "name": "数据增强与正则化策略",
                        "rationale": "通过增强和正则化减少过拟合",
                        "search_keywords": ["data augmentation", "regularization", "generalization"],
                        "target_module": "数据加载/训练流程",
                        "expected_impact": "提升验证集精度和泛化"
                    },
                    {
                        "name": "损失函数优化",
                        "rationale": "使用Focal Loss或Label Smoothing改善难例和校准",
                        "search_keywords": ["Focal Loss", "Label Smoothing", "classification"],
                        "target_module": "损失函数定义",
                        "expected_impact": "提升F1和准确率"
                    }
                ]
        
        analysis["optimization_directions"] = valid_directions[:3]
        analysis["directions"] = valid_directions[:3]
        return analysis
    
    def _parse_analysis(self, result):
        """解析分析结果"""
        import json
        import re
        
        self.logger.log_step("Supervisor", "_parse_analysis", "开始解析分析结果")
        
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                directions = parsed.get('optimization_directions', [])
                self.logger.log_step("Supervisor", "_parse_analysis", 
                                    f"成功解析，找到 {len(directions)} 个优化方向")
                # 同时提供 directions 字段以兼容旧代码
                parsed["directions"] = directions
                return parsed
        except Exception as e:
            self.logger.log_agent_error("Supervisor", "_parse_analysis", e)
            pass
        
        # 默认返回
        return {
            "research_summary": result[:500],
            "project_characteristics": "",
            "optimization_directions": [],
            "eda_analysis": "",
            "directions": []
        }
    
    @log_agent_method("name")
    def receive_search_report(self, search_report):
        """接收Search Agent的汇报"""
        print("\n🎯 Supervisor: 接收Search Agent汇报")
        self.logger.log_step("Supervisor", "receive_search_report", 
                            "接收搜索汇报", {"report": str(search_report)[:200]})
        
        best_methods = search_report.get("best_methods", [])
        confidence = search_report.get("confidence", "medium")
        
        if best_methods:
            print(f"  ⭐ 最推荐方法: {best_methods[0].get('method_name', '未知')}")
            print(f"     信心等级: {confidence}")
            print(f"     预期效果: {best_methods[0].get('expected_effect', '')}")
        
        # 将搜索汇报存入内部状态，供后续决策使用
        self.latest_search_report = search_report
        return {
            "acknowledged": True,
            "confidence": confidence,
            "preferred_direction": best_methods[0].get("direction_name") if best_methods else None
        }
    
    @log_agent_method("name")
    def receive_test_results(self, test_results):
        """接收测试结果并决策"""
        print("\n🎯 Supervisor: 分析测试结果")
        self.logger.log_step("Supervisor", "receive_test_results", 
                            "分析测试结果", {"results": str(test_results)[:200]})
        
        prompt = f"""基于以下测试结果，决策下一步行动：

测试结果：{test_results}

请判断：
1. 是否达到预期目标？
2. 是否需要继续优化？
3. 是否需要调整方向？
4. 下一步建议行动

输出JSON：
{{
  "decision": "决策说明",
  "should_continue": true/false,
  "next_actions": ["行动1", "行动2"]
}}"""
        
        start_time = time.time()
        result = self.llm.generate(prompt=prompt)
        duration_ms = (time.time() - start_time) * 1000
        
        self.logger.log_llm_call("Supervisor", len(prompt), len(result), duration_ms)
        
        import json
        import re
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "decision": "建议继续优化",
            "should_continue": True,
            "next_actions": ["调整参数", "尝试其他方向"]
        }
