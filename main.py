# -*- coding: utf-8 -*-
"""EvoAgentX 代码优化系统 - 主入口"""

import os
from dotenv import load_dotenv
from agents import create_llm
from core.enhanced_workflow import run_enhanced_workflow

load_dotenv()


def main():
    """主函数"""
    print("=" * 70)
    print("EvoAgentX 代码优化系统 (增强版)")
    print("=" * 70)
    
    # 创建 LLM（自动处理 Moonshot 模型名称转换）
    llm = create_llm(temperature=0.3)
    
    # 获取项目信息
    project_name = input("项目名称: ").strip() or "test_project"
    baseline_code = input("Baseline 代码路径 (可选): ").strip()
    data_path = input("数据样本路径 (可选): ").strip()
    instruction = input("优化指令 (可选): ").strip()
    
    print(f"\n✅ 配置完成: {project_name}")
    print("🚀 启动增强版工作流...")
    print("-" * 70)
    
    # 运行增强版工作流
    try:
        results = run_enhanced_workflow(
            llm=llm,
            project_name=project_name,
            baseline_code_path=baseline_code if baseline_code else None,
            data_path=data_path if data_path else None,
            instruction=instruction if instruction else None
        )
        
        print("\n" + "=" * 70)
        print("✅ 工作流执行完成!")
        print(f"📁 输出目录: {results.get('output_dir', 'N/A')}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 工作流执行失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
