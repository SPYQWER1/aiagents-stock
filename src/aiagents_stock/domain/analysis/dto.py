"""
分析领域 DTO（数据传输对象）。

该模块只包含数据结构定义，不包含任何 IO 逻辑，便于测试与跨层传递。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class StockRequest:
    """
    单股分析请求。

    Args:
        symbol: 股票代码（A股/港股/美股均可）
        period: 数据周期（例如 1y/6mo/3mo 等）
        model: AI 模型标识（例如 deepseek-chat）
        enabled_analysts: 启用的分析师配置（键为分析师标识，值为是否启用）
    """

    symbol: str
    period: str
    model: str
    enabled_analysts: dict[str, bool]


@dataclass(frozen=True)
class QuarterlyData:
    """季报数据。"""

    data: Any  # TODO: 进一步细化内部结构


@dataclass(frozen=True)
class FundFlowData:
    """资金流向数据。"""

    data: Any


@dataclass(frozen=True)
class SentimentData:
    """市场情绪数据。"""

    data: Any


@dataclass(frozen=True)
class NewsData:
    """新闻数据。"""

    data: Any


@dataclass(frozen=True)
class RiskData:
    """风险数据。"""

    data: Any


@dataclass(frozen=True)
class StockDataBundle:
    """
    股票数据聚合。

    Args:
        stock_info: 股票基本信息
        stock_data: 历史K线数据
        indicators: 最新指标快照
        financial_data: 财务数据
        fund_flow_data: 资金流向数据
        sentiment_data: 市场情绪数据
        news_data: 新闻数据
        quarterly_data: 季报数据
        risk_data: 风险数据
    """

    stock_info: dict[str, Any]
    stock_data: pd.DataFrame | None
    indicators: dict[str, Any] | None
    financial_data: Any | None = None
    fund_flow_data: FundFlowData | None = None
    sentiment_data: SentimentData | None = None
    news_data: NewsData | None = None
    quarterly_data: QuarterlyData | None = None
    risk_data: RiskData | None = None


@dataclass(frozen=True)
class AnalysisResult:
    """
    AI 分析输出。

    Args:
        agents_results: 各分析师输出
        discussion_result: 团队讨论结果
        final_decision: 最终决策结果
    """

    agents_results: dict[str, Any]
    discussion_result: Any
    final_decision: Any


@dataclass(frozen=True)
class AnalysisRecord:
    """
    可持久化的分析记录。

    Args:
        symbol: 股票代码
        stock_name: 股票名称
        period: 数据周期
        stock_info: 股票基本信息
        agents_results: 各分析师输出
        discussion_result: 团队讨论结果
        final_decision: 最终决策结果
    """

    symbol: str
    stock_name: str
    period: str
    stock_info: dict[str, Any]
    agents_results: dict[str, Any]
    discussion_result: Any
    final_decision: Any
