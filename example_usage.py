"""
EvoAgentX 代码优化系统 - 使用示例
所有Agent共用相同的API配置
"""

import os
from dotenv import load_dotenv

from agents import create_llm
from workflows.optimization_workflow import create_optimization_workflow


def main():
    """使用示例"""
    load_dotenv()
    
    print("=" * 70)
    print("EvoAgentX 代码优化系统 - 使用示例")
    print("=" * 70)
    
    # 检查配置
    api_key = os.getenv("KIMI_API_KEY")
    
    if not api_key or api_key == "your-kimi-api-key-here":
        print("\n❌ 请先在 .env 文件中配置 KIMI_API_KEY")
        print("\n配置文件格式 (.env):")
        print("KIMI_API_KEY=your-kimi-api-key-here")
        print("KIMI_BASE_URL=https://api.moonshot.cn/v1")
        print("KIMI_MODEL=moonshot-v1-128k")
        return
    
    # 1. 创建LLM（所有Agent共用）
    llm = create_llm(temperature=0.3)
    
    print(f"\n✅ LLM配置完成")
    print(f"   API: {os.getenv('KIMI_BASE_URL')}")
    print(f"   Model: {os.getenv('KIMI_MODEL')}")
    
    # 2. 创建工作流
    print(f"\n{'='*70}")
    print("创建工作流...")
    print(f"{'='*70}")
    
    workflow = create_optimization_workflow(
        project_name="birdclif_optimization",
        llm=llm
    )
    
    print(f"\n✅ 工作流创建完成！")
    print(f"\n下一步:")
    print(f"  1. 运行后端: python backend/app.py")
    print(f"  2. 访问: http://localhost:8000")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()