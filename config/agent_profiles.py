"""
Agent 配置文件系统 - 可配置的 Agent 角色和行为
类似 src 中可配置的命令和工具
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
from copy import deepcopy


@dataclass
class AgentProfile:
    """
    Agent 配置文件 - 定义 Agent 的角色、能力和行为
    """
    name: str
    description: str
    
    # 系统提示词模板（支持变量替换）
    system_prompt_template: str = ""
    
    # 提示词变量默认值
    prompt_variables: Dict[str, Any] = field(default_factory=dict)
    
    # 能力列表
    capabilities: List[str] = field(default_factory=list)
    
    # 行为配置
    behaviors: Dict[str, Any] = field(default_factory=dict)
    
    # 提示词构建钩子
    _prompt_hooks: List[Callable[[str, Dict], str]] = field(default_factory=list, repr=False)
    
    def get_system_prompt(self, **kwargs) -> str:
        """生成系统提示词 - 支持变量替换和钩子"""
        # 合并变量
        variables = deepcopy(self.prompt_variables)
        variables.update(kwargs)
        
        # 基础模板
        prompt = self.system_prompt_template
        
        # 变量替换
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(value))
        
        # 执行钩子
        for hook in self._prompt_hooks:
            prompt = hook(prompt, variables)
        
        return prompt
    
    def add_prompt_hook(self, hook: Callable[[str, Dict], str]):
        """添加提示词构建钩子"""
        self._prompt_hooks.append(hook)
    
    def set_behavior(self, key: str, value: Any):
        """设置行为配置"""
        self.behaviors[key] = value
    
    def get_behavior(self, key: str, default: Any = None) -> Any:
        """获取行为配置"""
        return self.behaviors.get(key, default)
    
    def has_capability(self, capability: str) -> bool:
        """检查是否有某能力"""
        return capability in self.capabilities
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'name': self.name,
            'description': self.description,
            'system_prompt_template': self.system_prompt_template,
            'prompt_variables': self.prompt_variables,
            'capabilities': self.capabilities,
            'behaviors': self.behaviors
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentProfile':
        """从字典创建"""
        return cls(
            name=data.get('name', 'Unknown'),
            description=data.get('description', ''),
            system_prompt_template=data.get('system_prompt_template', ''),
            prompt_variables=data.get('prompt_variables', {}),
            capabilities=data.get('capabilities', []),
            behaviors=data.get('behaviors', {})
        )


class AgentProfileRegistry:
    """
    Agent 配置注册表 - 管理和加载 Agent 配置
    类似 src 的命令注册系统
    """
    
    _instance: Optional['AgentProfileRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._profiles: Dict[str, AgentProfile] = {}
        self._load_builtin_profiles()
        self._load_custom_profiles()
        
        self._initialized = True
    
    def _load_builtin_profiles(self):
        """加载内置 Agent 配置"""
        
        # ===== Supervisor Agent 配置 =====
        supervisor = AgentProfile(
            name="Supervisor",
            description="主管Agent，负责深度研究、确定优化方向、协调全局",
            system_prompt_template="""你是主管Agent，负责：
1. 深度分析用户上传的HTML规划和代码
2. 进行EDA数据分析（如果有数据文件）
3. 确定最多{max_directions}个优化方向
4. 协调其他Agent工作
5. 基于历史反馈做决策

**重要限制 - 优化方向选择原则**：
1. **禁止**从调整模型结构（如修改网络层数、改变模型架构、设计新模型）入手
2. 优化方向应聚焦于：数据增强、特征工程、损失函数、训练策略、集成方法、后处理等
3. 优先选择数据层面和训练策略层面的优化，而非模型架构层面的修改
4. 保持模型骨干网络不变，关注数据流和训练流程的改进

输出格式：
- 研究总结
- 优化方向（最多{max_directions}个，每个包含名称、理由、关键词）
- EDA分析结果（如有数据）

数据类型：{data_type}
项目类型：{project_type}""",
            prompt_variables={
                'max_directions': 3,
                'data_type': '未知',
                'project_type': '通用'
            },
            capabilities=[
                'project_analysis',
                'eda_analysis',
                'direction_planning',
                'historical_feedback',
                'coordination'
            ],
            behaviors={
                'enable_eda': True,
                'enable_history': True,
                'max_directions': 3,
                'banned_keywords': [
                    '推理速度', 'inference speed', 'latency', '延迟',
                    '内存占用', 'memory usage', '代码重构', '可读性'
                ]
            }
        )
        self.register(supervisor)
        
        # ===== Search Agent 配置 =====
        search = AgentProfile(
            name="Search",
            description="搜索Agent，负责并行检索学术资源和开源项目",
            system_prompt_template="""你是搜索Agent，负责：
1. 并行检索学术资源（arXiv、论文）
2. 搜索开源项目和文档
3. 整理关键技术点
4. 生成Markdown格式研究报告

搜索策略：
- 优先搜索近{year_range}年的论文
- 关注高引用论文
- 提取核心方法和创新点
- 对比不同方法的优缺点

