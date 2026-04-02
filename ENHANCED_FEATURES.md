# EvoAgentX 增强版功能说明

## 概述

为了解决 AI "跑偏" 问题（生成的优化方向与 baseline 代码脱节、不符合赛题约束），我们引入了以下增强功能：

## 🆕 新增组件

### 1. ConstraintAgent - 约束检查器

**文件**: `agents/v2/constraint_agent.py`

**职责**: 三重校验防止 AI 跑偏

```python
from agents.v2.constraint_agent import ConstraintAgent

checker = ConstraintAgent(llm)
result = checker.validate_directions(
    directions=directions,
    baseline_analysis=baseline_analysis
)

# 结果包含：
# - valid_directions: 通过校验的方向
# - rejected_directions: 被拒绝的方向及原因
# - check_results: 详细检查报告
```

**检查维度**:
1. **约束符合性**: 是否违反"不涉及模型架构"等硬性约束
2. **Baseline 关联性**: 是否与 baseline 代码结构相关
3. **可行性**: 技术路线是否可行

**配置**:
```yaml
features:
  constraint_check: true

agent:
  constraint_strictness: "medium"  # low/medium/high
```

---

### 2. BaselineAnalyzer - 深度代码分析器

**文件**: `agents/v2/baseline_analyzer.py`

**职责**: 解析 baseline 代码，提取关键架构信息

```python
from agents.v2.baseline_analyzer import BaselineAnalyzer

analyzer = BaselineAnalyzer(llm)
analysis = analyzer.analyze(code_content)

# 结果包含：
# - data_pipeline: 数据流程
# - model_architecture: 模型架构
# - training_config: 训练配置
# - optimization_opportunities: 优化机会
```

**分析维度**:

| 维度 | 提取信息 | 用途 |
|------|----------|------|
| **数据流** | Dataset类、Transforms、DataLoader | 确定数据增强插入点 |
| **模型架构** | Backbone、Head、Loss Function | 约束优化方向 |
| **训练循环** | Optimizer、Scheduler、Validation | 训练策略优化 |
| **优化机会** | 缺失的增强、可改进的损失函数 | 指导方向选择 |

---

### 3. SmartEDA - 智能数据探索

**文件**: `data/smart_eda.py`

**职责**: 自动检测数据类型并进行深度分析

```python
from data.smart_eda import SmartEDA, quick_eda

# 完整分析
eda = SmartEDA(max_sample_size=100)
report = eda.explore("./data/train")

# 快速分析
report_dict = quick_eda("./data/train", max_samples=50)
```

**支持的数据类型**:
- **音频**: 采样率、时长、类别分布、不平衡检测
- **图像**: 尺寸、色彩、质量、类别不平衡
- **表格**: 缺失值、相关性、异常值

**自动生成的洞察**:
- 数据质量问题（类别不平衡、缺失值等）
- 针对性的优化建议

---

### 4. 增强版提示词模板

**文件**: `config/prompts_v2.py`

**特点**:
- 包含**约束检查清单**（逐项确认）
- 强制引用 **Baseline 架构信息**
- 强制基于 **EDA 结果**分析

```python
from config import get_supervisor_prompt_v2

prompt = get_supervisor_prompt_v2(
    max_directions=3,
    data_type="音频分类",
    evaluation_metric="AUC",
    baseline_analysis=baseline_summary,
    eda_results=eda_summary,
    html_content=html_content,
    code_content=code_content
)
```

---

## 🔄 增强版工作流

**文件**: `core/enhanced_workflow.py`

### 工作流顺序

```
用户输入
    ↓
BaselineAnalyzer (分析代码结构)
    ↓
SmartEDA (自动探索数据)
    ↓
Supervisor V2 (基于分析确定方向)
    ↓
ConstraintAgent (校验方向)
    ↓
Search (搜索技术方案)
    ↓
Engineer (生成代码)
    ↓
Output
```

### 使用方式

```python
from core.enhanced_workflow import run_enhanced_workflow

results = await run_enhanced_workflow(
    llm=llm,
    project_name="birdclef",
    html_content=html_content,
    code_content=code_content,
    data_path="./data/train",
    instruction="优化音频分类模型",
    enable_constraint_check=True
)

# 结果包含:
# - baseline_analysis: baseline 架构分析
# - eda_report: 数据探索报告
# - directions: 优化方向（已通过约束检查）
# - constraint_check: 约束检查详情
# - search_results: 搜索结果
# - generated_code: 生成的代码
```

