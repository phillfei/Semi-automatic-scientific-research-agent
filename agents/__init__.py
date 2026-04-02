# -*- coding: utf-8 -*-
"""
Agents 模块 - 所有Agent共用相同的API配置
使用新版 OpenAI SDK (v1.0+) 适配 EvoAgentX 接口
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel, ConfigDict

# 导入 EvoAgentX 的基类
from evoagentx.models.base_model import BaseLLM


class CustomOpenAILLMConfig(BaseModel):
    """自定义配置类，不依赖 EvoAgentX 的 LLMConfig，避免 Pydantic 冲突"""
    model: str
    api_base: str
    openai_key: str
    temperature: float = 0.3
    max_tokens: int = 8000
    stream: bool = True
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class CustomOpenAILLM(BaseLLM):
    """
    适配新版 OpenAI SDK (v1.0+) 的 LLM 类
    继承自 EvoAgentX BaseLLM，完全兼容 Pydantic 验证
    类名加 Custom 前缀避免与 EvoAgentX 内置 OpenAILLM 冲突
    """
    
    def init_model(self):
        """初始化 OpenAI 客户端（新版 SDK）"""
        self._client = OpenAI(
            api_key=self.config.openai_key,
            base_url=self.config.api_base,  # 新版 SDK 使用 base_url
        )
    
    def formulate_messages(self, prompts: List[str], system_messages: Optional[List[str]] = None) -> List[List[dict]]:
        """将 prompts 转换为消息格式"""
        results = []
        for i, prompt in enumerate(prompts):
            messages = []
            if system_messages and i < len(system_messages):
                messages.append({"role": "system", "content": system_messages[i]})
            messages.append({"role": "user", "content": prompt})
            results.append(messages)
        return results
    
    def single_generate(self, messages: List[dict], **kwargs) -> str:
        """单条生成（EvoAgentX 核心接口）"""
        try:
            # Moonshot 部分模型（如 reasoning 模型）强制 temperature=1
            # 为兼容性，统一使用 temperature=1
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=1,  # 强制设为 1，避免模型不支持其他 temperature
                max_tokens=kwargs.get('max_tokens', getattr(self.config, 'max_tokens', 8000)),
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"LLM API 调用失败: {str(e)}")
    
    def batch_generate(self, batch_messages: List[List[dict]], **kwargs) -> List[str]:
        """批量生成"""
        results = []
        for messages in batch_messages:
            result = self.single_generate(messages, **kwargs)
            results.append(result)
        return results
    
    async def single_generate_async(self, messages: List[dict], **kwargs) -> str:
        """异步单条生成"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.single_generate, messages, **kwargs)
    
    def generate(self, prompt: str, **kwargs) -> str:
        """EvoAgentX Agent 使用的便捷接口"""
        messages = [{"role": "user", "content": prompt}]
        return self.single_generate(messages, **kwargs)
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天接口"""
        return self.single_generate(messages, **kwargs)
    
    def __call__(self, prompt: str, **kwargs) -> str:
        """使 LLM 可调用"""
        return self.generate(prompt, **kwargs)


def create_llm(temperature=0.3, max_tokens=8000):
    """创建LLM实例 - 所有Agent使用相同的API配置"""
    api_key = os.getenv("KIMI_API_KEY")
    base_url = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    model = os.getenv("KIMI_MODEL", "kimi-k2.5")
    
    # Moonshot API 直接使用原始模型名，不加前缀
    # 验证模型名是否合法（从查到的列表中）
    valid_models = [
        "kimi-k2.5", "kimi-k2", "kimi-k2-turbo-preview", "kimi-k2-0711-preview",
        "kimi-k2-thinking", "kimi-k2-thinking-turbo", "kimi-k2-0905-preview",
        "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "moonshot-v1-auto",
        "moonshot-v1-8k-vision-preview", "moonshot-v1-32k-vision-preview", "moonshot-v1-128k-vision-preview"
    ]
    
    # 如果用户配置的模型不在列表中，给出警告并使用默认模型
    if model not in valid_models:
        print(f"⚠️ 警告: 模型 '{model}' 可能不正确，使用默认模型 kimi-k2.5")
        model = "kimi-k2.5"
    
    # 推理模型（thinking）强制 temperature=1，为避免兼容性问题，自动切换到非推理模型
    thinking_models = ["kimi-k2-thinking", "kimi-k2-thinking-turbo"]
    if model in thinking_models:
        print(f"⚠️ 推理模型 '{model}' 限制较多，自动切换到 kimi-k2.5")
        model = "kimi-k2.5"
    
    if not api_key or api_key == "your-kimi-api-key-here":
        raise ValueError("请在 .env 文件中配置 KIMI_API_KEY")
    
    config = CustomOpenAILLMConfig(
        model=model,
        api_base=base_url,
        openai_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True
    )
    
    # 使用新版 SDK 兼容的 LLM 类（继承自 BaseLLM）
    return CustomOpenAILLM(config=config)


# 导入新版 V2 Agent类
from agents.v2.supervisor_agent_v2 import SupervisorAgentV2
from agents.v2.engineer_agent_v2 import EngineerAgentV2
from agents.v2.constraint_agent import ConstraintAgent
from agents.v2.baseline_analyzer import BaselineAnalyzer
from agents.v2.direction_selector import DirectionSelectorAgent
from agents.search_agent import SearchAgent

__all__ = [
    'SupervisorAgentV2', 
    'EngineerAgentV2', 
    'ConstraintAgent', 
    'BaselineAnalyzer',
    'DirectionSelectorAgent',
    'SearchAgent',
    'create_llm'
]
