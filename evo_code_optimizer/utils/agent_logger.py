"""
Agent 调用日志记录器
记录每个 Agent 的调用过程、输入、输出和执行时间
"""

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from functools import wraps
import time


class AgentLogger:
    """Agent 调用日志记录器"""
    
    def __init__(self, log_dir: str = None):
        # 使用相对于项目根目录的路径
        if log_dir is None:
            # 获取本文件所在目录的父目录（即 evo_code_optimizer 目录）
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            log_dir = project_root / "logs" / "agents"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建按日期的日志文件
        self.current_date = datetime.now().strftime('%Y%m%d')
        self.log_file = self.log_dir / f"agent_calls_{self.current_date}.log"
        
        # 配置日志记录器
        self.logger = logging.getLogger("AgentLogger")
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加 handler
        if not self.logger.handlers:
            # 文件 handler - 详细日志
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # 控制台 handler - 简要信息
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        self._log_system_info()
    
    def _log_system_info(self):
        """记录系统启动信息"""
        self.logger.info("=" * 70)
        self.logger.info("Agent Logger 启动")
        self.logger.info(f"日志文件: {self.log_file}")
        self.logger.info("=" * 70)
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    def _format_data(self, data: Any, max_length: int = 500) -> str:
        """格式化数据用于日志记录"""
        try:
            if isinstance(data, str):
                result = data
            elif isinstance(data, (dict, list)):
                result = json.dumps(data, ensure_ascii=False, indent=2)
            else:
                result = str(data)
            
            # 截断过长的内容
            if len(result) > max_length:
                result = result[:max_length] + f"\n... [截断，总长度: {len(result)}]"
            return result
        except Exception as e:
            return f"<无法序列化: {e}>"
    
    def log_agent_call(self, agent_name: str, method_name: str, 
                       inputs: Dict[str, Any], call_id: Optional[str] = None):
        """
        记录 Agent 方法调用开始
        
        Args:
            agent_name: Agent 名称
            method_name: 方法名
            inputs: 输入参数
            call_id: 调用 ID（用于关联开始和结束）
        """
        call_id = call_id or f"{agent_name}_{method_name}_{int(time.time() * 1000)}"
        
        self.logger.info(f"[AGENT CALL] {agent_name}.{method_name} | CallID: {call_id}")
        self.logger.debug(f"[INPUTS] {self._format_data(inputs)}")
        
        return call_id
    
    def log_agent_return(self, agent_name: str, method_name: str,
                         outputs: Any, duration_ms: float, 
                         call_id: Optional[str] = None):
        """
        记录 Agent 方法调用结束
        
        Args:
            agent_name: Agent 名称
            method_name: 方法名
            outputs: 返回值
            duration_ms: 执行时间（毫秒）
            call_id: 调用 ID
        """
        call_id_str = f" | CallID: {call_id}" if call_id else ""
        self.logger.info(f"[AGENT RETURN] {agent_name}.{method_name} | 耗时: {duration_ms:.2f}ms{call_id_str}")
        self.logger.debug(f"[OUTPUTS] {self._format_data(outputs)}")
    
    def log_agent_error(self, agent_name: str, method_name: str,
                        error: Exception, call_id: Optional[str] = None):
        """
        记录 Agent 调用错误
        
        Args:
            agent_name: Agent 名称
            method_name: 方法名
            error: 异常对象
            call_id: 调用 ID
        """
        call_id_str = f" | CallID: {call_id}" if call_id else ""
        self.logger.error(f"[AGENT ERROR] {agent_name}.{method_name}{call_id_str}")
        self.logger.error(f"  错误类型: {type(error).__name__}")
        self.logger.error(f"  错误信息: {str(error)}")
    
    def log_step(self, agent_name: str, step_name: str, message: str, 
                 data: Optional[Dict] = None):
        """
        记录 Agent 执行步骤
        
        Args:
            agent_name: Agent 名称
            step_name: 步骤名称
            message: 消息
            data: 附加数据
        """
        self.logger.info(f"[STEP] {agent_name}.{step_name} | {message}")
        if data:
            self.logger.debug(f"[STEP DATA] {self._format_data(data)}")
    
    def log_llm_call(self, agent_name: str, prompt_length: int, 
                     response_length: int, duration_ms: float):
        """
        记录 LLM 调用
        
        Args:
            agent_name: Agent 名称
            prompt_length: 提示词长度
            response_length: 响应长度
            duration_ms: 耗时（毫秒）
        """
        self.logger.info(
            f"[LLM CALL] {agent_name} | "
            f"Prompt: {prompt_length} chars | "
            f"Response: {response_length} chars | "
            f"耗时: {duration_ms:.2f}ms"
        )
    
    def log_search_result(self, agent_name: str, query: str, 
                          result_count: int, duration_ms: float):
        """
        记录搜索结果
        
        Args:
            agent_name: Agent 名称
            query: 搜索查询
            result_count: 结果数量
            duration_ms: 耗时（毫秒）
        """
        self.logger.info(
            f"[SEARCH] {agent_name} | "
            f"Query: {query[:50]}... | "
            f"Results: {result_count} | "
            f"耗时: {duration_ms:.2f}ms"
        )


# 全局日志记录器实例
_agent_logger_instance: Optional[AgentLogger] = None


def get_agent_logger(log_dir: str = "logs/agents") -> AgentLogger:
    """获取全局 AgentLogger 实例"""
    global _agent_logger_instance
    if _agent_logger_instance is None:
        _agent_logger_instance = AgentLogger(log_dir)
    return _agent_logger_instance


def log_agent_method(agent_name_attr: str = "name"):
    """
    装饰器：自动记录 Agent 方法的调用
    
    Args:
        agent_name_attr: Agent 名称属性的名称
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            agent_name = getattr(self, agent_name_attr, self.__class__.__name__)
            method_name = func.__name__
            
            logger = get_agent_logger()
            
            # 构建输入参数字典
            inputs = {}
            if args:
                inputs['args'] = [str(arg)[:100] for arg in args]
            if kwargs:
                inputs['kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}
            
            # 记录调用开始
            call_id = logger.log_agent_call(agent_name, method_name, inputs)
            
            # 执行方法
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # 记录调用结束
                logger.log_agent_return(
                    agent_name, method_name, 
                    {"type": type(result).__name__, "summary": str(result)[:200]},
                    duration_ms, call_id
                )
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.log_agent_error(agent_name, method_name, e, call_id)
                raise
        
        return wrapper
    return decorator