---

## 📊 与原系统对比

| 功能 | 原系统 | 增强版 | 改进 |
|------|--------|--------|------|
| **Baseline 分析** | ❌ 无 | ✅ 深度解析 | 代码结构、数据流、模型架构 |
| **数据探索** | ❌ 基础文件统计 | ✅ 智能类型检测 | 音频/图像/表格专项分析 |
| **约束检查** | ❌ 提示词软约束 | ✅ 自动校验 | 三重检查，自动拒绝 |
| **跑偏检测** | ❌ 人工发现 | ✅ 自动拦截 | 实时检查，即时反馈 |
| **代码生成** | ❌ 独立生成 | ✅ 绑定 baseline | 强制增量修改模式 |
| **代码验证** | ❌ 无 | ✅ 多层约束验证 | 装饰器/继承/包装评分 |

---

## ⚙️ 配置指南

### 完整配置示例

```yaml
# evo_config.yaml

# ============= 特性开关 =============
features:
  # 核心增强功能
  constraint_check: true           # 启用约束检查
  baseline_analysis: true          # 启用 baseline 分析
  smart_eda: true                  # 启用智能 EDA
  
  # 调试
  debug_prompts: false

# ============= Agent 配置 =============
agent:
  # Supervisor
  supervisor_max_directions: 3
  
  # ConstraintAgent
  constraint_strictness: "medium"  # low/medium/high
  
  # SmartEDA
  eda_max_sample_size: 100
  eda_max_analysis_time: 60

# ============= 工作流配置 =============
workflow:
  enable_baseline_analysis: true
  enable_smart_eda: true
  enable_constraint_check: true
```

### 环境变量覆盖

```bash
# 快速开关功能
export EVO_FEATURE_CONSTRAINT_CHECK=true
export EVO_FEATURE_BASELINE_ANALYSIS=true
export EVO_FEATURE_SMART_EDA=true

# 调整参数
export EVO_AGENT_CONSTRAINT_STRICTNESS=high
export EVO_AGENT_EDA_MAX_SAMPLE_SIZE=200
```

---

## 🎯 使用场景

### 场景1: 约束检查失败，方向被拒绝

```
🎯 Supervisor: 确定优化方向
  - 方向1: SpecAugment数据增强 ✅
  - 方向2: 添加ResNet101骨干网络
  - 方向3: 优化推理速度

🔒 ConstraintAgent: 约束检查
  ✅ 通过: 2个
  ❌ 拒绝: 1个
     - 添加ResNet101骨干网络: 违反约束"不涉及模型架构修改"
     - 优化推理速度: 违反约束"不优化推理速度"
```

### 场景2: Baseline 分析指导方向选择

```
📊 BaselineAnalyzer 分析结果:
  - 框架: PyTorch
  - Backbone: ResNet50 (预训练)
  - 损失函数: CrossEntropyLoss
  - 优化机会: 未使用数据增强、学习率调度

🎯 Supervisor 基于分析确定方向:
  ✅ 方向1: 添加SpecAugment (插入点: Dataset.__getitem__)
  ✅ 方向2: 使用CosineAnnealing调度器 (替换现有scheduler)
```

### 场景3: SmartEDA 发现数据问题

```
🔬 SmartEDA 分析结果:
  - 数据类型: 音频
  - 类别数: 100
  - ⚠️ 类别不平衡: 100:1
  - ⚠️ 采样率不一致: 32000Hz / 44100Hz

💡 自动建议:
  - 使用 Focal Loss 改善类别不平衡
  - 统一重采样到 32000Hz
```

---

### 5. Engineer V2 - 严格绑定 Baseline 的代码生成

**文件**: `agents/v2/engineer_agent_v2.py`

**核心原则**：
1. **绝不修改 baseline 原有代码**
2. **只使用增量修改模式**：装饰器、继承、包装、回调
3. **强制 API 兼容**：不修改函数签名，不删除功能

