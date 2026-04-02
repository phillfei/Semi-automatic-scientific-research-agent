# 架构对比：死板代码 vs 配置化架构

## 原代码问题分析

### 1. 硬编码工作流

```python
# 原代码：工作流顺序完全硬编码
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

**问题**：
- 无法在不改代码的情况下调整顺序
- 无法跳过某些步骤
- 无法添加新步骤
- 无法根据条件选择不同路径

### 2. 硬编码系统提示词

```python
# 原代码：200+ 行提示词硬编码在代码中
system_prompt="""你是主管Agent，负责：
1. 深度分析用户上传的HTML规划和代码
2. 进行EDA数据分析（如果有数据文件）
3. 确定最多3个优化方向
...

输出格式：
- 研究总结
- 优化方向（最多3个，每个包含名称、理由、关键词）
- EDA分析结果（如有数据）

**重要限制 - 优化方向选择原则**：
1. **禁止**从调整模型结构...
"""
```

**问题**：
- 修改提示词需要改代码
- 无法针对不同场景使用不同提示词
- 变量无法动态替换
- 提示词和逻辑混在一起

### 3. 硬编码行为参数

```python
# 原代码：行为参数分散在各处
class SupervisorAgent(Agent):
    def __init__(self, llm):
        self.max_directions = 3  # 硬编码
        
    def _load_historical_feedback(self, project_name):
        history = self.project_manager.get_history(project_name, limit=5)  # 硬编码 5
        
    def _perform_eda(self, ...):
        sample_files = files[:5]  # 硬编码 5
```

**问题**：
- 参数分散，难以统一管理
- 无法根据场景调整
- 用户无法自定义

### 4. 无条件执行逻辑

```python
# 原代码：所有功能都执行，无法开关
class SearchAgent(Agent):
    def parallel_search(self, tasks, ...):
        # 总是执行迭代搜索
        papers1 = self._search(query)
        keywords = self._refine_keywords(papers1)  # 无法跳过
        papers2 = self._search(keywords)  # 无法跳过
```

**问题**：
- 无法关闭某些功能
- 无法做 A/B 测试
- 无法根据性能要求调整

---

## 新架构解决方案

### 1. 蓝图驱动的工作流

```python
# 新架构：声明式工作流蓝图
blueprint = (WorkflowBuilder("custom")
    .add_node(
        name="research",
        node_type=NodeType.RESEARCH,
        agent="Supervisor",
        required_features=["supervisor_eda"],  # 特性门控
        enabled=True  # 可开关
    )
    .add_node(
        name="search", 
        node_type=NodeType.SEARCH,
        agent="Search",
        required_features=["parallel_search"],
        enabled=get_config('workflow.enable_search')  # 配置控制
    )
    .sequential("research", "search")
    .build()
)
```

**优势**：
- ✅ 配置文件中调整顺序
- ✅ 通过特性开关跳过步骤
- ✅ 动态添加新步骤
- ✅ 条件分支支持

### 2. 模板化的系统提示词

```python
# 新架构：配置化提示词模板
supervisor_profile = AgentProfile(
    name="Supervisor",
    system_prompt_template="""你是主管Agent，负责：
1. 深度分析用户上传的HTML规划和代码
2. 确定最多{max_directions}个优化方向
...
数据类型：{data_type}
项目类型：{project_type}""",
    prompt_variables={
        'max_directions': 3,  # 可配置
        'data_type': '未知',
        'project_type': '通用'
    }
)

# 使用时动态替换
prompt = profile.get_system_prompt(
    max_directions=5,  # 覆盖默认值
    data_type="音频分类",
    project_type="Kaggle竞赛"
)
```

**优势**：
- ✅ 提示词在配置文件中
- ✅ 支持场景化提示词
- ✅ 变量动态替换
- ✅ 提示词和逻辑分离

### 3. 集中式配置管理

```yaml
# evo_config.yaml - 统一管理所有参数
agent:
  supervisor_max_directions: 5
  supervisor_history_limit: 10
  supervisor_eda_sample_size: 10
  
  search_max_workers: 5
  search_time_limit_minutes: 10
  
  llm_temperature: 0.5
