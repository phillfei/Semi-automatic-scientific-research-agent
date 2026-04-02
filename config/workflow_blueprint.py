"""
工作流蓝图系统 - 动态构建工作流
参考 src 的命令和工作流系统
"""

import json
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy


class NodeType(str, Enum):
    """节点类型"""
    RESEARCH = "research"           # 研究分析
    SEARCH = "search"               # 搜索资源
    IMPLEMENT = "implement"         # 代码实现
    TEST = "test"                   # 测试验证
    REVIEW = "review"               # 审查评估
    HITL = "hitl"                   # 人工审批
    CONDITION = "condition"         # 条件分支
    PARALLEL = "parallel"           # 并行执行


@dataclass
class WorkflowNode:
    """工作流节点定义"""
    name: str
    node_type: NodeType
    description: str = ""
    
    # 执行的 Agent
    agent: Optional[str] = None
    
    # 输入参数
    inputs: List[str] = field(default_factory=list)
    
    # 输出参数
    outputs: List[str] = field(default_factory=list)
    
    # 条件执行（仅 CONDITION 类型）
    condition: Optional[Callable[[Dict], bool]] = None
    
    # 是否启用
    enabled: bool = True
    
    # 配置覆盖
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # 超时时间（秒）
    timeout: Optional[int] = None
    
    # 重试配置
    max_retries: int = 0
    retry_delay: float = 1.0
    
    # 前置条件：需要哪些特性
    required_features: List[str] = field(default_factory=list)
    
    def is_available(self, context: Dict) -> bool:
        """检查节点是否可用"""
        if not self.enabled:
            return False
        
        # 检查特性要求
        from .feature_flags import feature_enabled
        for feature in self.required_features:
            if not feature_enabled(feature):
                return False
        
        # 检查条件
        if self.condition:
            try:
                return self.condition(context)
            except:
                return False
        
        return True


@dataclass
class WorkflowEdge:
    """工作流边定义"""
    source: str
    target: str
    
    # 条件边
    condition: Optional[str] = None
    
    # 数据映射：source输出 -> target输入
    data_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowBlueprint:
    """
    工作流蓝图 - 可配置的工作流定义
    """
    name: str
    description: str
    
    # 节点列表
    nodes: List[WorkflowNode] = field(default_factory=list)
    
    # 边列表
    edges: List[WorkflowEdge] = field(default_factory=list)
    
    # 全局配置
    global_config: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_node(self, name: str) -> Optional[WorkflowNode]:
        """获取节点"""
        for node in self.nodes:
            if node.name == name:
                return node
        return None
    
    def get_next_nodes(self, node_name: str, context: Dict) -> List[WorkflowNode]:
        """获取下一个可用节点"""
        next_nodes = []
        for edge in self.edges:
            if edge.source == node_name:
                target = self.get_node(edge.target)
                if target and target.is_available(context):
                    next_nodes.append(target)
        return next_nodes
    
    def validate(self) -> List[str]:
        """验证工作流蓝图"""
        errors = []
        
        # 检查节点名称唯一
        names = [n.name for n in self.nodes]
        if len(names) != len(set(names)):
            errors.append("存在重复的节点名称")
        
        # 检查边的有效性
        node_names = set(names)
        for edge in self.edges:
            if edge.source not in node_names:
                errors.append(f"边的源节点不存在: {edge.source}")
            if edge.target not in node_names:
                errors.append(f"边的目标节点不存在: {edge.target}")
        
        # 检查孤立节点
        connected = set()
        for edge in self.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        
        for node in self.nodes:
            if node.name not in connected and len(self.nodes) > 1:
                errors.append(f"孤立节点: {node.name}")
        
        return errors
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'name': self.name,
            'description': self.description,
            'nodes': [
                {
                    'name': n.name,
                    'type': n.node_type.value,
                    'description': n.description,
                    'agent': n.agent,
                    'inputs': n.inputs,
                    'outputs': n.outputs,
                    'enabled': n.enabled,
                    'timeout': n.timeout,
                    'max_retries': n.max_retries,
                    'required_features': n.required_features
                }
                for n in self.nodes
            ],
            'edges': [
                {
                    'source': e.source,
                    'target': e.target,
                    'condition': e.condition,
                    'data_mapping': e.data_mapping
                }
                for e in self.edges
            ],
            'global_config': self.global_config,
            'metadata': self.metadata
        }