**使用方式**：
```python
from agents.v2.engineer_agent_v2 import EngineerAgentV2

engineer = EngineerAgentV2(llm)
code_result = engineer.generate_code_with_baseline(
    direction=direction,
    baseline_analysis=baseline_analysis,
    search_results=search_results,
    original_code=original_code
)

# 结果包含:
# - main_code: 主代码（使用增量模式）
# - test_code: 测试代码
# - integration_guide: 详细的集成指南（JSON + Markdown）
# - validation: 自动验证结果
# - insertion_info: 具体的插入点信息
```

**增量修改模式**：

| 模式 | 适用场景 | 示例 |
|------|----------|------|
| **装饰器** | 数据增强、日志记录 | `@augment_decorator` |
| **继承扩展** | 修改损失、自定义数据集 | `class AugmentedDataset(BaseDataset)` |
| **函数包装** | 训练策略、后处理 | `wrapped_train = create_wrapped_trainer(original)` |
| **回调注入** | 训练过程自定义 | `callbacks=[CustomCallback()]` |

---

### 6. CodeConstraintValidator - 代码约束验证

**文件**: `core/code_constraints.py`

**职责**：三层防护确保代码不修改 baseline

```python
from core.code_constraints import validate_code

result = validate_code(
    generated_code=generated_code,
    baseline_code=baseline_code,
    strict_mode=True  # 严格模式
)

# 结果:
# - valid: 是否通过
# - score: 代码质量评分 (0-100)
# - violations: 违规列表
# - recommendations: 改进建议
```

**验证维度**：

| 检查项 | 级别 | 说明 |
|--------|------|------|
| 直接修改 baseline | ERROR | 检测到修改 baseline 函数/类 |
| 修改函数签名 | ERROR | 改变了参数列表 |
| 类名重名 | ERROR | 与 baseline 类重名 |
| 函数名重名 | WARNING | 可能与 baseline 函数冲突 |
| 修改全局变量 | WARNING | 建议通过配置传入 |
| 导入冲突 | WARNING | 库版本可能冲突 |
| 缺少增量模式 | WARNING | 未使用装饰器/继承/包装 |

**评分系统**：
```
基础分 100
- ERROR: -20
- WARNING: -10
+ 使用推荐模式: +10
```

**保存的文件结构**：
```
output/
└── timestamp_direction/
    ├── {direction}_patch.py       # 主代码
    ├── {direction}_test.py        # 测试代码
    ├── INTEGRATION_GUIDE.md       # 集成指南（Markdown）
    ├── INTEGRATION_GUIDE.json     # 集成指南（结构化）
    ├── baseline_backup.py         # baseline 备份
    └── integration_example.py     # 集成示例代码
```

---

## 📁 文件结构

```
evo_code_optimizer/
├── agents/v2/
│   ├── constraint_agent.py      # 约束检查器 ⭐新增
│   ├── baseline_analyzer.py     # 代码分析器 ⭐新增
│   ├── engineer_agent_v2.py     # 严格绑定 baseline 的代码生成器 ⭐新增
│   └── supervisor_agent_v2.py   # 增强版 Supervisor
├── data/
│   └── smart_eda.py             # 智能 EDA ⭐新增
├── core/
│   ├── enhanced_workflow.py     # 增强版工作流 ⭐新增
│   └── code_constraints.py      # 代码约束验证器 ⭐新增
├── config/
│   └── prompts_v2.py            # 增强提示词 ⭐新增
├── CODE_CONSTRAINTS.md          # 代码约束详细文档
├── example_enhanced_workflow.py # 使用示例
└── ENHANCED_FEATURES.md         # 本文档
```

---

## 🚀 快速开始

1. **安装依赖**:
```bash
pip install soundfile pillow  # 音频/图像分析
```

2. **运行示例**:
```bash
python example_enhanced_workflow.py
```

3. **集成到现有工作流**:
```python
from core.enhanced_workflow import run_enhanced_workflow

# 替换原来的工作流调用
results = await run_enhanced_workflow(...)
```

---

## ⚠️ 注意事项

1. **ConstraintAgent 会增加延迟**: 每个方向需要额外 ~1-2s 检查时间
2. **BaselineAnalyzer 依赖代码质量**: 对于高度封装的代码，分析可能不够准确
3. **SmartEDA 需要相应库**: 音频分析需要 `soundfile`，图像需要 `PIL`
4. **建议渐进式启用**: 可以先启用 `baseline_analysis` 和 `smart_eda`，再启用 `constraint_check`
