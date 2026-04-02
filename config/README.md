# EvoAgentX 配置系统

参考 [Claude Code CLI](../../src) 的架构设计，为 EvoAgentX 引入配置化、模块化的架构。

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     EvoAgentX 配置系统                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ FeatureFlags │  │ConfigManager │  │AgentProfiles │         │
│  │   特性开关    │  │   配置管理    │  │  Agent配置   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           ▼                                    │
│              ┌────────────────────────┐                       │
│              │   WorkflowBlueprint    │                       │
│              │     工作流蓝图          │                       │
│              └───────────┬────────────┘                       │
│                          ▼                                    │
│              ┌────────────────────────┐                       │
│              │ ConfigurableWorkflow   │                       │
│              │    可配置工作流引擎      │                       │
│              └────────────────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 核心组件

### 1. FeatureFlags - 特性开关系统

类似 `src` 的 `feature()` 函数，支持运行时特性控制。

```python
from config import feature_enabled, enable_feature, Feature

# 检查特性
if feature_enabled(Feature.ITERATIVE_SEARCH):
    # 执行迭代搜索
    pass

# 启用/禁用特性
enable_feature(Feature.AUTO_TEST)
disable_feature(Feature.HITL_APPROVAL)
```

**配置方式（优先级从高到低）：**
1. 运行时覆盖 (`enable_feature()`)
2. 环境变量 (`EVO_FEATURE_XXX=true`)
3. 配置文件 (`evo_config.yaml`)
4. 代码默认值

### 2. ConfigManager - 配置管理器

统一管理所有配置项，支持嵌套访问。

```python
from config import get_config, set_config

config = get_config()

# 读取配置
temp = config.get('agent.llm_temperature')
workers = config.get('agent.search_max_workers')

# 修改配置
set_config('agent.llm_temperature', 0.5)

# 获取配置对象
agent_config = config.get_agent_config()
```

### 3. AgentProfiles - Agent 配置文件

模板化的 Agent 角色定义，支持变量替换。

```python
from config import get_profile

profile = get_profile("Supervisor")

# 获取系统提示词（自动变量替换）
prompt = profile.get_system_prompt(
    max_directions=3,
    data_type="音频分类"
)

# 获取行为配置
max_dirs = profile.get_behavior('max_directions')
```

### 4. WorkflowBlueprint - 工作流蓝图

声明式工作流定义，支持条件执行和特性门控。

```python
from config import WorkflowBuilder, NodeType, create_standard_blueprint

# 使用预定义蓝图
blueprint = create_standard_blueprint()

# 或使用 Builder 自定义
builder = WorkflowBuilder("custom", "自定义工作流")
blueprint = (builder
    .add_node(
        name="research",
        node_type=NodeType.RESEARCH,
        agent="Supervisor",
        outputs=["directions"],
        required_features=["supervisor_eda"]
    )
    .add_node(
        name="implement",
        node_type=NodeType.IMPLEMENT,
        agent="Engineer",
        inputs=["directions"],
        outputs=["code"]
    )
    .sequential("research", "implement")
    .build()
)
```

## 🚀 快速开始

### 步骤 1: 创建配置文件

复制示例配置文件：

```bash
cp evo_config_example.yaml evo_config.yaml
```

编辑 `evo_config.yaml`：

```yaml
features:
  iterative_search: true
  knowledge_base: true
  hitl_approval: false      # 关闭人工审批以加速
  auto_test: false

agent:
  supervisor_max_directions: 3
  engineer_code_style: "incremental"
```

### 步骤 2: 使用配置系统

```python
from config import (
    feature_enabled, 
    get_config, 
    get_profile,
    create_standard_blueprint
)
from agents.v2.supervisor_agent_v2 import SupervisorAgentV2

# 创建配置化 Agent
llm = create_llm()
supervisor = SupervisorAgentV2(llm, profile_name="Supervisor")

# Agent 自动读取配置
# - 系统提示词从 profile 加载
# - EDA 开关从 feature_flags 检查
# - 方向数量从 config_manager 获取
```

### 步骤 3: 动态工作流

