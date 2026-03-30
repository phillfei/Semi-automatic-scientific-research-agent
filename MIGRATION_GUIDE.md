# Knowledge Base 迁移到 EvoAgentX 项目指南

## 迁移对照表

| Knowledge Base 组件 | EvoAgentX 对应组件 | 状态 |
|-------------------|-------------------|------|
| `agents/supervisor_agent.py` | `agents/supervisor_agent.py` | ✅ 已迁移 |
| `agents/search_agent.py` | `agents/search_agent.py` | ⏳ 待迁移 |
| `agents/planner_agent.py` | `agents/planner_agent.py` | ⏳ 待迁移 |
| `agents/engineer_agent.py` | `agents/engineer_agent.py` | ⏳ 待迁移 |
| `agents/maintenance_agent.py` | `agents/maintenance_agent.py` | ⏳ 待迁移 |
| `app.py` (Flask) | `backend/app.py` (FastAPI) | ✅ 已创建基础 |
| `main_enhanced.py` | `main.py` | ✅ 已简化 |
| `utils/project_manager.py` | EvoAgentX 内置 | ⏳ 需适配 |
| `web_interface/` | `frontend/` | ⏳ 需迁移 |

## 快速迁移步骤

### 1. 安装依赖
```bash
cd evo_code_optimizer
pip install -r requirements.txt
```

### 2. 配置环境
```bash
# 编辑 .env 文件
KIMI_API_KEY=your-kimi-api-key
```

### 3. 迁移业务逻辑
将 `knowledge_base/agents/` 中的业务逻辑复制到 `evo_code_optimizer/agents/`，并修改：
- 继承 `evoagentx.agents.Agent` 而非自定义基类
- 使用 `self.llm.generate()` 替代 `call_chat_llm()`
- 使用 EvoAgentX 的工具系统

### 4. 创建工作流
```python
# workflows/optimization_workflow.py
from evoagentx.workflow import WorkFlow
from evoagentx.agents import AgentManager

def create_workflow(project_name, llm):
    manager = AgentManager()
    # 添加迁移后的 Agent
    from agents.supervisor_agent import SupervisorAgent
    from agents.search_agent import SearchAgent
    # ...
    
    manager.add_agent(SupervisorAgent(llm))
    manager.add_agent(SearchAgent(llm))
    # ...
    
    return WorkFlow(agent_manager=manager)
```

### 5. 启动服务
```bash
python backend/app.py
```

## 关键改动说明

### Agent 基类变化
```python
# Before (knowledge_base)
class SupervisorAgent:
    def __init__(self, llm_config=None):
        self.llm_config = llm_config or {}
    
    def initialize_project(self, ...):
        result = call_chat_llm(...)

# After (evo_code_optimizer)
from evoagentx.agents import Agent

class SupervisorAgent(Agent):
    def __init__(self, llm, project_manager=None):
        super().__init__(name="Supervisor", llm=llm, system_prompt="...")
        self.project_manager = project_manager
    
    def initialize_project(self, ...):
        result = self.llm.generate(prompt=...)
```

### 工作流编排变化
```python
# Before: 手动顺序调用
supervisor_result = supervisor.initialize_project(...)
search_result = search.parallel_search(...)
engineer_result = engineer.generate_code(...)

# After: EvoAgentX WorkFlow
workflow = WorkFlow(agent_manager=manager)
result = workflow.run(inputs)
```

## 下一步任务

- [ ] 迁移 search_agent.py
- [ ] 迁移 planner_agent.py  
- [ ] 迁移 engineer_agent.py
- [ ] 迁移 maintenance_agent.py
- [ ] 创建完整工作流编排
- [ ] 迁移前端界面
- [ ] 集成测试

## 参考文档

- `knowledge_base/EVOAGENTX_INTEGRATION.md` - 完整集成方案
- `knowledge_base/QUICK_START.md` - 快速启动指南
- `knowledge_base/VPN_REQUIREMENTS.md` - VPN 需求说明