class WorkflowBuilder:
    """
    工作流构建器 - 链式 API 构建工作流
    """
    
    def __init__(self, name: str, description: str = ""):
        self.blueprint = WorkflowBlueprint(
            name=name,
            description=description
        )
        self._last_node: Optional[str] = None
    
    def add_node(
        self,
        name: str,
        node_type: NodeType,
        agent: Optional[str] = None,
        description: str = "",
        inputs: List[str] = None,
        outputs: List[str] = None,
        enabled: bool = True,
        timeout: Optional[int] = None,
        required_features: List[str] = None,
        **config_overrides
    ) -> 'WorkflowBuilder':
        """添加节点"""
        node = WorkflowNode(
            name=name,
            node_type=node_type,
            description=description,
            agent=agent,
            inputs=inputs or [],
            outputs=outputs or [],
            enabled=enabled,
            timeout=timeout,
            required_features=required_features or [],
            config_overrides=config_overrides
        )
        self.blueprint.nodes.append(node)
        self._last_node = name
        return self
    
    def add_edge(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        condition: Optional[str] = None,
        data_mapping: Dict[str, str] = None
    ) -> 'WorkflowBuilder':
        """添加边"""
        if source is None:
            source = self._last_node
        
        if source and target:
            edge = WorkflowEdge(
                source=source,
                target=target,
                condition=condition,
                data_mapping=data_mapping or {}
            )
            self.blueprint.edges.append(edge)
        
        return self
    
    def sequential(self, *node_names: str) -> 'WorkflowBuilder':
        """按顺序连接多个节点"""
        for i in range(len(node_names) - 1):
            self.add_edge(node_names[i], node_names[i + 1])
        return self
    
    def parallel(self, source: str, *targets: str) -> 'WorkflowBuilder':
        """从一个节点并行到多个节点"""
        for target in targets:
            self.add_edge(source, target)
        return self
    
    def with_config(self, **kwargs) -> 'WorkflowBuilder':
        """设置全局配置"""
        self.blueprint.global_config.update(kwargs)
        return self
    
    def build(self) -> WorkflowBlueprint:
        """构建蓝图"""
        errors = self.blueprint.validate()
        if errors:
            raise ValueError(f"工作流验证失败: {', '.join(errors)}")
        return self.blueprint


def create_standard_blueprint() -> WorkflowBlueprint:
    """创建标准优化工作流蓝图"""
    builder = WorkflowBuilder(
        name="standard_optimization",
        description="标准代码优化工作流"
    )
    
    return (builder
        .add_node(
            name="research",
            node_type=NodeType.RESEARCH,
            agent="Supervisor",
            description="深度研究项目",
            inputs=[],
            outputs=["analysis", "directions"],
            required_features=["supervisor_eda"]
        )
        .add_node(
            name="hitl_review_directions",
            node_type=NodeType.HITL,
            description="人工审批优化方向",
            inputs=["directions"],
            outputs=["approved_directions"],
            enabled=False,  # 默认关闭
            required_features=["hitl_approval"]
        )
        .add_node(
            name="search",
            node_type=NodeType.SEARCH,
            agent="Search",
            description="并行搜索相关资源",
            inputs=["directions"],
            outputs=["search_results"],
            required_features=["parallel_search"]
        )
        .add_node(
            name="implement",
            node_type=NodeType.IMPLEMENT,
            agent="Engineer",
            description="生成优化代码",
            inputs=["search_results", "analysis"],
            outputs=["code", "tests"],
            required_features=["incremental_code"]
        )
        .add_node(
            name="test",
            node_type=NodeType.TEST,
            agent="Test",
            description="执行测试验证",
            inputs=["code", "tests"],
            outputs=["test_results"],
            enabled=False,  # 默认关闭
            required_features=["auto_test"]
        )
        .sequential("research", "search", "implement")
        .with_config(
            max_parallel_search=3,
            enable_caching=True
        )
        .build()
    )


def create_minimal_blueprint() -> WorkflowBlueprint:
    """创建最小化工作流（仅实现，无搜索）"""
    builder = WorkflowBuilder(
        name="minimal_implementation",
        description="最小化实现工作流"
    )
    
    return (builder
        .add_node(
            name="research",
            node_type=NodeType.RESEARCH,
            agent="Supervisor",
            description="快速分析",
            outputs=["analysis", "directions"]
        )
        .add_node(
            name="implement",
            node_type=NodeType.IMPLEMENT,
            agent="Engineer",
            description="直接生成代码",
            inputs=["directions"],
            outputs=["code"]
        )
        .sequential("research", "implement")
        .build()
    )


def create_advanced_blueprint() -> WorkflowBlueprint:
    """创建高级工作流（包含测试和审查）"""
    builder = WorkflowBuilder(
        name="advanced_optimization",
        description="高级优化工作流（含测试和审查）"
    )
    
    return (builder
        .add_node(
            name="research",
            node_type=NodeType.RESEARCH,
            agent="Supervisor",
            outputs=["analysis", "directions"]
        )
        .add_node(
            name="search",
            node_type=NodeType.SEARCH,
            agent="Search",
            inputs=["directions"],
            outputs=["search_results"]
        )
        .add_node(
            name="implement",
            node_type=NodeType.IMPLEMENT,
            agent="Engineer",
            inputs=["search_results"],
            outputs=["code", "tests"]
        )
        .add_node(
            name="test",
            node_type=NodeType.TEST,
            agent="Test",
            inputs=["code", "tests"],
            outputs=["test_results"],
            required_features=["auto_test"]
        )
        .add_node(
            name="review",
            node_type=NodeType.REVIEW,
            agent="Supervisor",
            inputs=["test_results", "code"],
            outputs=["review_report"]
        )
        .sequential("research", "search", "implement", "test", "review")
        .build()
    )
