"""
AI Domain Ports.
"""
from typing import Dict, List, Optional, Protocol


class LLMClient(Protocol):
    """
    Generic LLM Client Interface.
    Provides basic chat completion capabilities.
    """
    
    def call_chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Execute chat completion.
        
        Args:
            messages: List of message dicts (role, content)
            model: Optional model override
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional provider-specific args
            
        Returns:
            Generated text content
        """
        ...
