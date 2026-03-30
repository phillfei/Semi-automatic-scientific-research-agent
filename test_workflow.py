#!/usr/bin/env python3
"""
测试工作流执行
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from backend.task_manager import task_manager
from backend.workflow_api import run_agent_workflow


async def test_workflow():
    """测试工作流执行"""
    print("=" * 70)
    print("测试 Agent 工作流")
    print("=" * 70)
    
    # 创建任务
    inputs = {
        "html_content": "<html><body>测试项目规划</body></html>",
        "code_content": "import pandas as pd\n# 测试代码",
        "instruction": "优化数据加载代码"
    }
    
    task = task_manager.create_task("test_project", inputs)
    print(f"\n✅ 任务创建: {task.id}")
    
    # 执行任务
    print("\n🚀 开始执行工作流...\n")
    await run_agent_workflow(task.id, "test_project", inputs)
    
    # 检查结果
    await asyncio.sleep(1)  # 等待完成
    
    task = task_manager.get_task(task.id)
    print(f"\n{'='*70}")
    print(f"任务状态: {task.status.value}")
    print(f"进度: {task.progress}%")
    print(f"结果: {task.results}")
    print(f"{'='*70}")
    
    # 打印日志
    print("\n📋 执行日志:")
    for log in task.logs:
        print(f"  [{log['level']}] {log['message']}")


if __name__ == "__main__":
    asyncio.run(test_workflow())
