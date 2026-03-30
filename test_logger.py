"""
测试 Agent 日志记录功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.agent_logger import get_agent_logger


def test_logger():
    """测试日志记录器"""
    print("=" * 70)
    print("测试 Agent 日志记录功能")
    print("=" * 70)
    
    # 获取日志记录器
    logger = get_agent_logger()
    
    # 模拟 Agent 调用
    print("\n1. 模拟 SupervisorAgent 调用...")
    call_id = logger.log_agent_call(
        agent_name="Supervisor",
        method_name="initialize_project",
        inputs={
            "project_name": "birdclef-2026",
            "html_content": "<html>...</html>",
            "code_content": "import pandas..."
        }
    )
    
    import time
    time.sleep(0.5)
    
    logger.log_agent_return(
        agent_name="Supervisor",
        method_name="initialize_project",
        outputs={
            "directions": ["数据增强", "模型优化", "训练策略"],
            "summary": "项目分析完成"
        },
        duration_ms=520,
        call_id=call_id
    )
    
    # 模拟步骤日志
    print("\n2. 模拟步骤日志...")
    logger.log_step("Supervisor", "_parse_analysis", "找到 3 个优化方向")
    
    # 模拟 LLM 调用日志
    print("\n3. 模拟 LLM 调用日志...")
    logger.log_llm_call(
        agent_name="Engineer",
        prompt_length=1500,
        response_length=3200,
        duration_ms=2500
    )
    
    # 模拟搜索日志
    print("\n4. 模拟搜索日志...")
    logger.log_search_result(
        agent_name="Search",
        query="data augmentation audio spectrogram",
        result_count=5,
        duration_ms=3200
    )
    
    # 模拟错误日志
    print("\n5. 模拟错误日志...")
    try:
        raise ValueError("测试错误")
    except Exception as e:
        logger.log_agent_error(
            agent_name="Engineer",
            method_name="_generate_code",
            error=e,
            call_id="test_call_123"
        )
    
    print("\n" + "=" * 70)
    print("日志测试完成！")
    print(f"日志文件位置: {logger.log_file}")
    print("=" * 70)


if __name__ == "__main__":
    test_logger()
