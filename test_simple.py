#!/usr/bin/env python3
"""简单测试日志功能"""
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.agent_logger import get_agent_logger

logger = get_agent_logger()

# 写入测试日志
logger.log_agent_call('TestAgent', 'test_method', {'param': 'value'})
logger.log_step('TestAgent', 'step1', '测试步骤')
logger.log_llm_call('TestAgent', 100, 200, 500)

print(f'日志文件: {logger.log_file}')
print(f'日志目录: {logger.log_dir}')
print('测试完成！')
