"""
分析用例（Use Cases）。

该模块不依赖 Streamlit，支持通过依赖注入对数据源、AI 与存储进行替换或 mock。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiagents_stock.domain.analysis.dto import  AnalysisResult, StockDataBundle, StockRequest
from aiagents_stock.domain.analysis.model import StockAnalysis, StockInfo, AgentRole
from aiagents_stock.domain.analysis.ports import (
    AIAnalyzer,
    AnalysisRecordRepository,
    MarketDataProvider,
    OptionalDataProvider,
    StockAnalysisRepository,
)
from aiagents_stock.domain.analysis.services import AnalysisOrchestrator


@dataclass(frozen=True)
class AnalyzeSingleStockResponse:
    """
    单股分析用例响应。

    Args:
        record_id: 持久化后的记录 ID
        bundle: 股票数据聚合（用于 UI 展示）
        analysis_result: AI 分析输出
    """

    record_id: int
    bundle: StockDataBundle
    analysis_result: AnalysisResult


class AnalyzeSingleStockUseCase:
    """
    单股分析用例。

    该用例只做流程编排：
    1) 获取市场数据聚合与财务数据
    2) 调用领域服务 orchestrator 进行分析
    3) 持久化分析聚合根
    """

    def __init__(
        self,
        *,
        data_provider: MarketDataProvider,
        optional_data_provider: OptionalDataProvider,
        orchestrator: AnalysisOrchestrator,
        repository: StockAnalysisRepository,
        # 兼容旧代码，暂时保留可选参数，但在新逻辑中不再使用
        analyzer: AIAnalyzer | None = None,
        old_repository: AnalysisRecordRepository | None = None,
    ) -> None:
        self._data_provider = data_provider
        self._optional_data_provider = optional_data_provider
        self._orchestrator = orchestrator
        self._repository = repository
        
    def execute(
        self,
        *,
        request: StockRequest,
        preloaded_bundle: StockDataBundle | None = None,
        preloaded_financial_data: Any | None = None,
    ) -> AnalyzeSingleStockResponse:
        """
        执行分析用例。

        Args:
            request: 分析请求参数
            preloaded_bundle: 预加载的股票数据包（若提供则跳过市场数据抓取）
            preloaded_financial_data: 预加载的财务数据（若提供则跳过财务数据抓取）
        """

        symbol = request.symbol
        period = request.period
        enabled = request.enabled_analysts

        # 1. 获取市场数据（优先使用预加载数据）
        bundle = preloaded_bundle
        if bundle is None:
            bundle = self._data_provider.get_stock_data_bundle(
                symbol=symbol, period=period
            )

        # 2. 获取财务数据（优先使用预加载数据）
        financial_data = preloaded_financial_data
        if financial_data is None:
            financial_data = self._data_provider.get_financial_data(symbol=symbol)

        # 3. 按需获取扩展数据
        quarterly_data = None
        if enabled.get("fundamental", False):
            quarterly_data = self._optional_data_provider.get_quarterly_data(
                symbol=symbol
            )

        fund_flow_data = None
        if enabled.get("technical", False):
            fund_flow_data = self._optional_data_provider.get_fund_flow_data(
                symbol=symbol
            )

        sentiment_data = None
        if enabled.get("sentiment", False):
            sentiment_data = self._optional_data_provider.get_sentiment_data(
                symbol=symbol, stock_data=bundle.stock_data
            )

        news_data = None
        if enabled.get("news", False):
            news_data = self._optional_data_provider.get_news_data(symbol=symbol)

        risk_data = None
        if enabled.get("risk", False):
            risk_data = self._optional_data_provider.get_risk_data(symbol=symbol)

        # 4. 组装完整的数据包
        full_bundle = StockDataBundle(
            stock_info=bundle.stock_info,
            stock_data=bundle.stock_data,
            indicators=bundle.indicators,
            financial_data=financial_data,
            fund_flow_data=fund_flow_data,
            sentiment_data=sentiment_data,
            news_data=news_data,
            quarterly_data=quarterly_data,
            risk_data=risk_data,
        )

        # 5. 构建领域对象并执行分析 (Refactored to DDD)
        
        # 5.1 创建聚合根
        stock_info_obj = StockInfo.from_dict(full_bundle.stock_info)
        analysis = StockAnalysis(stock_info=stock_info_obj, period=period)

        # 5.2 确定启用的分析师角色
        # 建立请求参数键名到领域模型 AgentRole 的映射
        role_mapping = {
            "technical": AgentRole.TECHNICAL,
            "fundamental": AgentRole.FUNDAMENTAL,
            "fund_flow": AgentRole.FUND_FLOW,
            "risk": AgentRole.RISK_MANAGEMENT,
            "sentiment": AgentRole.MARKET_SENTIMENT,
            "news": AgentRole.NEWS_ANALYST,
        }

        enabled_roles = []
        for role_key, is_enabled in enabled.items():
            if is_enabled:
                if role_key in role_mapping:
                    enabled_roles.append(role_mapping[role_key])
                else:
                    try:
                        enabled_roles.append(AgentRole(role_key))
                    except ValueError:
                        # 忽略未定义的角色
                        pass

        # 5.3 调用编排器服务
        self._orchestrator.perform_analysis(
            analysis=analysis,
            data_bundle=full_bundle,
            enabled_agents=enabled_roles
        )

        # 6. 持久化聚合根
        record_id = self._repository.save(analysis)

        # 7. 转换结果以适配旧版响应 DTO
        agents_results = {}
        for role, review in analysis.reviews.items():
            agents_results[role.value] = {
                "agent_name": review.agent_name,
                "analysis": review.content.raw_output,
                "focus_areas": review.content.focus_areas,
                "timestamp": review.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        analysis_result = AnalysisResult(
            agents_results=agents_results,
            discussion_result=analysis.team_discussion,
            final_decision=analysis.final_decision
        )

        return AnalyzeSingleStockResponse(
            record_id=record_id,
            bundle=full_bundle,
            analysis_result=analysis_result,
        )
