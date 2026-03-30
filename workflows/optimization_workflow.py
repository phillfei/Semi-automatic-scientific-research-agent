"""
代码优化工作流 - 基于 EvoAgentX
整合所有Agent的完整工作流
"""

from evoagentx.workflow import WorkFlow
from evoagentx.agents import AgentManager
from evoagentx.hitl import HITLManager
from evoagentx.workflow.workflow_graph import WorkFlowGraph, WorkFlowNode, WorkFlowEdge
from evoagentx.core.base_config import Parameter


def create_workflow(project_name, llm, hitl_manager=None, project_manager=None):
    """创建代码优化工作流
    
    Args:
        project_name: 项目名称
        llm: 所有Agent共用的LLM实例
        hitl_manager: HITL管理器（可选）
        project_manager: 项目管理器（可选）
    """
    
    # 导入Agent
    from agents.supervisor_agent import SupervisorAgent
    from agents.search_agent import SearchAgent
    from agents.engineer_agent import EngineerAgent
    
    # 创建Agent管理器
    manager = AgentManager()
    
    # 所有Agent使用相同的LLM
    supervisor = SupervisorAgent(llm=llm, project_manager=project_manager)
    search = SearchAgent(llm=llm, project_manager=project_manager)
    engineer = EngineerAgent(llm=llm)
    
    manager.add_agent(supervisor)
    manager.add_agent(search)
    manager.add_agent(engineer)
    
    print(f"\n{'='*70}")
    print(f"🚀 工作流配置完成: {project_name}")
    print(f"{'='*70}")
    print(f"  🎯 Supervisor Agent")
    print(f"  🔍 Search Agent")
    print(f"  🔧 Engineer Agent")
    print(f"{'='*70}")
    
    # 创建工作流图，定义正确的 inputs/outputs 确保数据流传递
    # 使用 Parameter 对象定义输入输出参数
    graph = WorkFlowGraph(
        goal=f"优化项目: {project_name}",
        nodes=[
            WorkFlowNode(
                name="research",
                description="深度研究和分析项目",
                inputs=[],
                outputs=[
                    Parameter(name="analysis", type="str", description="项目分析结果", required=True),
                    Parameter(name="directions", type="list", description="优化方向列表", required=True),
                ],
                agents=["Supervisor"]
            ),
            WorkFlowNode(
                name="search",
                description="搜索相关学术资源",
                inputs=[
                    Parameter(name="directions", type="list", description="优化方向列表", required=True),
                ],
                outputs=[
                    Parameter(name="search_results", type="list", description="搜索结果列表", required=True),
                ],
                agents=["Search"]
            ),
            WorkFlowNode(
                name="implement",
                description="生成优化代码",
                inputs=[
                    Parameter(name="search_results", type="list", description="搜索结果列表", required=True),
                    Parameter(name="analysis", type="str", description="项目分析结果", required=False),
                ],
                outputs=[
                    Parameter(name="code", type="str", description="生成的代码", required=True),
                    Parameter(name="tests", type="str", description="生成的测试代码", required=False),
                ],
                agents=["Engineer"]
            ),
        ],
        edges=[
            WorkFlowEdge(source="research", target="search"),
            WorkFlowEdge(source="search", target="implement"),
        ]
    )
    
    # 创建HITL管理器（如果不提供）
    if hitl_manager is None:
        hitl_manager = HITLManager()
    
    # 创建工作流
    workflow = WorkFlow(
        graph=graph,
        llm=llm,
        agent_manager=manager,
        hitl_manager=hitl_manager
    )
    
    return workflow
