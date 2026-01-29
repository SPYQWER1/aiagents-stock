from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from aiagents_stock.ai.ai_agents import StockAnalysisAgents
from aiagents_stock.core.config_manager import config_manager
from aiagents_stock.data.stock_data import StockDataFetcher
from aiagents_stock.db.database import db
from aiagents_stock.web.config import CACHE_TTL_OPTIONAL_DATA_SECONDS, CACHE_TTL_STOCK_DATA_SECONDS, EnabledAnalysts


@dataclass(frozen=True)
class StockDataBundle:
    """股票数据与技术指标的聚合类。"""

    stock_info: dict[str, Any]
    stock_data: pd.DataFrame | None
    indicators: dict[str, Any] | None


def check_api_key() -> bool:
    """检查 DeepSeek API Key 是否配置。"""

    cfg = config_manager.read_env()
    return bool(cfg.get("DEEPSEEK_API_KEY", "").strip())


def get_stock_data_uncached(symbol: str, period: str) -> StockDataBundle:
    """获取股票数据（不使用 Streamlit 缓存，适用于子线程）。"""

    fetcher = StockDataFetcher()
    stock_info = fetcher.get_stock_info(symbol)
    stock_data = fetcher.get_stock_data(symbol, period)
    
    #  处理股票数据获取失败的情况
    if isinstance(stock_data, dict) and "error" in stock_data:
        return StockDataBundle(stock_info=stock_info, stock_data=None, indicators=None)

    stock_data_with_indicators = fetcher.calculate_technical_indicators(stock_data)
    indicators = fetcher.get_latest_indicators(stock_data_with_indicators)
    return StockDataBundle(stock_info=stock_info, stock_data=stock_data_with_indicators, indicators=indicators)


@st.cache_data(ttl=CACHE_TTL_STOCK_DATA_SECONDS)
def get_stock_data(symbol: str, period: str) -> StockDataBundle:
    """获取股票数据（带缓存）。"""

    return get_stock_data_uncached(symbol, period)


def parse_stock_list(stock_input: str) -> list[str]:
    """解析批量股票代码输入。"""

    if not stock_input or not stock_input.strip():
        return []

    lines = stock_input.strip().split("\n")
    raw: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "," in line:
            raw.extend([code.strip() for code in line.split(",") if code.strip()])
        elif " " in line:
            raw.extend([code.strip() for code in line.split() if code.strip()])
        else:
            raw.append(line)

    seen: set[str] = set()
    unique: list[str] = []
    for code in raw:
        if code not in seen:
            seen.add(code)
            unique.append(code)
    return unique


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_financial_data(symbol: str) -> Any:
    """获取财务数据（带缓存）。"""

    return get_financial_data_uncached(symbol)


def get_financial_data_uncached(symbol: str) -> Any:
    """获取财务数据（不使用 Streamlit 缓存，适用于子线程）。"""

    fetcher = StockDataFetcher()
    return fetcher.get_financial_data(symbol)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_quarterly_data(symbol: str) -> Any | None:
    """获取季报数据（仅 A 股，带缓存）。"""

    return get_quarterly_data_uncached(symbol)


def get_quarterly_data_uncached(symbol: str) -> Any | None:
    """获取季报数据（仅 A 股，不使用 Streamlit 缓存，适用于子线程）。"""

    fetcher = StockDataFetcher()
    if not fetcher._is_chinese_stock(symbol):
        return None
    from aiagents_stock.data.quarterly_report_data import QuarterlyReportDataFetcher

    quarterly_fetcher = QuarterlyReportDataFetcher()
    return quarterly_fetcher.get_quarterly_reports(symbol)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_fund_flow_data(symbol: str) -> Any | None:
    """获取资金流向数据（仅 A 股，带缓存）。"""

    return get_fund_flow_data_uncached(symbol)


def get_fund_flow_data_uncached(symbol: str) -> Any | None:
    """获取资金流向数据（仅 A 股，不使用 Streamlit 缓存，适用于子线程）。"""

    fetcher = StockDataFetcher()
    if not fetcher._is_chinese_stock(symbol):
        return None
    from aiagents_stock.data.fund_flow_akshare import FundFlowAkshareDataFetcher

    fund_flow_fetcher = FundFlowAkshareDataFetcher()
    return fund_flow_fetcher.get_fund_flow_data(symbol)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_sentiment_data(symbol: str, period: str) -> Any | None:
    """获取市场情绪数据（仅 A 股，带缓存）。"""

    return get_sentiment_data_uncached(symbol, period, use_cache_for_stock_data=True)


