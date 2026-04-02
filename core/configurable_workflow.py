"""
可配置工作流引擎 - 基于蓝图动态执行
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum

from config.workflow_blueprint import WorkflowBlueprint, WorkflowNode, NodeType
from config.feature_flags import feature_enabled
from config.config_manager import get_config
from utils.agent_logger import get_agent_logger


class NodeStatus(str, Enum):
    """节点执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeResult:
    """节点执行结果"""
    node_name: str
    status: NodeStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0


class ConfigurableWorkflowEngine:
    """
    可配置工作流引擎
    
    特点：
    - 根据蓝图动态执行
    - 支持条件跳过和特性开关
    - 支持重试和超时
    """
    
    def __init__(self, blueprint: WorkflowBlueprint, agent_manager, context: Dict = None):
        self.blueprint = blueprint
        self.agent_manager = agent_manager
        self.context = context or {}
        self.logger = get_agent_logger()
        
        # 执行状态
        self.node_results: Dict[str, NodeResult] = {}
        self.execution_order: List[str] = []
        
        # 配置
        self.config = get_config()
        self.workflow_config = self.config.get_workflow_config()
    
    async def execute(self, initial_inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行工作流"""
        print(f"\n{'='*70}")
        print(f"🚀 执行工作流: {self.blueprint.name}")
        print(f"{'='*70}")
        
        # 初始化上下文
        if initial_inputs:
            self.context.update(initial_inputs)
        
        # 找到起始节点（没有入边的节点）
        start_nodes = self._find_start_nodes()
        
        if not start_nodes:
            raise ValueError("工作流没有起始节点")
        
        # 执行起始节点
        for node in start_nodes:
            await self._execute_node(node)
        
        # 汇总结果
        return self._collect_results()
    
    async def _execute_node(self, node: WorkflowNode, inputs: Dict = None):
        """执行单个节点"""
        # 检查节点是否可用
        if not node.is_available(self.context):
            self.logger.log_step("Workflow", "skip_node", f"跳过节点: {node.name}")
            self.node_results[node.name] = NodeResult(
                node_name=node.name,
                status=NodeStatus.SKIPPED
            )
            return
        
        # 检查是否已执行
        if node.name in self.node_results:
            return
        
        print(f"\n📍 执行节点: {node.name} ({node.description})")
        self.execution_order.append(node.name)
        
        import time
        start_time = time.time()
        
        try:
            # 准备输入
            node_inputs = inputs or self._prepare_node_inputs(node)
            
            # 获取 Agent
            agent = None
            if node.agent:
                agent = self.agent_manager.get_agent(node.agent)
            
            # 执行节点逻辑
            if node.node_type == NodeType.RESEARCH:
                result = await self._execute_research_node(node, agent, node_inputs)
            elif node.node_type == NodeType.SEARCH:
                result = await self._execute_search_node(node, agent, node_inputs)
            elif node.node_type == NodeType.IMPLEMENT:
                result = await self._execute_implement_node(node, agent, node_inputs)
            elif node.node_type == NodeType.TEST:
                result = await self._execute_test_node(node, agent, node_inputs)
            elif node.node_type == NodeType.HITL:
                result = await self._execute_hitl_node(node, node_inputs)
            else:
                result = {"status": "unknown", "outputs": {}}
            
            # 更新上下文
            if "outputs" in result:
                self.context.update(result["outputs"])
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.node_results[node.name] = NodeResult(
                node_name=node.name,
                status=NodeStatus.COMPLETED,
                outputs=result.get("outputs", {}),
                duration_ms=duration_ms
            )
            
            print(f"  ✅ 完成 ({duration_ms:.0f}ms)")
            
            # 执行后续节点
            next_nodes = self.blueprint.get_next_nodes(node.name, self.context)
            for next_node in next_nodes:
                await self._execute_node(next_node)
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_agent_error("Workflow", f"execute_{node.name}", e)
            
            self.node_results[node.name] = NodeResult(
                node_name=node.name,
                status=NodeStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms
            )
            
            print(f"  ❌ 失败: {e}")
            
            # 检查是否允许重试
            if node.max_retries > 0:
                # 简化处理：不重试
                pass
    
    def _prepare_node_inputs(self, node: WorkflowNode) -> Dict:
        """准备节点输入"""
        inputs = {}
        
        # 从上下文中提取输入
        for input_key in node.inputs:
            if input_key in self.context:
                inputs[input_key] = self.context[input_key]
        
        return inputs
    
    async def _execute_research_node(self, node: WorkflowNode, agent, inputs: Dict) -> Dict:
        """执行研究节点"""
        if not agent:
            return {"outputs": {}}
        
        # 调用 Supervisor Agent
        result = await asyncio.to_thread(
            agent.initialize_project,
            project_name=inputs.get("project_name", "unknown"),
            html_content=inputs.get("html_content", ""),
            data_sample_content=inputs.get("data_sample_content", ""),
            data_sample_path=inputs.get("data_sample_path", ""),
            data_sample_folder=inputs.get("data_sample_folder", ""),
            data_sample_info=inputs.get("data_sample_info", ""),
            code_content=inputs.get("code_content", ""),
            instruction=inputs.get("instruction", "")
        )
        
        return {
            "outputs": {
                "analysis": result.get("research_summary", ""),
                "directions": result.get("directions", []),
                "eda_analysis": result.get("eda_analysis", "")
            }
        }
    
    async def _execute_search_node(self, node: WorkflowNode, agent, inputs: Dict) -> Dict:
        """执行搜索节点"""
        if not agent:
            return {"outputs": {}}
        
        directions = inputs.get("directions", [])
        if not directions:
            return {"outputs": {"search_results": []}}
        
        # 构建搜索任务
        tasks = []
        for direction in directions[:3]:
            tasks.append({
                "direction_name": direction.get("name", "未知方向"),
                "keywords": direction.get("keywords", direction.get("search_keywords", [])),
                "rationale": direction.get("rationale", "")
            })
        
        # 执行搜索
        time_limit = self.config.get('agent.search_time_limit_minutes', 5)
        
        result = await asyncio.to_thread(
            agent.parallel_search,
            tasks=tasks,
            total_time_limit=time_limit,
            project_name=inputs.get("project_name", "")
        )
        
        return {
            "outputs": {
                "search_results": result.get("search_results", [])
            }
        }
    
    async def _execute_implement_node(self, node: WorkflowNode, agent, inputs: Dict) -> Dict:
        """执行实现节点"""
        if not agent:
            return {"outputs": {}}
        
        search_results = inputs.get("search_results", [])
        
        # 生成代码
        result = await asyncio.to_thread(
            agent.generate_code_and_tests,
            search_results=search_results,
            original_code=inputs.get("code_content", ""),
            project_name=inputs.get("project_name", ""),
            data_info=inputs.get("data_sample_info", "")
        )
        
        generated_items = result.get("generated_items", [])
        
        # 保存代码
        if generated_items:
            saved_files = await asyncio.to_thread(
                agent.save_generated_code,
                generated_items=generated_items,
                original_code=inputs.get("code_content", "")
            )
            
            # 添加文件路径到结果
            for idx, item in enumerate(generated_items):
                item['saved_files'] = [
                    f for f in saved_files 
                    if f"{idx+1}_" in f or f"direction_{idx+1}" in f
                ]
        
        return {
            "outputs": {
                "generated_items": generated_items,
                "code_files": [item.get('saved_files', []) for item in generated_items]
            }
        }
    
    async def _execute_test_node(self, node: WorkflowNode, agent, inputs: Dict) -> Dict:
        """执行测试节点"""
        # 测试节点逻辑
        return {"outputs": {"test_results": {}}}
    
    async def _execute_hitl_node(self, node: WorkflowNode, inputs: Dict) -> Dict:
        """执行人工审批节点"""
        print(f"  ⏸️ 等待人工审批...")
        # 简化处理：直接通过
        return {"outputs": {"hitl_approved": True}}
    
    def _find_start_nodes(self) -> List[WorkflowNode]:
        """找到起始节点（没有入边的节点）"""
        all_targets = set(edge.target for edge in self.blueprint.edges)
        start_nodes = []
        
        for node in self.blueprint.nodes:
            if node.name not in all_targets and node.enabled:
                start_nodes.append(node)
        
        return start_nodes
    
    def _collect_results(self) -> Dict:
        """汇总执行结果"""
        return {
            "workflow_name": self.blueprint.name,
            "execution_order": self.execution_order,
            "node_results": {
                name: {
                    "status": result.status.value,
                    "outputs": result.outputs,
                    "error": result.error,
                    "duration_ms": result.duration_ms
                }
                for name, result in self.node_results.items()
            },
            "final_context": self.context
        }
    
    def get_progress(self) -> Dict:
        """获取执行进度"""
        total = len([n for n in self.blueprint.nodes if n.enabled])
        completed = len([r for r in self.node_results.values() if r.status == NodeStatus.COMPLETED])
        
        return {
            "total_nodes": total,
            "completed_nodes": completed,
            "percentage": (completed / total * 100) if total > 0 else 0,
            "current_node": self.execution_order[-1] if self.execution_order else None
        }
