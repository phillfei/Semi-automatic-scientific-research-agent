#!/usr/bin/env python3
"""EvoAgentX 代码优化系统 - 主入口"""

import os
from dotenv import load_dotenv
from agents import create_llm
from workflows.optimization_workflow import create_workflow

load_dotenv()

def main():
    """主函数"""
    print("=" * 70)
    print("EvoAgentX 代码优化系统")
    print("=" * 70)
    
    # 创建 LLM（自动处理 Moonshot 模型名称转换）
    llm = create_llm(temperature=0.3)
    
    # 创建工作流
    project_name = input("项目名称: ").strip() or "test_project"
    workflow = create_workflow(project_name, llm)
    
    print(f"\n✅ 工作流已创建: {project_name}")
    print("运行: python backend/app.py 启动 Web 服务")
    
    return 0

if __name__ == "__main__":
    exit(main())