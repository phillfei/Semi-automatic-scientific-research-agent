<div align="center">

# 🤖 EvoAgentX Code Optimizer

**Your Semi-Automatic AI Code Optimization Assistant**

*Transform Ideas into Production-Ready Code Through Intelligent Research*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![EvoAgentX](https://img.shields.io/badge/Powered%20by-EvoAgentX-green.svg)](https://github.com/EvoAgentX/EvoAgentX)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[简体中文](README_zh.md) | English

</div>

---

## 🎯 What is EvoAgentX Code Optimizer?

EvoAgentX Code Optimizer is a **semi-automatic AI code optimization system** built on the EvoAgentX multi-agent framework. It helps developers optimize machine learning code through an intelligent workflow: **analyze → research → implement → validate**, while strictly preserving your baseline code.

### Core Philosophy

Don't just generate code—**understand the problem, research solutions, then implement**—while **never modifying your baseline code**.

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Anti-Drift** | Constraint validation ensures optimization directions comply with rules |
| 📊 **Code Analysis** | Automatically parses code structure and identifies optimization opportunities |
| 🧠 **Smart EDA** | Auto-detects data types and discovers potential issues |
| 📝 **Baseline-Safe** | Only generates incremental optimization code, never modifies original |
| 🎛️ **Configurable** | Feature flags allow flexible control of functionality |

## 🏗️ System Architecture

```
Input (HTML + Code + Data)
    ↓
Baseline Analyzer → Smart EDA → Supervisor → Constraint Check → Search → Engineer V2
    ↓                    ↓           ↓              ↓            ↓           ↓
Code Structure      Data Insights   Directions    Validation   Papers   Incremental
Analysis                                               Code
```

## 🚀 Quick Start

### Installation

```bash
git clone <repository-url>
cd evo_code_optimizer
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and set your LLM API key
```

### Usage

```bash
# Start web interface
python run_server.py
# Open http://localhost:8000
```

Or use programmatically:

```python
from core.enhanced_workflow import run_enhanced_workflow
from agents import create_llm

llm = create_llm(temperature=0.3)

results = await run_enhanced_workflow(
    llm=llm,
    project_name="my_project",
    html_content=html_content,      # Project description
    code_content=code_content,      # Your baseline code
    data_path="./data/train",       # Data path
    enable_constraint_check=True
)
```

## 📁 Project Structure

```
evo_code_optimizer/
├── agents/v2/           # Enhanced agents (V2)
├── backend/             # FastAPI web service
├── config/              # Configuration system
├── core/                # Core workflow
├── data/                # Data processing
├── utils/               # Utilities
├── output/              # Generated code output
├── main.py              # CLI entry
└── run_server.py        # Web server entry
```

## 🎛️ Configuration

```yaml
# evo_config.yaml
features:
  constraint_check: true       # Enable constraint checking
  baseline_analysis: true      # Enable code analysis
  smart_eda: true              # Enable smart EDA
  hitl_approval: false         # Human-in-the-loop
```

## 🆚 V2 vs V1

| Feature | V1 | V2 (Enhanced) |
|---------|-----|---------------|
| Baseline Analysis | Manual | Automatic |
| Constraint Check | Soft (prompt only) | Hard (triple validation) |
| Code Generation | May modify baseline | Strictly incremental |
| Output Format | Single file | Separated (patch + backup + guide) |
| Configurable | Limited | Full feature flags |

## 📚 Documentation

- [ENHANCED_FEATURES.md](ENHANCED_FEATURES.md) - Enhanced features details
- [CODE_CONSTRAINTS.md](CODE_CONSTRAINTS.md) - Code constraints system
- [ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md) - V1 vs V2 comparison
- [FILE_ENCODING_GUIDE.md](FILE_ENCODING_GUIDE.md) - File encoding guide
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Migration from V1 to V2

## 📄 License

MIT License

## 🙏 Acknowledgements

Built on [EvoAgentX](https://github.com/EvoAgentX/EvoAgentX) agent framework.