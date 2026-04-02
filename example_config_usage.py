"""
配置系统使用示例
展示如何使用新的配置化架构
"""

import asyncio
from config import (
    feature_enabled, enable_feature, disable_feature,
    get_config, set_config,
    get_profile, AgentProfileRegistry,
    WorkflowBlueprint, WorkflowBuilder, NodeType,
    create_standard_blueprint, create_minimal_blueprint
)
from config.feature_flags import Feature


def demo_feature_flags():
    """演示特性开关系统"""
    print("=" * 70)
    print("🚩 特性开关系统演示")
    print("=" * 70)
    
    # 检查特性状态
    print("\n当前特性状态:")
    print(f"  iterative_search: {feature_enabled(Feature.ITERATIVE_SEARCH)}")
    print(f"  knowledge_base: {feature_enabled(Feature.KNOWLEDGE_BASE)}")
    print(f"  hitl_approval: {feature_enabled(Feature.HITL_APPROVAL)}")
    print(f"  auto_test: {feature_enabled(Feature.AUTO_TEST)}")
    
    # 启用/禁用特性
    print("\n启用 auto_test...")
    enable_feature(Feature.AUTO_TEST)
    print(f"  auto_test: {feature_enabled(Feature.AUTO_TEST)}")
    
    print("\n禁用 iterative_search...")
    disable_feature(Feature.ITERATIVE_SEARCH)
    print(f"  iterative_search: {feature_enabled(Feature.ITERATIVE_SEARCH)}")
    
    # 恢复默认
    print("\n恢复默认...")
    from config.feature_flags import get_feature_flags
    flags = get_feature_flags()
    flags.reset(Feature.AUTO_TEST)
    flags.reset(Feature.ITERATIVE_SEARCH)
    
    print(f"  auto_test: {feature_enabled(Feature.AUTO_TEST)}")
    print(f"  iterative_search: {feature_enabled(Feature.ITERATIVE_SEARCH)}")


def demo_config_manager():
    """演示配置管理器"""
    print("\n" + "=" * 70)
    print("⚙️  配置管理器演示")
    print("=" * 70)
    
    config = get_config()
    
    # 读取配置
    print("\n当前配置:")
    print(f"  agent.llm_temperature: {config.get('agent.llm_temperature')}")
    print(f"  agent.search_max_workers: {config.get('agent.search_max_workers')}")
    print(f"  workflow.parallel_search: {config.get('workflow.parallel_search')}")
    
    # 修改配置
    print("\n修改配置...")
    set_config('agent.llm_temperature', 0.5)
    set_config('agent.search_max_workers', 5)
    
    print(f"  agent.llm_temperature: {config.get('agent.llm_temperature')}")
    print(f"  agent.search_max_workers: {config.get('agent.search_max_workers')}")
    
    # 获取配置对象
    agent_config = config.get_agent_config()
    print(f"\nAgentConfig 对象:")
    print(f"  llm_temperature: {agent_config.llm_temperature}")
    print(f"  search_max_workers: {agent_config.search_max_workers}")


def demo_agent_profiles():
    """演示 Agent 配置文件"""
    print("\n" + "=" * 70)
    print("👤 Agent 配置文件演示")
    print("=" * 70)
    
    registry = AgentProfileRegistry()
    
    # 列出所有配置
    print("\n可用 Agent 配置:")
    for name, profile in registry.get_all().items():
        print(f"  - {name}: {profile.description}")
        print(f"    能力: {', '.join(profile.capabilities[:3])}...")
    
    # 获取特定配置
    supervisor = get_profile("Supervisor")
    print(f"\nSupervisor 配置:")
    print(f"  描述: {supervisor.description}")
    print(f"  能力: {supervisor.capabilities}")
    print(f"  max_directions: {supervisor.get_behavior('max_directions')}")
    
    # 生成系统提示词
    prompt = supervisor.get_system_prompt(
        max_directions=5,
        data_type="音频分类",
        project_type="Kaggle竞赛"
    )
    print(f"\n生成的系统提示词 (前300字符):")
    print(prompt[:300] + "...")
    
    # 创建自定义配置
    custom_profile = registry.create_custom_profile(
        base_name="Supervisor",
        new_name="CustomSupervisor",
        overrides={
            "prompt_variables": {"max_directions": 2},
            "behaviors": {"enable_eda": False}
        }
    )
    print(f"\n自定义配置 CustomSupervisor:")
    print(f"  max_directions: {custom_profile.get_behavior('max_directions')}")
    print(f"  enable_eda: {custom_profile.get_behavior('enable_eda')}")


