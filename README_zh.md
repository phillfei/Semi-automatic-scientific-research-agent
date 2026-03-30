<div align="center">

# 🤖 AI Research Master

**你的半自动 AI 研究助手**

*通过智能研究将想法转化为生产级代码*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![EvoAgentX](https://img.shields.io/badge/Powered%20by-EvoAgentX-green.svg)](https://github.com/EvoAgentX/EvoAgentX)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

简体中文 | [English](README.md)

</div>

---

## 🎯 AI Research Master 是什么？

AI Research Master 是一个**半自动 AI 研究系统**，充当你的智能研究助手。与传统代码生成器不同，它模拟人类研究者的工作方式：**分析 → 研究 → 实现 → 验证**。

### 研究工作流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    分析     │───►│    研究     │───►│    实现     │───►│    验证     │
│    项目     │    │    论文     │    │    代码     │    │    结果     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │
   Supervisor         Search            Engineer          人机协作
     Agent            Agent              Agent            (HITL)
```

**核心理念**：不只是生成代码——**理解问题、研究方案、然后实现**。

## ✨ 核心能力

| 能力 | 描述 | 人类参与 |
|------|------|----------|
| 📊 **深度项目分析** | 自动解析 HTML 任务书、分析数据特征、识别优化机会 | 审查分析结果 |
| 🔍 **学术研究** | 搜索 arXiv 等学术资源获取最新技术（每个方向 3-5 篇论文） | 批准研究方向 |
| 💡 **智能方向选择** | 使用 EDA 确定前 3 个优化策略，避免架构改动 | 选择具体方向 |
| 📝 **研究驱动编程** | 基于论文洞见生成代码，而非简单模式匹配 | 审查代码 |
| 🏆 **竞赛就绪** | 针对 Kaggle/BirdCLEF 的特殊支持，含 OOG 策略 | 配置参数 |

## 🎭 三个研究 Agent

### 1️⃣ Supervisor Agent — 研究主管
**角色**：首席研究员
- 像资深研究者一样分析项目需求
- 对实际数据文件执行真实 EDA
- **约束解决方案**在数据/训练策略范围内（不涉及架构改动）
- 产出包含 3 个方向的研究提案

**相当于**：为你划定研究问题的博士导师。

### 2️⃣ Search Agent — 文献检索员
**角色**：研究图书管理员
- 跨学术数据库并行搜索
- 迭代优化：基于初步结果调整关键词
- 从论文中提取核心方法
- 生成文献综述报告

**相当于**：通宵为你查找并总结相关论文的研究助理。

### 3️⃣ Engineer Agent — 实现工程师
**角色**：研究工程师
- 将论文洞见转化为可运行代码
- 同时生成实现代码和 pytest 测试
- 使用 CodeExtraction 智能组织代码
- 输出到 `output/` 目录

**相当于**：为你实现实验的共同作者。

## 🔄 半自动工作流程

```
人类输入                    AI 处理                         人类审查
───────────                ───────────                     ───────────
上传 HTML         ───►     Supervisor 分析项目      ───►   审查研究提案
+ 代码 + 数据                并执行 EDA                          │
                                                                  ▼
从提案中选择      ◄───      Search Agent 研究      ◄───   批准搜索关键词
研究方向                     论文和方法                          │
                                   │                              ▼
                                   ▼                              ▼
审查生成的代码    ◄───      Engineer 基于论文     ◄───   审查代码结构
和测试                       实现方案                            │
                                   │                              ▼
                                   ▼                              ▼
运行实验并验证    ───►      迭代优化 refinement    ───►   验证并迭代
```

## 🚀 快速开始

### 安装

```bash
git clone <repository-url>
cd ai-research-master
pip install -r requirements.txt

# 设置你偏好的 LLM API 密钥
export OPENAI_API_KEY="sk-..."
# 或
export SILICONFLOW_API_KEY="sk-..."
```

### 启动研究

```python
from ai_research_master import ResearchSession

# 启动研究会话
session = ResearchSession(
    project_name="birdclef_audio_classification",
    llm_config={"model": "gpt-4o-mini"}
)

# 1. 上传你的研究材料
session.load_project(
    html_brief="./competition_brief.html",      # 竞赛/任务描述
    baseline_code="./baseline.py",              # 起始代码
    data_sample="./data/train_sample.csv"       # 用于 EDA 的数据
)

# 2. AI 分析并提出研究方向
proposal = session.generate_research_proposal()
# 返回：research_summary, 3 optimization_directions, eda_analysis

# 3. 你选择方向，AI 搜索论文
direction = proposal.directions[0]  # 或让用户选择
literature_review = session.research_direction(direction)

# 4. AI 基于论文实现
results = session.implement_solution(literature_review)
# 输出代码到 ./output/20260330_.../
```

### Web 界面

```bash
# 启动研究仪表板
python run_server.py

# 打开 http://localhost:8000
# - 上传项目材料
# - 监控研究进度
# - 在每个阶段审查和批准
# - 下载生成的代码
```

## 📋 研究输出结构

每个研究方向产出：

```
output/
├── 20260330_143022_1_specaugment_strategy/
│   ├── 20260330_143022_1_specaugment_strategy_main.py      # 实现代码
│   ├── 20260330_143022_1_specaugment_strategy_test.py      # pytest 测试
│   └── README.md                                            # 研究笔记
├── 20260330_143022_2_focal_loss_optimization/
│   ├── ...
└── literature_review.md                                     # 检索报告
```

## ⚠️ 研究约束

确保实用、可部署的结果：

**我们研究这些**：               **我们不研究这些**：
✅ 数据增强                    ❌ 新模型架构
✅ 特征工程                    ❌ 修改骨干网络
✅ 损失函数                    ❌ 增加/删除层
✅ 训练策略                    ❌ 架构搜索
✅ 集成方法                    ❌ 复杂模型重设计
✅ 后处理优化                  ❌ 仅推理优化

**为什么？** 架构改动需要深厚的领域专业知识和大量验证。对于大多数实践者来说，数据和训练策略提供更好的投入产出比。

## 🎓 示例：研究会话

```
用户："我需要改进我的 BirdCLEF 音频分类器"

[Supervisor Agent]
├─ 分析：多标签鸟鸣分类
├─ EDA：32kHz 音频，5秒片段，200+ 物种
└─ 提议：
   1. SpecAugment 音频鲁棒性
   2. Focal Loss 类别不平衡
   3. OOF 集成策略

用户选择："SpecAugment 音频鲁棒性"

[Search Agent]
├─ 查询："SpecAugment audio classification", "time warping spectrogram"
├─ 发现：arXiv 上 5 篇近期论文
└─ 综合：实现策略、超参数

[Engineer Agent]
├─ 实现：时间/频率掩码的 SpecAugment
├─ 生成：增强功能的 pytest 测试
└─ 输出：可直接集成的模块

用户：审查、测试、集成到训练流程
```

## 🔧 配置

### 支持的 LLM 提供商

| 提供商 | 适用场景 | 配置 |
|--------|----------|------|
| OpenAI | 通用研究 | `OPENAI_API_KEY` |
| SiliconFlow | 国内访问 | `SILICONFLOW_API_KEY` |
| OpenRouter | 模型多样性 | `OPENROUTER_API_KEY` |

### 研究参数

```python
# config.yaml
research:
  max_directions: 3              # 研究方向数量
  papers_per_direction: 5        # 文献搜索深度
  eda_sample_size: 1000          # 数据分析采样行数
  code_output_dir: "./output"    # 结果保存位置
  
constraints:
  allow_architecture_changes: false   # 禁止模型结构修改
  require_tests: true                 # 生成 pytest
  competition_mode: auto              # 自动检测 OOG 需求
```

## 🧪 研究领域

当前针对以下领域优化：
- 🎵 **音频分类**（BirdCLEF、音频标签）
- 🖼️ **计算机视觉**（图像分类、目标检测）
- 📊 **表格机器学习**（结构化数据、时间序列）
- 📝 **NLP**（文本分类、序列标注）

*每个领域使用领域特定的 EDA 和论文搜索策略。*

## 📊 研究指标

系统追踪：
- 📈 每次研究会话审查的论文数
- ⏱️ 平均研究到代码的时间
- 🎯 实现覆盖率（测试通过率）
- 🔄 知识库复用（避免的重复搜索）

查看 `logs/research_metrics.json`

## 🤝 如何融入你的工作流

| 你的角色 | AI Research Master 的帮助 |
|----------|--------------------------|
| **ML 工程师** | 快速文献综述 + 实现模板 |
| **研究者** | 自动化论文搜索 + 可复现代码 |
| **Kaggle 选手** | 竞赛特定策略 + OOG 处理 |
| **学生** | 从近期论文学习最佳实践 |
| **团队负责人** | 团队标准化研究流程 |

## 🆚 与传统工具对比

| | AI Research Master | AutoML | 代码 Copilot |
|---|-------------------|---------|--------------|
| **方法** | 研究驱动 | 搜索驱动 | 模式驱动 |
| **输入** | 项目任务书 + 数据 | 仅数据集 | 代码上下文 |
| **输出** | 基于研究的解决方案 | 优化模型 | 代码补全 |
| **人类角色** | 研究主管 | 最小参与 | 代码审查者 |
| **适用** | 新颖问题 | 标准问题 | 常规编码 |

## 📄 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)

## 🙏 致谢

基于 [EvoAgentX](https://github.com/EvoAgentX/EvoAgentX) Agent 框架构建。

---

<div align="center">

**将研究转化为代码**

*从文献综述到代码实现 —— 全程由你掌控*

</div>
