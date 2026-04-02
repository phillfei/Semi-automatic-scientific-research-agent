# 迁移指南：从死板代码到配置化架构

## 概述

本文档指导如何将原有的死板代码迁移到新的配置化架构。

## 迁移前 vs 迁移后

### 1. Agent 定义

**迁移前 (硬编码)：**

```python
# agents/supervisor_agent.py
class SupervisorAgent(Agent):
    def __init__(self, llm):
        super().__init__(
            name="Supervisor",
            description="主管Agent...",
            llm=llm,
            system_prompt="""你是主管Agent，负责：
1. 深度分析...
2. 确定最多3个优化方向...
... (200+ 行硬编码提示词)
"""
        )
        # 硬编码行为
        self.max_directions = 3
        self.enable_eda = True
```

**迁移后 (配置化)：**

```python
# agents/v2/supervisor_agent_v2.py
class SupervisorAgentV2(Agent):
    def __init__(self, llm, profile_name="Supervisor"):
        # 从配置加载
        self.profile = get_profile(profile_name)
        self.config = get_config()
        
        # 动态行为
        self.max_directions = self.profile.get_behavior('max_directions', 3)
        self.enable_eda = feature_enabled(Feature.SUPERVISOR_EDA)
        
        # 模板化提示词
        system_prompt = self.profile.get_system_prompt(
            max_directions=self.max_directions
        )
        
        super().__init__(...)
```

### 2. 工作流定义

**迁移前 (硬编码)：**

```python
# workflows/optimization_workflow.py
def create_workflow(project_name, llm):
    # 固定顺序：Supervisor -> Search -> Engineer
    graph = WorkFlowGraph(
        nodes=[
            WorkFlowNode(name="research", agents=["Supervisor"], ...),
            WorkFlowNode(name="search", agents=["Search"], ...),
            WorkFlowNode(name="implement", agents=["Engineer"], ...),
        ],
        edges=[
            WorkFlowEdge(source="research", target="search"),
            WorkFlowEdge(source="search", target="implement"),
        ]
    )
```

**迁移后 (蓝图驱动)：**

```python
from config import create_standard_blueprint
from core.configurable_workflow import ConfigurableWorkflowEngine

async def run_workflow(project_name, llm):
    # 根据配置选择蓝图
    blueprint = create_standard_blueprint()
    
    # 动态执行（自动处理特性开关）
    engine = ConfigurableWorkflowEngine(blueprint, agent_manager)
    results = await engine.execute(inputs={...})
```

### 3. 特性控制

**迁移前 (硬编码)：**

```python
# 无法在不改代码的情况下开关功能
class SearchAgent(Agent):
    def search(self, query):
        # 总是执行迭代搜索
        papers1 = self._search(query)
        keywords = self._refine_keywords(papers1)
        papers2 = self._search(keywords)
        return papers1 + papers2
```

**迁移后 (特性开关)：**

```python
from config import feature_enabled, Feature

class SearchAgentV2(Agent):
    def search(self, query):
        papers = self._search(query)
        
        # 根据特性开关决定是否迭代
        if feature_enabled(Feature.ITERATIVE_SEARCH):
            keywords = self._refine_keywords(papers)
            papers2 = self._search(keywords)
            papers.extend(papers2)
        
        return papers
```

## 分步迁移指南

### 第 1 步：添加配置系统

1. 复制 `evo_code_optimizer/config/` 目录到你的项目
2. 复制 `evo_config_example.yaml` 到项目根目录
3. 重命名为 `evo_config.yaml` 并开始自定义

### 第 2 步：渐进式迁移 Agent

**不要一次性迁移所有 Agent**，而是：

1. 保留原有 Agent 不变
2. 创建新的 V2 版本（如 `supervisor_agent_v2.py`）
3. 在新版本中使用配置系统
4. 通过特性开关控制使用哪个版本

```python
# 渐进式迁移示例
if feature_enabled(Feature.USE_V2_AGENTS):
    from agents.v2 import SupervisorAgentV2 as SupervisorAgent
else:
    from agents import SupervisorAgent  # 旧版本
```

### 第 3 步：迁移工作流

1. 使用 `WorkflowBuilder` 定义新工作流
2. 使用 `ConfigurableWorkflowEngine` 执行
3. 逐步替换旧的工作流代码

### 第 4 步：移除旧代码

当所有 Agent 都迁移完成后：

1. 删除旧 Agent 文件
2. 将 V2 Agent 重命名为正式版本
3. 更新导入路径

## 配置示例

### 场景 1: 快速模式（跳过搜索）

```yaml
# evo_config.yaml
features:
  iterative_search: false
  knowledge_base: false

workflow:
  enable_search: false
```

效果：工作流直接跳过搜索阶段，Supervisor 确定方向后 Engineer 直接生成代码。

### 场景 2: 严格模式（人工审批）

```yaml
features:
  hitl_approval: true

workflow:
  require_hitl_after_research: true
  require_hitl_after_search: true
```

效果：每个关键节点后都会暂停等待人工确认。

### 场景 3: 研究模式（深度搜索）

```yaml
features:
  iterative_search: true
  advanced_eda: true

agent:
  search_time_limit_minutes: 15
  search_papers_per_query: 10
  supervisor_max_directions: 5
```

效果：更长时间的搜索、更多的优化方向、更深入的 EDA。

## 环境变量速查

```bash
# 快速开关特性
export EVO_FEATURE_HITL_APPROVAL=true
export EVO_FEATURE_AUTO_TEST=true
export EVO_FEATURE_DEBUG_PROMPTS=true

# 调整参数
export EVO_AGENT_SUPERVISOR_MAX_DIRECTIONS=5
export EVO_AGENT_SEARCH_MAX_WORKERS=5
export EVO_AGENT_LLM_TEMPERATURE=0.5

# 运行
python main.py
```

## 常见问题

### Q: 配置文件不生效？

检查配置文件路径是否正确：

```python
from config import get_config
config = get_config()
print(config.agent.llm_temperature)  # 检查是否读取正确
```

### Q: 如何调试特性开关？

```python
from config import get_feature_flags

flags = get_feature_flags()
all_features = flags.get_all_features()

for name, info in all_features.items():
    print(f"{name}: {info['enabled']} (available: {info['available']})")
```

### Q: 如何创建自定义 Agent？

创建 `agent_profiles/my_agent.yaml`：

```yaml
name: MyAgent
description: 我的自定义 Agent
system_prompt_template: |
  你是 {role}，负责...
prompt_variables:
  role: "专家"
capabilities:
  - analysis
  - coding
behaviors:
  custom_param: true
```

然后在代码中使用：

```python
profile = get_profile("MyAgent")
agent = MyAgent(llm, profile_name="MyAgent")
```

## 回滚策略

如果新系统出现问题，可以通过以下方式快速回滚：

1. **特性开关回滚**：禁用有问题的特性
   ```bash
   export EVO_FEATURE_NEW_FEATURE=false
   ```

2. **代码回滚**：切换回旧版本 Agent
   ```python
   # 在代码中切换
   from agents import SupervisorAgent  # 旧版本
   ```

3. **配置回滚**：恢复默认配置
   ```bash
   rm evo_config.yaml  # 删除自定义配置，使用默认值
   ```
