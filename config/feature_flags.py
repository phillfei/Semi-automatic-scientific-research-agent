"""
特性开关系统 - 参考 src 的 feature flags 实现
提供运行时特性控制和 A/B 测试支持
"""

import os
import json
from typing import Dict, Set, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path


class Feature(str, Enum):
    """特性标志定义 - 类似 src 的 feature flags"""
    
    # 核心特性
    ITERATIVE_SEARCH = "iterative_search"           # 迭代搜索
    KNOWLEDGE_BASE = "knowledge_base"               # 知识库复用
    INCREMENTAL_CODE = "incremental_code"           # 增量代码生成
    CODE_EXTRACTION = "code_extraction"             # 代码提取 Action
    
    # Agent 特性
    SUPERVISOR_EDA = "supervisor_eda"               # Supervisor EDA 分析
    SUPERVISOR_HISTORY = "supervisor_history"       # 历史反馈分析
    SEARCH_KEYWORD_REFINE = "search_keyword_refine" # 关键词动态调整
    ENGINEER_PATCH_MODE = "engineer_patch_mode"     # Engineer Patch 模式
    
    # 工作流特性
    PARALLEL_SEARCH = "parallel_search"             # 并行搜索
    DYNAMIC_WORKFLOW = "dynamic_workflow"           # 动态工作流
    HITL_APPROVAL = "hitl_approval"                 # 人工审批
    
    # 实验特性
    ADVANCED_EDA = "advanced_eda"                   # 高级 EDA（音频/图像专用）
    MULTI_AGENT_VOTE = "multi_agent_vote"           # 多 Agent 投票
    AUTO_TEST = "auto_test"                         # 自动测试执行
    
    # 调试特性
    DEBUG_PROMPTS = "debug_prompts"                 # 打印完整提示词
    DEBUG_LLM_CALLS = "debug_llm_calls"             # 记录 LLM 调用
    SAVE_INTERMEDIATE = "save_intermediate"         # 保存中间结果


@dataclass
class FeatureGate:
    """特性门控配置 - 控制特性是否可用"""
    name: str
    enabled: bool = False
    requires_env: Optional[str] = None          # 需要的环境变量
    requires_flag: Optional[str] = None         # 需要的特性标志
    rollout_percentage: float = 100.0            # 灰度百分比
    description: str = ""
    
    def is_available(self) -> bool:
        """检查特性是否可用"""
        # 检查环境变量要求
        if self.requires_env:
            if not os.getenv(self.requires_env):
                return False
        
        # 检查依赖特性
        if self.requires_flag:
            if not feature_enabled(self.requires_flag):
                return False
        
        return True


