"""
LLM 客户端适配器。
"""

from __future__ import annotations

from typing import Dict, List

from aiagents_stock.domain.ai.ports import LLMClient
from aiagents_stock.infrastructure.ai.deepseek_client import DeepSeekClient


class DeepSeekLLMAdapter(LLMClient):
    """
    适配 DeepSeekClient 到 LLMClient 接口。
    """
    
    def __init__(self, model: str = "deepseek-chat"):
        self._client = DeepSeekClient(model=model)
    
    def call_chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        调用聊天补全接口。
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数，如 temperature, max_tokens 等
        """
        return self._client.call_api(
            messages=messages,
            model=kwargs.get("model"),
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2000)
        )
