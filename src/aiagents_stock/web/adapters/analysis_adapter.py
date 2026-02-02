from __future__ import annotations
from typing import Any, Iterator
import streamlit as st

from aiagents_stock.application.analysis.use_cases import BatchAnalyzeStocksRequest, BatchAnalysisItemResult
from aiagents_stock.domain.analysis.dto import (
    FundFlowData,
    NewsData,
    QuarterlyData,
    RiskData,
    SentimentData,
    StockDataBundle,
    StockRequest,
)
from aiagents_stock.web.config import (
    CACHE_TTL_OPTIONAL_DATA_SECONDS,
    CACHE_TTL_STOCK_DATA_SECONDS,
    EnabledAnalysts,
)
from aiagents_stock.container import DIContainer


def check_api_key() -> bool:
    """检查 DeepSeek API Key 是否配置。"""
    return DIContainer.check_api_key()


@st.cache_data(ttl=CACHE_TTL_STOCK_DATA_SECONDS)
def get_stock_data(symbol: str, period: str) -> StockDataBundle:
    """UI 专用的数据代理：带 Streamlit 缓存。"""
    return DIContainer.get_market_data_provider().get_stock_data_bundle(symbol=symbol, period=period)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_financial_data(symbol: str) -> Any:
    """获取财务数据（带缓存）。"""
    return DIContainer.get_market_data_provider().get_financial_data(symbol=symbol)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_quarterly_data(symbol: str) -> QuarterlyData | None:
    """获取季报数据（仅 A 股，带缓存）。"""
    return DIContainer.get_optional_data_provider().get_quarterly_data(symbol=symbol)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_fund_flow_data(symbol: str) -> FundFlowData | None:
    """获取资金流向数据（仅 A 股，带缓存）。"""
    return DIContainer.get_optional_data_provider().get_fund_flow_data(symbol=symbol)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_sentiment_data(symbol: str, period: str) -> SentimentData | None:
    """获取市场情绪数据（仅 A 股，带缓存）。"""
    # 情绪分析需要K线数据作为上下文
    bundle = get_stock_data(symbol, period)
    if bundle.stock_data is None:
        return None

    return DIContainer.get_optional_data_provider().get_sentiment_data(
        symbol=symbol, stock_data=bundle.stock_data
    )


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_news_data(symbol: str) -> NewsData | None:
    """获取新闻数据（仅 A 股，带缓存）。"""
    return DIContainer.get_optional_data_provider().get_news_data(symbol=symbol)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_risk_data(symbol: str) -> RiskData | None:
    """获取风险数据（仅 A 股，带缓存）。"""
    return DIContainer.get_optional_data_provider().get_risk_data(symbol=symbol)


def analyze_single_stock_via_use_case(
    *,
    symbol: str,
    period: str,
    enabled: EnabledAnalysts,
    selected_model: str,
    use_cached_agents: bool = True,
    preloaded_bundle: StockDataBundle | None = None,
    preloaded_financial_data: Any | None = None,
) -> dict[str, Any]:
    """
    新架构入口：组装依赖并执行单股分析用例。

    Args:
        symbol: 股票代码
        period: 数据周期
        enabled: 启用的分析师配置
        selected_model: 模型标识
        use_cached_agents: 是否使用缓存的 agents 资源
        preloaded_bundle: 可选的预加载市场数据（若提供则跳过抓取）
        preloaded_financial_data: 可选的预加载财务数据（若提供则跳过抓取）

    Returns:
        dict: 便于表现层渲染的结构化结果
    """
    use_case = DIContainer.create_analyze_single_stock_use_case(
        model=selected_model,
        use_cache=use_cached_agents
    )

    response = use_case.execute(
        request=StockRequest(
            symbol=symbol,
            period=period,
            model=selected_model,
            enabled_analysts=enabled.as_dict(),
        ),
        preloaded_bundle=preloaded_bundle,
        preloaded_financial_data=preloaded_financial_data,
    )

    return {
        "record_id": response.record_id,
        "stock_info": response.bundle.stock_info,
        "stock_data": response.bundle.stock_data,
        "indicators": response.bundle.indicators,
        "agents_results": response.analysis_result.agents_results,
        "discussion_result": response.analysis_result.discussion_result,
        "final_decision": response.analysis_result.final_decision,
    }


def analyze_batch_stocks_via_use_case(
    *,
    stock_list: list[str],
    period: str,
    enabled: EnabledAnalysts,
    selected_model: str,
    max_workers: int = 1,
    timeout_seconds: int | None = None
) -> Iterator[BatchAnalysisItemResult]:
    """
    新架构入口：执行批量分析用例。
    """
    use_case = DIContainer.create_batch_analyze_stocks_use_case(model=selected_model)
    request = BatchAnalyzeStocksRequest(
        stock_list=stock_list,
        period=period,
        enabled_analysts=enabled.as_dict(),
        selected_model=selected_model,
        max_workers=max_workers,
        timeout_seconds=timeout_seconds
    )
    yield from use_case.execute(request)
