"""
分析领域端口（Ports）。

端口用于定义应用层所依赖的能力契约（数据获取、AI分析、持久化），
基础设施层通过实现这些端口来对接外部系统。
"""

from __future__ import annotations

from typing import Any, Protocol

from aiagents_stock.domain.analysis.dto import (
    AnalysisRecord,
    AnalysisResult,
    FundFlowData,
    NewsData,
    QuarterlyData,
    RiskData,
    SentimentData,
    StockDataBundle,
)


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
        """执行 AI 分析。"""


class AnalysisRecordRepository(Protocol):
    """
    分析记录持久化端口。

    该端口用于隔离存储实现（sqlite/其他DB），并提升用例可测试性。
    """

    def save(self, *, record: AnalysisRecord) -> int:
        """保存分析记录并返回记录 ID。"""

    def get(self, *, record_id: int) -> AnalysisRecord | None:
        """读取分析记录，若不存在返回 None。"""


from aiagents_stock.domain.analysis.model import StockAnalysis

class StockAnalysisRepository(Protocol):
    """
    基于聚合根的分析记录仓储接口。
    """
    
    def save(self, analysis: StockAnalysis) -> int:
        """保存分析聚合根，返回生成的 ID (int)。"""

    def find_by_id(self, analysis_id: str) -> StockAnalysis | None:
        """根据 ID 查找分析聚合根。"""
        """根据 ID 查找分析聚合根。"""


class LLMClient(Protocol):
    """
    LLM 客户端接口。
    只负责发送消息和接收响应，不包含任何业务 Prompt。
    """
    
    def call_chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        """调用聊天补全接口。"""
        ...