```

```python
# 代码中统一读取
config = get_config()
max_directions = config.get('agent.supervisor_max_directions')
history_limit = config.get('agent.supervisor_history_limit')
```

**优势**：
- ✅ 参数集中管理
- ✅ 支持环境变量覆盖
- ✅ 用户可以自定义

### 4. 特性开关系统

```python
# 新架构：特性开关控制逻辑
class SearchAgentV2(Agent):
    def parallel_search(self, tasks, ...):
        papers = self._search(query)
        
        # 根据特性开关决定是否迭代
        if feature_enabled(Feature.ITERATIVE_SEARCH):
            keywords = self._refine_keywords(papers)
            papers2 = self._search(keywords)
            papers.extend(papers2)
        
        # 根据特性开关决定是否使用知识库
        if feature_enabled(Feature.KNOWLEDGE_BASE):
            cached = self._check_knowledge_base(query)
            if cached:
                return cached
```

**优势**：
- ✅ 功能可开关
- ✅ 支持 A/B 测试
- ✅ 可根据性能要求调整
- ✅ 灰度发布支持

---

## 对比总结

| 维度 | 原架构（死板） | 新架构（配置化） |
|------|--------------|----------------|
| **工作流** | 硬编码顺序 | 蓝图驱动，动态构建 |
| **提示词** | 代码中硬编码 | 模板化，变量替换 |
| **参数** | 分散硬编码 | 集中配置管理 |
| **功能开关** | 不支持 | 特性开关系统 |
| **扩展性** | 需改代码 | 配置文件即可 |
| **测试** | 困难 | A/B 测试支持 |
| **维护** | 难维护 | 配置即文档 |

---

## 实际效果对比

### 场景：调整优化方向数量

**原架构**：
```python
# 需要修改代码文件
# 1. 打开 supervisor_agent.py
# 2. 找到第 15 行
# 3. 修改 max_directions = 3 为 5
# 4. 保存文件
# 5. 重启服务
```

**新架构**：
```yaml
# 只需修改 evo_config.yaml
agent:
  supervisor_max_directions: 5
```
或
```bash
# 或设置环境变量
export EVO_AGENT_SUPERVISOR_MAX_DIRECTIONS=5
```

### 场景：添加人工审批节点

**原架构**：
```python
# 需要修改多个文件
# 1. 修改 workflow_graph 添加 hitl 节点
# 2. 修改 workflow_api 添加审批逻辑
# 3. 测试并部署
```

**新架构**：
```yaml
# 只需启用特性
features:
  hitl_approval: true

workflow:
  require_hitl_after_research: true
```

### 场景：针对音频项目优化提示词

**原架构**：
```python
# 修改代码中的提示词
# 需要创建新的 Agent 子类或添加 if 判断
class SupervisorAgent(Agent):
    def _build_research_prompt(self, ...):
        if is_audio_project:  # 新增判断
            prompt = "...音频专用提示词..."
        else:
            prompt = "...通用提示词..."
```

**新架构**：
```python
# 创建配置文件
# agent_profiles/audio_supervisor.yaml
name: AudioSupervisor
system_prompt_template: |
  你是音频分类专家...
prompt_variables:
  data_type: "音频分类"

# 代码中使用
profile = get_profile("AudioSupervisor")
agent = SupervisorAgentV2(llm, profile_name="AudioSupervisor")
```

---

## 迁移收益

| 指标 | 预期改进 |
|------|---------|
| **配置调整时间** | 从 10 分钟 → 10 秒 |
| **新功能上线** | 从改代码 → 改配置 |
| **A/B 测试** | 从不可行 → 一行配置 |
| **故障恢复** | 从回滚代码 → 关闭特性 |
| **团队协作** | 冲突多 → 配置独立 |