```python
from core.configurable_workflow import ConfigurableWorkflowEngine

# 根据配置选择蓝图
if feature_enabled(Feature.DYNAMIC_WORKFLOW):
    blueprint = create_custom_blueprint()
else:
    blueprint = create_standard_blueprint()

# 执行工作流
engine = ConfigurableWorkflowEngine(blueprint, agent_manager)
results = await engine.execute(inputs={
    "project_name": "my_project",
    "code_content": "..."
})
```

## ⚙️ 配置详解

### 特性开关 (features)

| 特性 | 说明 | 默认 |
|------|------|------|
| `iterative_search` | 迭代搜索优化关键词 | ✅ |
| `knowledge_base` | 知识库复用搜索结果 | ✅ |
| `incremental_code` | 增量代码生成模式 | ✅ |
| `hitl_approval` | 人工审批节点 | ❌ |
| `auto_test` | 自动测试执行 | ❌ |
| `advanced_eda` | 高级 EDA 分析 | ❌ |
| `debug_prompts` | 打印完整提示词 | ❌ |

### Agent 配置 (agent)

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `supervisor_max_directions` | 最大优化方向数 | 3 |
| `search_max_workers` | 并行搜索线程数 | 3 |
| `engineer_code_style` | 代码生成风格 | `incremental` |
| `llm_temperature` | LLM 温度参数 | 0.3 |

### 工作流配置 (workflow)

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `enable_research` | 启用研究节点 | ✅ |
| `enable_search` | 启用搜索节点 | ✅ |
| `enable_test` | 启用测试节点 | ❌ |
| `parallel_search` | 并行搜索 | ✅ |

## 🔧 环境变量覆盖

所有配置都可通过环境变量覆盖：

```bash
# 特性开关
export EVO_FEATURE_HITL_APPROVAL=true
export EVO_FEATURE_AUTO_TEST=true

# Agent 配置
export EVO_AGENT_SEARCH_MAX_WORKERS=5
export EVO_AGENT_ENGINEER_CODE_STYLE=patch

# 运行程序
python main.py
```

## 📝 自定义 Agent 配置

创建 `agent_profiles/my_supervisor.yaml`：

```yaml
name: MySupervisor
description: 我的自定义 Supervisor
system_prompt_template: |
  你是 Supervisor，负责 {max_directions} 个方向...
prompt_variables:
  max_directions: 5
capabilities:
  - project_analysis
  - eda_analysis
behaviors:
  enable_eda: true
  banned_keywords:
    - "模型架构"
    - "推理速度"
```

## 🔄 与原代码的对比

| 原代码 (死板) | 新代码 (配置化) |
|--------------|----------------|
| 硬编码工作流顺序 | 蓝图驱动的动态工作流 |
| 固定系统提示词 | 模板化、变量替换 |
| 代码中判断 EDA | 特性开关控制 |
| 固定方向数量 | 配置可调 |
| 无法扩展新 Agent | 配置文件注册新 Agent |
| 需要改代码调整行为 | 改配置文件即可 |

## 📂 文件结构

```
evo_code_optimizer/
├── config/                      # 配置系统
│   ├── __init__.py
│   ├── feature_flags.py         # 特性开关
│   ├── config_manager.py        # 配置管理
│   ├── agent_profiles.py        # Agent 配置
│   └── workflow_blueprint.py    # 工作流蓝图
├── agents/v2/                   # 配置化 Agent
│   └── supervisor_agent_v2.py
├── core/                        # 核心引擎
│   └── configurable_workflow.py
├── evo_config_example.yaml      # 配置示例
└── example_config_usage.py      # 使用示例
```

## 💡 最佳实践

1. **默认关闭实验性功能**：新功能默认关闭，稳定后再开启
2. **环境变量用于 CI/CD**：在流水线中通过环境变量控制行为
3. **配置文件用于团队共享**：将 `evo_config.yaml` 提交到版本控制
4. **Agent Profile 继承**：基于现有配置创建变体
5. **渐进式迁移**：新旧代码可以共存，逐步迁移
