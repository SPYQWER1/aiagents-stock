"""
AI 分析器基础设施实现。

该模块直接实现领域端口 AIAnalyzer，使用 DeepSeekAnalyzer 执行分析。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from aiagents_stock.domain.analysis.dto import AnalysisResult, StockDataBundle, StockRequest
from aiagents_stock.domain.analysis.model import AgentRole, StockAnalysis, StockInfo
from aiagents_stock.domain.analysis.ports import AIAnalyzer
from aiagents_stock.infrastructure.ai.llm_client import DeepSeekLLMAdapter
from aiagents_stock.infrastructure.ai.orchestrator import DeepSeekAnalysisOrchestrator


@dataclass(frozen=True)
class DeepSeekAIAnalyzer(AIAnalyzer):
    """
    基于 DeepSeek 的 AIAnalyzer 实现。
    使用 DDD 架构：Adapter -> Orchestrator (Domain Service) -> LLMClient (Port)
    """

    def analyze(
        self,
        *,
        request: StockRequest,
        bundle: StockDataBundle,
    ) -> AnalysisResult:
        """
        调用 DeepSeekAnalysisOrchestrator 执行分析。
        """

        # 1. 转换请求为领域对象
        stock_info = StockInfo.from_dict(bundle.stock_info)
        analysis = StockAnalysis(stock_info=stock_info, period=request.period)
        
        # 2. 准备服务和适配器
        llm_client = DeepSeekLLMAdapter(model=request.model)
        orchestrator = DeepSeekAnalysisOrchestrator(llm_client=llm_client)
        
        # 3. 确定启用的 Agent
        enabled_agents: List[AgentRole] = []
        if request.enabled_analysts:
            for key, enabled in request.enabled_analysts.items():
                if enabled:
                    try:
                        enabled_agents.append(AgentRole(key))
                    except ValueError:
                        pass # 忽略未知的角色

        # 4. 执行分析 (使用编排器)
        orchestrator.perform_analysis(
            analysis=analysis,
            data_bundle=bundle,
            enabled_agents=enabled_agents
        )

        # 5. 将领域对象转换为 DTO 返回
        return self._map_to_dto(analysis, bundle)

    def _map_to_dto(self, analysis: StockAnalysis, bundle: StockDataBundle) -> AnalysisResult:
        """将 StockAnalysis 实体转换为 AnalysisResult DTO"""
        
        agents_results = {}
        for role, review in analysis.reviews.items():
            # 重构为前端期望的格式 (参考 deepseek_agents.py 的输出)
            result_dict = {
                "agent_name": review.agent_name,
                "agent_role": role.value,
                "analysis": review.content.raw_output, # 或者 use details['full_text']
                "focus_areas": review.content.focus_areas,
                "timestamp": review.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            # 尝试回填一些数据字段，虽然 bundle 里有，但为了兼容性
            # 注意：Orchestrator 没有在 Review 里存原始数据，这里如果需要只能从 bundle 取
            # 但既然 bundle 传给了 UI，UI 应该直接用 bundle
            
            agents_results[role.value] = result_dict

        return AnalysisResult(
            agents_results=agents_results,
            discussion_result=analysis.team_discussion,
            final_decision=analysis.final_decision,
        )
