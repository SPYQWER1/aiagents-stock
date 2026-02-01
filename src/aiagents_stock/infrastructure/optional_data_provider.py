"""
可选数据端口适配器。

该模块将现有的各种数据抓取器（资金流、情绪、新闻等）封装为领域端口 OptionalDataProvider。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiagents_stock.domain.analysis.dto import (
    FundFlowData,
    NewsData,
    QuarterlyData,
    RiskData,
    SentimentData,
)
from aiagents_stock.domain.analysis.ports import OptionalDataProvider
from aiagents_stock.infrastructure.market_data_provider import is_chinese_stock


@dataclass(frozen=True)
class DefaultOptionalDataProvider(OptionalDataProvider):
    """
    基于现有 Fetcher 实现的 OptionalDataProvider 适配器。
    """

    def get_quarterly_data(self, *, symbol: str) -> QuarterlyData | None:
        """获取季报数据（仅 A 股）。"""
        if not is_chinese_stock(symbol):
            return None

        from aiagents_stock.infrastructure.data_sources.quarterly_report_data import QuarterlyReportDataFetcher

        data = QuarterlyReportDataFetcher().get_quarterly_reports(symbol)
        return QuarterlyData(data=data) if data else None

    def get_fund_flow_data(self, *, symbol: str) -> FundFlowData | None:
        """获取资金流向数据（仅 A 股）。"""
        if not is_chinese_stock(symbol):
            return None

        from aiagents_stock.infrastructure.data_sources.fund_flow_akshare import FundFlowAkshareDataFetcher

        data = FundFlowAkshareDataFetcher().get_fund_flow_data(symbol)
        return FundFlowData(data=data) if data else None

    def get_sentiment_data(
        self, *, symbol: str, stock_data: Any
    ) -> SentimentData | None:
        """获取市场情绪数据（仅 A 股）。"""
        if not is_chinese_stock(symbol):
            return None

        if stock_data is None:
            return None

        from aiagents_stock.infrastructure.data_sources.market_sentiment_data import MarketSentimentDataFetcher

        data = MarketSentimentDataFetcher().get_market_sentiment_data(
            symbol, stock_data
        )
        return SentimentData(data=data) if data else None

    def get_news_data(self, *, symbol: str) -> NewsData | None:
        """获取新闻数据（仅 A 股）。"""
        if not is_chinese_stock(symbol):
            return None

        from aiagents_stock.infrastructure.data_sources.qstock_news_data import QStockNewsDataFetcher

        data = QStockNewsDataFetcher().get_stock_news(symbol)
        return NewsData(data=data) if data else None

    def get_risk_data(self, *, symbol: str) -> RiskData | None:
        """获取风险数据（仅 A 股）。"""
        if not is_chinese_stock(symbol):
            return None

        from aiagents_stock.infrastructure.data_sources.risk_data_fetcher import RiskDataFetcher

        data = RiskDataFetcher().get_risk_data(symbol)
        return RiskData(data=data) if data else None
