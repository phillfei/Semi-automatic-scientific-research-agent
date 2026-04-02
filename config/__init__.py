"""
配置系统 - 参考 Claude Code CLI 的架构设计
提供特性开关、配置管理和动态行为控制

使用示例:
    # 特性开关
    from config import feature_enabled, Feature
    if feature_enabled(Feature.ITERATIVE_SEARCH):
        # 执行迭代搜索
        pass
    
    # 配置管理
    from config import get_config, set_config
    temp = get_config('agent.llm_temperature')
    set_config('agent.llm_temperature', 0.5)
    
    # Agent 配置
    from config import get_profile
    profile = get_profile('Supervisor')
    prompt = profile.get_system_prompt(max_directions=3)
    
    # 工作流蓝图
    from config import WorkflowBuilder, NodeType, create_standard_blueprint
    blueprint = create_standard_blueprint()
"""

# 特性开关系统
from .feature_flags import (
    FeatureFlags,
    Feature,
    feature_enabled,
    enable_feature,
    disable_feature,
    get_feature_flags
)

# 配置管理器
from .config_manager import (
    ConfigManager,
    AgentConfig,
    WorkflowConfig,
    OutputConfig,
    get_config,
    set_config
)

# Agent 配置文件
from .agent_profiles import (
    AgentProfile,
    AgentProfileRegistry,
    get_profile,
    get_registry
)

# 工作流蓝图
from .workflow_blueprint import (
    WorkflowBlueprint,
    WorkflowNode,
    WorkflowEdge,
    WorkflowBuilder,
    NodeType,
    create_standard_blueprint,
    create_minimal_blueprint,
    create_advanced_blueprint
)

# V2 提示词模板
from .prompts_v2 import (
    SUPERVISOR_PROMPT_TEMPLATE_V2,
    CONSTRAINT_AGENT_PROMPT,
    ENGINEER_PROMPT_TEMPLATE_V2,
    get_supervisor_prompt_v2,
    get_engineer_prompt_v2,
    get_constraint_agent_prompt,
    fill_prompt_template
)

# V2 Agent 导出
from agents.v2.constraint_agent import ConstraintAgent
from agents.v2.baseline_analyzer import BaselineAnalyzer
from agents.v2.engineer_agent_v2 import EngineerAgentV2

__all__ = [
    # 特性开关
    'FeatureFlags',
    'Feature',
    'feature_enabled',
    'enable_feature',
    'disable_feature',
    'get_feature_flags',
    
    # 配置管理
    'ConfigManager',
    'AgentConfig',
    'WorkflowConfig',
    'OutputConfig',
    'get_config',
    'set_config',
    
    # Agent 配置
    'AgentProfile',
    'AgentProfileRegistry',
    'get_profile',
    'get_registry',
    
    # 工作流蓝图
    'WorkflowBlueprint',
    'WorkflowNode',
    'WorkflowEdge',
    'WorkflowBuilder',
    'NodeType',
    'create_standard_blueprint',
    'create_minimal_blueprint',
    'create_advanced_blueprint',
    
    # V2 提示词模板
    'SUPERVISOR_PROMPT_TEMPLATE_V2',
    'CONSTRAINT_AGENT_PROMPT',
    'ENGINEER_PROMPT_TEMPLATE_V2',
    'get_supervisor_prompt_v2',
    'get_engineer_prompt_v2',
    'get_constraint_agent_prompt',
    'fill_prompt_template',
]
