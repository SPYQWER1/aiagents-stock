"""
分析领域端口（Ports）。

端口用于定义应用层所依赖的能力契约（数据获取、AI分析、持久化），
基础设施层通过实现这些端口来对接外部系统。
"""

from __future__ import annotations

from typing import Any, Protocol

from aiagents_stock.domain.analysis.dto import (
    AnalysisResult,
    FundFlowData,
    NewsData,
    QuarterlyData,
    RiskData,
    SentimentData,
    StockDataBundle,
    StockRequest,
)
from aiagents_stock.domain.analysis.model import StockAnalysis


class MarketDataProvider(Protocol):
    """
    基础市场数据提供者（行情、财务）。
    """

    def get_stock_data_bundle(self, *, symbol: str, period: str) -> StockDataBundle:
        """获取股票数据聚合包（含 K 线、指标）。"""

    def get_stock_info(self, *, symbol: str) -> dict[str, Any]:
        """获取股票基本信息。"""

    def get_financial_data(self, *, symbol: str) -> Any:
        """获取财务数据。"""


class OptionalDataProvider(Protocol):
    """
    可选数据端口（资金流、情绪、新闻等）。
    """

    def get_quarterly_data(self, *, symbol: str) -> QuarterlyData | None:
        """获取季报数据。"""

    def get_fund_flow_data(self, *, symbol: str) -> FundFlowData | None:
        """获取资金流向数据。"""

    def get_sentiment_data(
        self, *, symbol: str, stock_data: Any
    ) -> SentimentData | None:
        """获取市场情绪数据。"""

    def get_news_data(self, *, symbol: str) -> NewsData | None:
        """获取新闻数据。"""

    def get_risk_data(self, *, symbol: str) -> RiskData | None:
        """获取风险数据。"""


class AIAnalyzer(Protocol):
    """
    AI 分析器端口。
    """

    def analyze(
        self,
        *,
        request: StockRequest,
        bundle: StockDataBundle,
    ) -> AnalysisResult:
        """执行分析。"""



class StockAnalysisRepository(Protocol):
    """
    基于聚合根的分析记录仓储接口。
    """
    
    def save(self, analysis: StockAnalysis) -> int:
        """保存分析聚合根，返回生成的 ID (int)。"""

    def find_by_id(self, analysis_id: str) -> StockAnalysis | None:
        """根据 ID 查找分析聚合根。"""


class StockBatchAnalysisRepository(Protocol):
    """
    批量分析历史记录仓储接口。
    """

    def save(
        self,
        batch_count: int,
        analysis_mode: str,
        success_count: int,
        failed_count: int,
        total_time: float,
        results: list[dict[str, Any]],
    ) -> int:
        """保存批量分析结果。"""

    def get_all(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取所有历史记录。"""

    def get_by_id(self, record_id: int) -> dict[str, Any] | None:
        """根据ID获取单条记录。"""

    def delete(self, record_id: int) -> bool:
        """删除记录。"""
