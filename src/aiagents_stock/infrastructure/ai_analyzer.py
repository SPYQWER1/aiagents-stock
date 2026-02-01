"""
AI 分析器基础设施实现。

该模块直接实现领域端口 AIAnalyzer，使用 DeepSeekAnalyzer 执行分析。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiagents_stock.domain.analysis.dto import AnalysisResult, StockDataBundle, StockRequest
from aiagents_stock.domain.analysis.ports import AIAnalyzer
from aiagents_stock.infrastructure.ai.deepseek_agents import DeepSeekAnalyzer


@dataclass(frozen=True)
class DeepSeekAIAnalyzer(AIAnalyzer):
    """
    基于 DeepSeek 的 AIAnalyzer 实现。
    """

    def analyze(
        self,
        *,
        request: StockRequest,
        bundle: StockDataBundle,
    ) -> AnalysisResult:
        """
        调用 DeepSeekAnalyzer 执行分析。
        """

        symbol = request.symbol
        stock_info = bundle.stock_info
        
        # 实例化 DeepSeekAnalyzer
        # 注意：这里直接使用 request 中的 model
        agents = DeepSeekAnalyzer(model=request.model)
        
        # 1. 运行多智能体分析
        agents_results = agents.run_multi_agent_analysis(
            stock_info=stock_info,
            bundle=bundle,
            enabled_analysts=request.enabled_analysts,
        )

        # 2. 组织团队讨论
        discussion_result = agents.conduct_team_discussion(
            agents_results=agents_results,
            stock_info=stock_info,
        )

        # 3. 生成最终决策
        final_decision = agents.make_final_decision(
            discussion_result=discussion_result,
            stock_info=stock_info,
            bundle=bundle,
        )

        return AnalysisResult(
            agents_results=agents_results,
            discussion_result=discussion_result,
            final_decision=final_decision,
        )
