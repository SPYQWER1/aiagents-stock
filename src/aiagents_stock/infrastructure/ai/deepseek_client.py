from typing import Dict, List, Optional

import openai

from aiagents_stock.core.config_manager import config_manager


class DeepSeekClient:
    """DeepSeek API客户端"""

    def __init__(self, model="deepseek-chat"):
        self.model = model
        config = config_manager.read_env()
        self.client = openai.OpenAI(
            api_key=config.get("DEEPSEEK_API_KEY", ""),
            base_url=config.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )

    def call_chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """实现 LLMClient 接口"""
        return self.call_api(messages, model, temperature, max_tokens)

    def call_api(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """调用DeepSeek API"""
        # 使用实例的模型，如果没有传入则使用默认模型
        model_to_use = model or self.model

        # 对于 reasoner 模型，自动增加 max_tokens
        if "reasoner" in model_to_use.lower() and max_tokens <= 2000:
            max_tokens = 8000  # reasoner 模型需要更多 tokens 来输出推理过程

        try:
            response = self.client.chat.completions.create(
                model=model_to_use, messages=messages, temperature=temperature, max_tokens=max_tokens
            )

            # 处理 reasoner 模型的响应
            message = response.choices[0].message

            # reasoner 模型可能包含 reasoning_content（推理过程）和 content（最终答案）
            # 我们返回完整内容，包括推理过程（如果有的话）
            result = ""

            # 检查是否有推理内容
            if hasattr(message, "reasoning_content") and message.reasoning_content:
                result += f"【推理过程】\n{message.reasoning_content}\n\n"

            # 添加最终内容
            if message.content:
                result += message.content

            return result if result else "API返回空响应"

        except Exception as e:
            return f"API调用失败: {str(e)}"