def demo_workflow_blueprints():
    """演示工作流蓝图"""
    print("\n" + "=" * 70)
    print("📊 工作流蓝图演示")
    print("=" * 70)
    
    # 标准工作流
    standard = create_standard_blueprint()
    print(f"\n标准工作流: {standard.name}")
    print(f"  节点: {[n.name for n in standard.nodes]}")
    print(f"  边: {[(e.source, e.target) for e in standard.edges]}")
    
    # 最小化工作流
    minimal = create_minimal_blueprint()
    print(f"\n最小化工作流: {minimal.name}")
    print(f"  节点: {[n.name for n in minimal.nodes]}")
    
    # 自定义工作流
    print("\n使用 WorkflowBuilder 创建自定义工作流:")
    builder = WorkflowBuilder("custom_workflow", "自定义工作流")
    
    blueprint = (builder
        .add_node(
            name="analyze",
            node_type=NodeType.RESEARCH,
            agent="Supervisor",
            description="分析项目",
            outputs=["directions"]
        )
        .add_node(
            name="search",
            node_type=NodeType.SEARCH,
            agent="Search",
            description="搜索资源",
            inputs=["directions"],
            outputs=["papers"],
            required_features=["parallel_search"]
        )
        .add_node(
            name="code",
            node_type=NodeType.IMPLEMENT,
            agent="Engineer",
            description="生成代码",
            inputs=["papers"],
            outputs=["code"]
        )
        .sequential("analyze", "search", "code")
        .with_config(enable_caching=True)
        .build()
    )
    
    print(f"\n自定义工作流: {blueprint.name}")
    print(f"  描述: {blueprint.description}")
    print(f"  节点: {[n.name for n in blueprint.nodes]}")
    print(f"  全局配置: {blueprint.global_config}")
    
    # 验证工作流
    errors = blueprint.validate()
    print(f"\n验证结果: {len(errors)} 个错误")
    for error in errors:
        print(f"  - {error}")
    
    # 导出为字典
    blueprint_dict = blueprint.to_dict()
    print(f"\n蓝图字典 (简化):")
    print(f"  name: {blueprint_dict['name']}")
    print(f"  nodes: {len(blueprint_dict['nodes'])} 个")


def demo_integration():
    """演示配置系统的集成使用"""
    print("\n" + "=" * 70)
    print("🔗 集成使用演示 - 根据配置动态构建工作流")
    print("=" * 70)
    
    # 场景1：快速模式（跳过搜索）
    print("\n场景1: 快速模式")
    disable_feature(Feature.PARALLEL_SEARCH)
    
    blueprint = create_standard_blueprint()
    available_nodes = [n.name for n in blueprint.nodes if n.is_available({})]
    print(f"  可用节点: {available_nodes}")
    
    # 场景2：完整模式（启用所有功能）
    print("\n场景2: 完整模式")
    enable_feature(Feature.PARALLEL_SEARCH)
    enable_feature(Feature.HITL_APPROVAL)
    
    blueprint = create_standard_blueprint()
    available_nodes = [n.name for n in blueprint.nodes if n.is_available({})]
    print(f"  可用节点: {available_nodes}")
    
    # 场景3：自动测试模式
    print("\n场景3: 自动测试模式")
    enable_feature(Feature.AUTO_TEST)
    
    blueprint = create_standard_blueprint()
    available_nodes = [n.name for n in blueprint.nodes if n.is_available({})]
    print(f"  可用节点: {available_nodes}")
    
    # 恢复默认
    from config.feature_flags import get_feature_flags
    flags = get_feature_flags()
    for feature in [Feature.PARALLEL_SEARCH, Feature.HITL_APPROVAL, Feature.AUTO_TEST]:
        flags.reset(feature)


def show_config_yaml():
    """展示推荐的配置文件格式"""
    print("\n" + "=" * 70)
    print("📝 推荐配置文件格式 (evo_config.yaml)")
    print("=" * 70)
    
    config_example = """
# ============= 特性开关 =============
features:
  iterative_search: true
  knowledge_base: true
  incremental_code: true
  hitl_approval: false      # 默认关闭
  auto_test: false          # 默认关闭

# ============= Agent 配置 =============
agent:
  supervisor_max_directions: 3
  search_max_workers: 3
  engineer_code_style: "incremental"

# ============= 工作流配置 =============
workflow:
  enable_research: true
  enable_search: true
  enable_test: false

# ============= 自定义配置 =============
custom:
  project_type: "competition"
"""
    print(config_example)


async def main():
    """主函数"""
    print("\n" + "🚀" * 35)
    print("  EvoAgentX 配置系统演示")
    print("🚀" * 35)
    
    demo_feature_flags()
    demo_config_manager()
    demo_agent_profiles()
    demo_workflow_blueprints()
    demo_integration()
    show_config_yaml()
    
    print("\n" + "=" * 70)
    print("✅ 演示完成！")
    print("=" * 70)
    print("""
使用建议:
1. 复制 evo_config_example.yaml 为 evo_config.yaml
2. 修改配置以适应你的需求
3. 使用 feature_enabled() 检查特性状态
4. 使用 get_profile() 获取 Agent 配置
5. 使用 WorkflowBuilder 构建自定义工作流

环境变量覆盖:
  EVO_FEATURE_AUTO_TEST=true python main.py
""")


if __name__ == "__main__":
    asyncio.run(main())