迭代搜索：{enable_iterative}
关键词动态优化：{enable_keyword_refine}""",
            prompt_variables={
                'year_range': 5,
                'enable_iterative': True,
                'enable_keyword_refine': True
            },
            capabilities=[
                'arxiv_search',
                'github_search',
                'iterative_search',
                'keyword_refinement',
                'markdown_report'
            ],
            behaviors={
                'enable_iterative_search': True,
                'enable_keyword_refinement': True,
                'max_workers': 3,
                'papers_per_query': 3,
                'arxiv_delay': 3.0
            }
        )
        self.register(search)
        
        # ===== Engineer Agent 配置 =====
        engineer = AgentProfile(
            name="Engineer",
            description="工程师Agent，负责生成高质量代码和测试用例",
            system_prompt_template="""你是工程师Agent，负责生成高质量的Python代码。

代码生成模式：{code_mode}

代码要求：
1. 代码必须完整、可运行
2. 添加详细的中文注释
3. 遵循PEP8规范
4. 包含错误处理
5. 提供使用示例

测试代码要求：
1. 使用pytest框架
2. 覆盖主要功能
3. 包含边界条件测试
4. 提供性能测试

增量修改模式说明：
- 方式1：新增独立函数/类（推荐）
- 方式2：装饰器模式（AOP风格）
- 方式3：继承扩展

包含测试：{include_tests}
验证级别：{validation_level}""",
            prompt_variables={
                'code_mode': 'incremental',
                'include_tests': True,
                'validation_level': 'basic'
            },
            capabilities=[
                'code_generation',
                'test_generation',
                'incremental_patch',
                'code_validation',
                'integration_guide'
            ],
            behaviors={
                'code_style': 'incremental',  # incremental | full_replace | patch
                'include_tests': True,
                'validation_level': 'basic',  # none | basic | strict
                'save_backup': True,
                'save_merged_example': True,
                'save_integration_guide': True
            }
        )
        self.register(engineer)
        
        # ===== Test Agent 配置（实验性）=====
        test_agent = AgentProfile(
            name="Test",
            description="测试Agent，负责自动执行测试和验证代码",
            system_prompt_template="""你是测试Agent，负责：
1. 执行生成的测试代码
2. 分析测试结果
3. 提供修复建议
4. 评估代码质量

自动修复：{auto_fix}
最大修复迭代：{max_iterations}""",
            prompt_variables={
                'auto_fix': False,
                'max_iterations': 3
            },
            capabilities=[
                'test_execution',
                'result_analysis',
                'auto_fix',
                'quality_assessment'
            ],
            behaviors={
                'auto_fix': False,
                'max_iterations': 3,
                'timeout_seconds': 60
            }
        )
        self.register(test_agent)
    
    def _load_custom_profiles(self):
        """从文件加载自定义 Agent 配置"""
        profile_dirs = [
            Path.cwd() / "agent_profiles",
            Path(__file__).parent.parent / "agent_profiles",
            Path.home() / ".evo" / "profiles",
        ]
        
        for profile_dir in profile_dirs:
            if not profile_dir.exists():
                continue
            
            for file_path in profile_dir.glob("*.yaml"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    
                    profile = AgentProfile.from_dict(data)
                    self.register(profile)
                    print(f"[Profile] 加载自定义配置: {profile.name} from {file_path}")
                except Exception as e:
                    print(f"[Profile] 加载失败 {file_path}: {e}")
    
    def register(self, profile: AgentProfile):
        """注册 Agent 配置"""
        self._profiles[profile.name] = profile
    
    def get(self, name: str) -> Optional[AgentProfile]:
        """获取 Agent 配置"""
        return self._profiles.get(name)
    
    def get_all(self) -> Dict[str, AgentProfile]:
        """获取所有配置"""
        return self._profiles.copy()
    
    def list_capabilities(self) -> List[str]:
        """列出所有可用能力"""
        caps = set()
        for profile in self._profiles.values():
            caps.update(profile.capabilities)
        return sorted(caps)
    
    def find_by_capability(self, capability: str) -> List[AgentProfile]:
        """按能力查找 Agent"""
        return [
            p for p in self._profiles.values()
            if p.has_capability(capability)
        ]
    
    def create_custom_profile(
        self, 
        base_name: str, 
        new_name: str, 
        overrides: Dict[str, Any]
    ) -> AgentProfile:
        """基于现有配置创建自定义配置"""
        base = self.get(base_name)
        if not base:
            raise ValueError(f"基础配置不存在: {base_name}")
        
        # 深拷贝并覆盖
        data = base.to_dict()
        data['name'] = new_name
        
        for key, value in overrides.items():
            if key in data:
                if isinstance(data[key], dict) and isinstance(value, dict):
                    data[key].update(value)
                else:
                    data[key] = value
        
        return AgentProfile.from_dict(data)


# 全局注册表
_registry = AgentProfileRegistry()


def get_profile(name: str) -> Optional[AgentProfile]:
    """获取 Agent 配置 - 快捷函数"""
    return _registry.get(name)


def get_registry() -> AgentProfileRegistry:
    """获取注册表实例"""
    return _registry
