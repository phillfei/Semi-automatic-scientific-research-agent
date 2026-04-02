"""
配置管理器 - 统一管理所有配置项
支持配置继承、验证和热重载
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, TypeVar, Generic, Callable
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum


T = TypeVar('T')


class ConfigValue(Generic[T]):
    """带类型和验证的配置值"""
    
    def __init__(
        self, 
        default: T, 
        validator: Optional[Callable[[T], bool]] = None,
        description: str = "",
        env_var: Optional[str] = None
    ):
        self.default = default
        self.value = default
        self.validator = validator
        self.description = description
        self.env_var = env_var
    
    def set(self, value: T) -> bool:
        """设置值，返回是否成功"""
        if self.validator and not self.validator(value):
            return False
        self.value = value
        return True
    
    def get(self) -> T:
        """获取当前值"""
        # 优先从环境变量读取
        if self.env_var:
            env_value = os.getenv(self.env_var)
            if env_value is not None:
                # 尝试类型转换
                try:
                    if isinstance(self.default, bool):
                        return env_value.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(self.default, int):
                        return int(env_value)
                    elif isinstance(self.default, float):
                        return float(env_value)
                    else:
                        return env_value
                except:
                    pass
        return self.value


@dataclass
class AgentConfig:
    """Agent 配置 - 可配置的 Agent 行为"""
    
    # Supervisor 配置
    supervisor_max_directions: int = 3
    supervisor_eda_sample_size: int = 5
    supervisor_history_limit: int = 5
    supervisor_system_prompt: str = ""  # 空字符串使用默认
    
    # Search 配置
    search_max_workers: int = 3
    search_time_limit_minutes: int = 5
    search_papers_per_query: int = 3
    search_max_iterations: int = 2
    search_arxiv_delay_seconds: float = 3.0
    
    # Engineer 配置
    engineer_code_style: str = "incremental"  # incremental | full_replace | patch
    engineer_include_tests: bool = True
    engineer_validation_level: str = "basic"  # none | basic | strict
    
    # LLM 配置
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4000
    llm_model: str = "default"


@dataclass
class WorkflowConfig:
    """工作流配置 - 动态工作流控制"""
    
    # 节点启用控制
    enable_research: bool = True
    enable_search: bool = True
    enable_implement: bool = True
    enable_test: bool = False
    
    # 流程控制
    require_hitl_after_research: bool = False
    require_hitl_after_search: bool = False
    auto_retry_on_failure: bool = True
    max_retry_count: int = 2
    
    # 并行控制
    parallel_search: bool = True
    parallel_implement: bool = False


@dataclass
class OutputConfig:
    """输出配置"""
    
    output_dir: str = "./output"
    save_backup: bool = True
    save_merged_example: bool = True
    save_integration_guide: bool = True
    save_search_reports: bool = True
    
    # 日志配置
    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: str = "./logs"


class ConfigManager:
    """
    配置管理器 - 统一管理所有配置
    支持配置文件、环境变量和运行时修改
    """
    
    _instance: Optional['ConfigManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.agent = AgentConfig()
        self.workflow = WorkflowConfig()
        self.output = OutputConfig()
        
        self._custom: Dict[str, Any] = {}
        self._listeners: Dict[str, list] = {}
        
        self._load_config()
        self._initialized = True
    
    def _load_config(self):
        """加载配置文件"""
        config_paths = [
            Path.cwd() / "evo_config.yaml",
            Path.cwd() / "evo_config.json",
            Path.home() / ".evo" / "config.yaml",
            Path(__file__).parent.parent / "evo_config.yaml",
        ]
        
        for path in config_paths:
            if path.exists():
                self._load_from_file(path)
                print(f"[Config] 加载配置: {path}")
                break
    
    def _load_from_file(self, path: Path):
        """从文件加载配置"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix == '.yaml' or path.suffix == '.yml':
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            if not data:
                return
            
            # 更新 Agent 配置
            if 'agent' in data:
                agent_data = data['agent']
                for key, value in agent_data.items():
                    if hasattr(self.agent, key):
                        setattr(self.agent, key, value)
            
            # 更新工作流配置
            if 'workflow' in data:
                wf_data = data['workflow']
                for key, value in wf_data.items():
                    if hasattr(self.workflow, key):
                        setattr(self.workflow, key, value)
            
            # 更新输出配置
            if 'output' in data:
                out_data = data['output']
                for key, value in out_data.items():
                    if hasattr(self.output, key):
                        setattr(self.output, key, value)
            
            # 保存自定义配置
            if 'custom' in data:
                self._custom.update(data['custom'])
                
        except Exception as e:
            print(f"[Config] 加载配置失败: {e}")
    
    def get(self, key: str, default: T = None) -> T:
        """通过键获取配置值，支持嵌套键 (如 'agent.llm_temperature')"""
        parts = key.split('.')
        
        # 检查标准配置
        if len(parts) == 2:
            section, name = parts
            if section == 'agent' and hasattr(self.agent, name):
                return getattr(self.agent, name)
            elif section == 'workflow' and hasattr(self.workflow, name):
                return getattr(self.workflow, name)
            elif section == 'output' and hasattr(self.output, name):
                return getattr(self.output, name)
        
        # 检查自定义配置
        return self._custom.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置值"""
        parts = key.split('.')
        
        if len(parts) == 2:
            section, name = parts
            if section == 'agent' and hasattr(self.agent, name):
                old_value = getattr(self.agent, name)
                setattr(self.agent, name, value)
                self._notify_change(key, old_value, value)
                return True
            elif section == 'workflow' and hasattr(self.workflow, name):
                old_value = getattr(self.workflow, name)
                setattr(self.workflow, name, value)
                self._notify_change(key, old_value, value)
                return True
            elif section == 'output' and hasattr(self.output, name):
                old_value = getattr(self.output, name)
                setattr(self.output, name, value)
                self._notify_change(key, old_value, value)
                return True
        
        # 自定义配置
        old_value = self._custom.get(key)
        self._custom[key] = value
        self._notify_change(key, old_value, value)
        return True
    
    def on_change(self, key: str, callback: Callable[[Any, Any], None]):
        """注册配置变更监听器"""
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)
    
    def _notify_change(self, key: str, old_value: Any, new_value: Any):
        """通知配置变更"""
        for callback in self._listeners.get(key, []):
            try:
                callback(old_value, new_value)
            except Exception as e:
                print(f"[Config] 监听器错误: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            'agent': asdict(self.agent),
            'workflow': asdict(self.workflow),
            'output': asdict(self.output),
            'custom': self._custom
        }
    
    def save(self, path: Optional[str] = None):
        """保存配置到文件"""
        if path is None:
            path = "evo_config.yaml"
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, sort_keys=False)
    
    def get_agent_config(self) -> AgentConfig:
        """获取 Agent 配置"""
        return self.agent
    
    def get_workflow_config(self) -> WorkflowConfig:
        """获取工作流配置"""
        return self.workflow
    
    def get_output_config(self) -> OutputConfig:
        """获取输出配置"""
        return self.output


# 全局配置实例
_config_manager = ConfigManager()


def get_config(key: str = None, default: T = None) -> T:
    """
    获取配置值 - 全局快捷函数
    
    用法:
        get_config() -> 返回 ConfigManager 实例
        get_config('agent.llm_temperature') -> 返回具体值
    """
    if key is None:
        return _config_manager
    return _config_manager.get(key, default)


def set_config(key: str, value: Any) -> bool:
    """设置配置值 - 全局快捷函数"""
    return _config_manager.set(key, value)
