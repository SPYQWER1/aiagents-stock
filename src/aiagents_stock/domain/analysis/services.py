"""
领域服务定义。

本模块定义了领域层的服务接口和纯领域逻辑服务。
"""

from __future__ import annotations

from typing import Protocol, Any, Dict, List
from aiagents_stock.domain.analysis.model import StockAnalysis, AgentRole

class AnalysisOrchestrator(Protocol):
    """
    分析编排器接口。
    
    负责协调各个 Agent 进行工作，但不包含具体的 LLM 调用细节。
    它定义了分析的步骤和策略。
    """
    def perform_analysis(
        self, 
        analysis: StockAnalysis, 
        data_bundle: Any,
        enabled_agents: List[AgentRole]
    ) -> StockAnalysis:
        """执行全流程分析"""
        ...

class AgentInteractionPolicy(Protocol):
    """
    Agent 交互策略接口。
    
    定义 Agent 之间如何交互，例如是否需要辩论，谁先发言等。
    """
    def should_debate(self, analysis: StockAnalysis) -> bool:
        ...
    
    def get_discussion_prompt(self, analysis: StockAnalysis) -> str:
        ...