class FeatureFlags:
    """
    特性开关管理器 - 参考 src 的 feature() 实现
    支持环境变量、配置文件和运行时控制
    """
    
    _instance: Optional['FeatureFlags'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._gates: Dict[str, FeatureGate] = {}
        self._overrides: Set[str] = set()           # 运行时覆盖
        self._listeners: Dict[str, list] = {}       # 变更监听器
        
        self._init_default_gates()
        self._load_from_env()
        self._load_from_file()
        
        self._initialized = True
    
    def _init_default_gates(self):
        """初始化默认特性门控"""
        defaults = [
            # 核心特性 - 默认开启
            FeatureGate(Feature.ITERATIVE_SEARCH, True, description="启用迭代搜索优化关键词"),
            FeatureGate(Feature.KNOWLEDGE_BASE, True, description="启用知识库复用搜索结果"),
            FeatureGate(Feature.INCREMENTAL_CODE, True, description="使用增量代码生成模式"),
            
            # Agent 特性 - 默认开启
            FeatureGate(Feature.SUPERVISOR_EDA, True, description="Supervisor 执行 EDA 分析"),
            FeatureGate(Feature.SUPERVISOR_HISTORY, True, description="Supervisor 分析历史反馈"),
            FeatureGate(Feature.SEARCH_KEYWORD_REFINE, True, description="Search Agent 动态调整关键词"),
            FeatureGate(Feature.ENGINEER_PATCH_MODE, True, description="Engineer 生成 Patch 代码而非全量替换"),
            
            # 工作流特性
            FeatureGate(Feature.PARALLEL_SEARCH, True, description="并行搜索多个方向"),
            FeatureGate(Feature.DYNAMIC_WORKFLOW, False, description="根据输入动态构建工作流"),
            FeatureGate(Feature.HITL_APPROVAL, False, description="关键步骤人工审批"),
            
            # 实验特性 - 默认关闭
            FeatureGate(Feature.ADVANCED_EDA, False, description="高级 EDA（音频波形分析等）"),
            FeatureGate(Feature.MULTI_AGENT_VOTE, False, description="多 Agent 投票决策"),
            FeatureGate(Feature.AUTO_TEST, False, description="自动生成并执行测试"),
            
            # 调试特性
            FeatureGate(Feature.DEBUG_PROMPTS, False, description="打印完整提示词到日志"),
            FeatureGate(Feature.DEBUG_LLM_CALLS, True, description="记录 LLM 调用统计"),
            FeatureGate(Feature.SAVE_INTERMEDIATE, False, description="保存中间结果到文件"),
        ]
        
        for gate in defaults:
            self._gates[gate.name] = gate
    
    def _load_from_env(self):
        """从环境变量加载特性配置 - 格式: EVO_FEATURE_XXX=true"""
        prefix = "EVO_FEATURE_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                feature_name = key[len(prefix):].lower()
                if feature_name in self._gates:
                    enabled = value.lower() in ('true', '1', 'yes', 'on')
                    self._gates[feature_name].enabled = enabled
                    print(f"[Feature] 从环境变量设置: {feature_name} = {enabled}")
    
    def _load_from_file(self, config_path: Optional[str] = None):
        """从配置文件加载特性配置"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'evo_config.json'
            )
        
        path = Path(config_path)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                features = config.get('features', {})
                for name, enabled in features.items():
                    if name in self._gates:
                        self._gates[name].enabled = bool(enabled)
                        print(f"[Feature] 从配置文件设置: {name} = {enabled}")
            except Exception as e:
                print(f"[Feature] 加载配置文件失败: {e}")
    
    def is_enabled(self, feature: str) -> bool:
        """
        检查特性是否启用 - 类似 src 的 feature() 函数
        
        优先级: 运行时覆盖 > 环境变量 > 配置文件 > 默认值
        """
        gate = self._gates.get(feature)
        if not gate:
            return False
        
        # 检查是否被运行时覆盖
        if feature in self._overrides:
            return gate.enabled
        
        # 检查门控条件
        if not gate.is_available():
            return False
        
        return gate.enabled
    
    def enable(self, feature: str):
        """启用特性"""
        if feature in self._gates:
            self._gates[feature].enabled = True
            self._overrides.add(feature)
            self._notify_change(feature, True)
    
    def disable(self, feature: str):
        """禁用特性"""
        if feature in self._gates:
            self._gates[feature].enabled = False
            self._overrides.add(feature)
            self._notify_change(feature, False)
    
    def reset(self, feature: str):
        """重置特性到默认值"""
        self._overrides.discard(feature)
        self._notify_change(feature, self._gates[feature].enabled)
    
    def get_all_features(self) -> Dict[str, dict]:
        """获取所有特性状态"""
        return {
            name: {
                'enabled': gate.enabled,
                'available': gate.is_available(),
                'description': gate.description,
                'overridden': name in self._overrides
            }
            for name, gate in self._gates.items()
        }
    
    def on_change(self, feature: str, callback: Callable[[bool], None]):
        """注册特性变更监听器"""
        if feature not in self._listeners:
            self._listeners[feature] = []
        self._listeners[feature].append(callback)
    
    def _notify_change(self, feature: str, enabled: bool):
        """通知特性变更"""
        for callback in self._listeners.get(feature, []):
            try:
                callback(enabled)
            except Exception as e:
                print(f"[Feature] 监听器错误: {e}")
    
    def save_to_file(self, config_path: Optional[str] = None):
        """保存当前配置到文件"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'evo_config.json'
            )
        
        config = {
            'features': {
                name: gate.enabled 
                for name, gate in self._gates.items()
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)


# 全局特性标志实例
_feature_flags = FeatureFlags()


def feature_enabled(feature: str) -> bool:
    """检查特性是否启用 - 全局快捷函数"""
    return _feature_flags.is_enabled(feature)


def enable_feature(feature: str):
    """启用特性 - 全局快捷函数"""
    _feature_flags.enable(feature)


def disable_feature(feature: str):
    """禁用特性 - 全局快捷函数"""
    _feature_flags.disable(feature)


def get_feature_flags() -> FeatureFlags:
    """获取特性标志管理器实例"""
    return _feature_flags