def get_sentiment_data_uncached(symbol: str, period: str, *, use_cache_for_stock_data: bool) -> Any | None:
    """获取市场情绪数据（仅 A 股，不使用 Streamlit 缓存，适用于子线程）。"""

    fetcher = StockDataFetcher()
    if not fetcher._is_chinese_stock(symbol):
        return None

    bundle = get_stock_data(symbol, period) if use_cache_for_stock_data else get_stock_data_uncached(symbol, period)
    if bundle.stock_data is None:
        return None

    from aiagents_stock.data.market_sentiment_data import MarketSentimentDataFetcher

    sentiment_fetcher = MarketSentimentDataFetcher()
    return sentiment_fetcher.get_market_sentiment_data(symbol, bundle.stock_data)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_news_data(symbol: str) -> Any | None:
    """获取新闻数据（仅 A 股，带缓存）。"""

    return get_news_data_uncached(symbol)


def get_news_data_uncached(symbol: str) -> Any | None:
    """获取新闻数据（仅 A 股，不使用 Streamlit 缓存，适用于子线程）。"""

    fetcher = StockDataFetcher()
    if not fetcher._is_chinese_stock(symbol):
        return None
    from aiagents_stock.data.qstock_news_data import QStockNewsDataFetcher

    news_fetcher = QStockNewsDataFetcher()
    return news_fetcher.get_stock_news(symbol)


@st.cache_data(ttl=CACHE_TTL_OPTIONAL_DATA_SECONDS)
def get_risk_data(symbol: str) -> Any | None:
    """获取风险数据（仅 A 股，带缓存）。"""

    return get_risk_data_uncached(symbol)


def get_risk_data_uncached(symbol: str) -> Any | None:
    """获取风险数据（仅 A 股，不使用 Streamlit 缓存，适用于子线程）。"""

    fetcher = StockDataFetcher()
    if not fetcher._is_chinese_stock(symbol):
        return None
    return fetcher.get_risk_data(symbol)


@st.cache_resource
def get_agents(selected_model: str) -> StockAnalysisAgents:
    """创建并缓存 StockAnalysisAgents 资源（仅主线程使用）。"""

    return StockAnalysisAgents(model=selected_model)


def run_ai_analysis(
    *,
    stock_info: dict[str, Any],
    stock_data: pd.DataFrame,
    indicators: dict[str, Any] | None,
    financial_data: Any,
    enabled_analysts: EnabledAnalysts,
    selected_model: str,
    use_cached_agents: bool = True,
    fund_flow_data: Any | None = None,
    sentiment_data: Any | None = None,
    news_data: Any | None = None,
    quarterly_data: Any | None = None,
    risk_data: Any | None = None,
) -> tuple[dict[str, dict[str, Any]], Any, Any]:
    """执行多智能体分析、团队讨论与最终决策。"""

    agents = get_agents(selected_model) if use_cached_agents else StockAnalysisAgents(model=selected_model)
    agents_results = agents.run_multi_agent_analysis(
        stock_info,
        stock_data,
        indicators,
        financial_data,
        fund_flow_data,
        sentiment_data,
        news_data,
        quarterly_data,
        risk_data,
        enabled_analysts=enabled_analysts.as_dict(),
    )
    discussion_result = agents.conduct_team_discussion(agents_results, stock_info)
    final_decision = agents.make_final_decision(discussion_result, stock_info, indicators)
    return agents_results, discussion_result, final_decision


def save_analysis_to_db(
    *,
    symbol: str,
    stock_name: str,
    period: str,
    stock_info: dict[str, Any],
    agents_results: dict[str, dict[str, Any]],
    discussion_result: Any,
    final_decision: Any,
) -> tuple[bool, str | None]:
    """保存分析结果到数据库。"""

    try:
        db.save_analysis(
            symbol=symbol,
            stock_name=stock_name,
            period=period,
            stock_info=stock_info,
            agents_results=agents_results,
            discussion_result=discussion_result,
            final_decision=final_decision,
        )
        return True, None
    except Exception as exc:
        return False, str(exc)
