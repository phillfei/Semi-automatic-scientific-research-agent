<div align="center">

# 🤖 EvoAgentX 代码优化系统

**你的半自动 AI 代码优化助手**

*通过智能研究将想法转化为生产级代码*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![EvoAgentX](https://img.shields.io/badge/Powered%20by-EvoAgentX-green.svg)](https://github.com/EvoAgentX/EvoAgentX)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

简体中文 | [English](README.md)

</div>

---

## 🎯 什么是 EvoAgentX 代码优化系统？

EvoAgentX 代码优化系统是一个**半自动 AI 代码优化系统**，基于 EvoAgentX 多 Agent 框架构建。它通过智能工作流程帮助开发者优化机器学习代码：**分析 → 研究 → 实现 → 验证**，同时严格保留你的 baseline 代码。

### 核心理念

不只是生成代码——**理解问题、研究方案、然后实现**——同时**绝不修改你的 baseline 代码**。

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔍 **防跑偏** | 约束验证确保优化方向符合规则 |
| 📊 **代码分析** | 自动解析代码结构，识别优化机会 |
| 🧠 **智能 EDA** | 自动检测数据类型，发现潜在问题 |
| 📝 **Baseline 安全** | 只生成增量优化代码，绝不修改原始代码 |
| 🎛️ **可配置** | 特性开关灵活控制功能启用 |

## 🏗️ 系统架构

```
输入 (HTML + 代码 + 数据)
    ↓
代码分析器 → 智能 EDA → 主管 Agent → 约束检查 → 搜索 → 工程师 V2
    ↓              ↓           ↓           ↓         ↓           ↓
代码结构       数据洞察      优化方向     验证      论文      增量代码
分析
```

## 🚀 快速开始

### 安装

```bash
git clone <repository-url>
cd evo_code_optimizer
pip install -r requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 设置你的 LLM API 密钥
```

### 使用

```bash
# 启动 Web 界面
python run_server.py
# 打开 http://localhost:8000
```

或通过代码使用：

```python
from core.enhanced_workflow import run_enhanced_workflow
from agents import create_llm

llm = create_llm(temperature=0.3)

results = await run_enhanced_workflow(
    llm=llm,
    project_name="my_project",
    html_content=html_content,      # 项目描述
    code_content=code_content,      # 你的 baseline 代码
    data_path="./data/train",       # 数据路径
    enable_constraint_check=True
)
```

## 📁 项目结构

```
evo_code_optimizer/
├── agents/v2/           # 增强版 Agent (V2)
├── backend/             # FastAPI Web 服务
├── config/              # 配置系统
├── core/                # 核心工作流
├── data/                # 数据处理
├── utils/               # 工具函数
├── output/              # 生成代码输出
├── main.py              # 命令行入口
└── run_server.py        # Web 服务入口
```

## 🎛️ 配置

```yaml
# evo_config.yaml
features:
  constraint_check: true       # 启用约束检查
  baseline_analysis: true      # 启用代码分析
  smart_eda: true              # 启用智能 EDA
  hitl_approval: false         # 人工审批
```

## 🆚 V2 vs V1

| 特性 | V1 | V2 (增强版) |
|------|-----|-------------|
| 代码分析 | 手动 | 自动 |
| 约束检查 | 软约束（仅提示词） | 硬约束（三重验证） |
| 代码生成 | 可能修改 baseline | 严格增量模式 |
| 输出格式 | 单文件 | 分离（补丁 + 备份 + 指南） |
| 可配置性 | 有限 | 完整特性开关 |

## 📚 文档

- [ENHANCED_FEATURES.md](ENHANCED_FEATURES.md) - 增强功能详情
- [CODE_CONSTRAINTS.md](CODE_CONSTRAINTS.md) - 代码约束系统
- [ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md) - V1 vs V2 对比
- [FILE_ENCODING_GUIDE.md](FILE_ENCODING_GUIDE.md) - 文件编码指南
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - 从 V1 迁移到 V2

## 📄 许可证

MIT 许可证

## 🙏 致谢

基于 [EvoAgentX](https://github.com/EvoAgentX/EvoAgentX) Agent 框架构建。