<div align="center">

# 🤖 AI Research Master

**Your Semi-Automatic AI Research Assistant**

*Transform Ideas into Production-Ready Code Through Intelligent Research*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![EvoAgentX](https://img.shields.io/badge/Powered%20by-EvoAgentX-green.svg)](https://github.com/EvoAgentX/EvoAgentX)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[简体中文](README_zh.md) | English

</div>

---

## 🎯 What is AI Research Master?

AI Research Master is a **semi-automatic AI research system** that acts as your intelligent research assistant. Unlike traditional code generators, it mimics how human researchers work: **analyze → research → implement → validate**.

### The Research Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Analyze   │───►│   Research  │───►│  Implement  │───►│   Validate  │
│   Project   │    │   Papers    │    │    Code     │    │   Results   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │
   Supervisor         Search            Engineer          Human-in-
     Agent            Agent              Agent            the-Loop
```

**Key Philosophy**: Don't just generate code—**understand the problem, research solutions, then implement**.

## ✨ Core Capabilities

| Capability | Description | Human Involvement |
|------------|-------------|-------------------|
| 📊 **Deep Project Analysis** | Automatically parse HTML briefs, analyze data characteristics, identify optimization opportunities | Review analysis |
| 🔍 **Academic Research** | Search arXiv and academic sources for latest techniques (3-5 papers per direction) | Approve directions |
| 💡 **Intelligent Direction Selection** | Use EDA to determine top 3 optimization strategies, avoiding architectural changes | Choose direction |
| 📝 **Research-Driven Coding** | Generate code based on paper insights, not just patterns | Review code |
| 🏆 **Competition Ready** | Specialized support for Kaggle/BirdCLEF with OOG strategies | Configure params |

## 🎭 The Three Agents

### 1️⃣ Supervisor Agent — The Research Lead
**Role**: Principal Investigator
- Analyzes project requirements like a senior researcher
- Performs real EDA on actual data files
- **Constrains solutions** to data/training strategies (no architecture changes)
- Produces research proposal with 3 directions

**Think of it as**: Your PhD advisor who scopes the research problem.

### 2️⃣ Search Agent — The Literature Reviewer
**Role**: Research Librarian
- Parallel searches across academic databases
- Iterative refinement: adjust keywords based on initial results
- Extracts key methods from papers
- Generates literature review reports

**Think of it as**: Your research assistant who finds and summarizes relevant papers overnight.

### 3️⃣ Engineer Agent — The Implementer
**Role**: Research Engineer
- Translates paper insights into working code
- Generates both implementation and pytest tests
- Uses CodeExtraction for intelligent code organization
- Outputs to `output/` directory

**Think of it as**: Your co-author who implements the experiments.

## 🔄 Semi-Automatic Workflow

```
Human Input                    AI Processing                    Human Review
───────────                    ─────────────                    ────────────
Upload HTML         ───►      Supervisor analyzes         ───►  Review research
+ Code + Data                    project & EDA                       proposal
                                                                      │
                                                                      ▼
Select direction    ◄───      Search Agent researches     ◄───  Approve search
from proposal                   papers & methods                    keywords
                                      │                               │
                                      ▼                               ▼
Review generated    ◄───      Engineer implements         ◄───  Review code
code & tests                    based on papers                   structure
                                      │                               │
                                      ▼                               ▼
Run experiments     ───►      Iterative refinement        ───►  Validate &
& validate                                                    iterate
```

## 🚀 Quick Start

### Installation

```bash
git clone <repository-url>
cd ai-research-master
pip install -r requirements.txt

# Set your preferred LLM API key
export OPENAI_API_KEY="sk-..."
# OR
export SILICONFLOW_API_KEY="sk-..."
```

### Launch Your Research

```python
from ai_research_master import ResearchSession

# Start a research session
session = ResearchSession(
    project_name="birdclef_audio_classification",
    llm_config={"model": "gpt-4o-mini"}
)

# 1. Upload your research materials
session.load_project(
    html_brief="./competition_brief.html",      # Competition/task description
    baseline_code="./baseline.py",              # Starting code
    data_sample="./data/train_sample.csv"       # Data for EDA
)

# 2. AI analyzes and proposes research directions
proposal = session.generate_research_proposal()
# Returns: research_summary, 3 optimization_directions, eda_analysis

# 3. You select a direction, AI searches papers
direction = proposal.directions[0]  # Or let user choose
literature_review = session.research_direction(direction)

# 4. AI implements based on papers
results = session.implement_solution(literature_review)
# Outputs code to ./output/20260330_.../
```

### Web Interface

```bash
# Launch the research dashboard
python run_server.py

# Open http://localhost:8000
# - Upload project materials
# - Monitor research progress
# - Review and approve at each stage
# - Download generated code
```

## 📋 Research Output Structure

Each research direction produces:

```
output/
├── 20260330_143022_1_specaugment_strategy/
│   ├── 20260330_143022_1_specaugment_strategy_main.py      # Implementation
│   ├── 20260330_143022_1_specaugment_strategy_test.py      # pytest tests
│   └── README.md                                            # Research notes
├── 20260330_143022_2_focal_loss_optimization/
│   ├── ...
└── literature_review.md                                     # Search report
```

## ⚠️ Research Constraints

To ensure practical, deployable results:

**We Research These**:          **We Don't Research These**:
✅ Data augmentation           ❌ New model architectures
✅ Feature engineering          ❌ Modifying backbone networks
✅ Loss functions               ❌ Adding/removing layers
✅ Training strategies          ❌ Architecture search
✅ Ensemble methods             ❌ Complex model redesigns
✅ Post-processing              ❌ Inference optimization only

**Why?** Architectural changes require deep domain expertise and extensive validation. Data and training strategies offer better ROI for most practitioners.

## 🎓 Example: Research Session

```
User: "I need to improve my BirdCLEF audio classifier"

[Supervisor Agent]
├─ Analyzes: Multi-label bird sound classification
├─ EDA: 32kHz audio, 5-second clips, 200+ species
└─ Proposes:
   1. SpecAugment for audio robustness
   2. Focal Loss for class imbalance
   3. OOF ensemble strategy

User selects: "SpecAugment for audio robustness"

[Search Agent]
├─ Queries: "SpecAugment audio classification", "time warping spectrogram"
├─ Finds: 5 recent papers on arXiv
└─ Synthesizes: Implementation strategies, hyperparameters

[Engineer Agent]
├─ Implements: SpecAugment with time/freq masking
├─ Generates: pytest tests for augmentation
└─ Outputs: Ready-to-integrate module

User: Reviews, tests, integrates into training pipeline
```

## 🔧 Configuration

### Supported LLM Providers

| Provider | Best For | Setup |
|----------|----------|-------|
| OpenAI | General research | `OPENAI_API_KEY` |
| SiliconFlow | China access | `SILICONFLOW_API_KEY` |
| OpenRouter | Model variety | `OPENROUTER_API_KEY` |

### Research Parameters

```python
# config.yaml
research:
  max_directions: 3              # Number of research directions
  papers_per_direction: 5        # Literature search depth
  eda_sample_size: 1000          # Rows for data analysis
  code_output_dir: "./output"    # Where to save results
  
constraints:
  allow_architecture_changes: false   # Enforce no model mods
  require_tests: true                 # Generate pytest
  competition_mode: auto              # Auto-detect OOG needs
```

## 🧪 Research Domains

Currently optimized for:
- 🎵 **Audio Classification** (BirdCLEF, audio tagging)
- 🖼️ **Computer Vision** (Image classification, object detection)
- 📊 **Tabular ML** (Structured data, time series)
- 📝 **NLP** (Text classification, sequence labeling)

*Each domain uses domain-specific EDA and paper search strategies.*

## 📊 Research Metrics

The system tracks:
- 📈 Papers reviewed per research session
- ⏱️ Average research-to-code time
- 🎯 Implementation coverage (tests pass rate)
- 🔄 Knowledge base reuse (avoided duplicate searches)

View in `logs/research_metrics.json`

## 🤝 How It Fits Your Workflow

| Your Role | AI Research Master Helps With |
|-----------|------------------------------|
| **ML Engineer** | Quick literature review + implementation templates |
| **Researcher** | Automated paper search + reproducible code |
| **Kaggler** | Competition-specific strategies + OOG handling |
| **Student** | Learn best practices from recent papers |
| **Team Lead** | Standardized research process across team |

## 🆚 vs. Traditional Tools

| | AI Research Master | AutoML | Code Copilot |
|---|-------------------|---------|--------------|
| **Approach** | Research-driven | Search-driven | Pattern-driven |
| **Input** | Project brief + data | Dataset only | Code context |
| **Output** | Research-based solution | Optimized model | Code completion |
| **Human Role** | Research director | Minimal | Code reviewer |
| **Best For** | Novel problems | Standard problems | Routine coding |

## 📄 License

MIT License - See [LICENSE](LICENSE)

## 🙏 Acknowledgements

Built on [EvoAgentX](https://github.com/EvoAgentX/EvoAgentX) agent framework.

---

<div align="center">

**Transform Research into Code**

*From Literature Review to Implementation — With You in Control*

</div>
