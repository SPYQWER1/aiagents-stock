"""
DeepSeek Agents 实现。

将具体的 Agent 分析逻辑从 Orchestrator 中分离出来，
每个 Agent 负责自己的数据准备、Prompt 组装和结果解析。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from aiagents_stock.domain.ai.ports import LLMClient
from aiagents_stock.domain.analysis.dto import StockDataBundle
from aiagents_stock.domain.analysis.model import AgentReview, AgentRole, AnalysisContent, StockInfo
from aiagents_stock.domain.analysis.prompts import (
    FUND_FLOW_ANALYSIS_PROMPT,
    FUNDAMENTAL_ANALYSIS_PROMPT,
    MARKET_SENTIMENT_PROMPT,
    NEWS_ANALYSIS_PROMPT,
    RISK_MANAGEMENT_PROMPT,
    TECHNICAL_ANALYSIS_PROMPT,
)
from aiagents_stock.domain.analysis.services import AnalysisAgent
from aiagents_stock.infrastructure.data_sources.fund_flow_akshare import FundFlowAkshareDataFetcher
from aiagents_stock.infrastructure.data_sources.market_sentiment_data import MarketSentimentDataFetcher
from aiagents_stock.infrastructure.data_sources.qstock_news_data import QStockNewsDataFetcher
from aiagents_stock.infrastructure.data_sources.quarterly_report_data import QuarterlyReportDataFetcher

# Fetchers
from aiagents_stock.infrastructure.data_sources.risk_data_fetcher import RiskDataFetcher

logger = logging.getLogger(__name__)

class BaseDeepSeekAgent(AnalysisAgent, ABC):
    """DeepSeek Agent 基类"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.llm_client.call_chat(messages, temperature=temperature, max_tokens=max_tokens)
    
    def _create_review_result(
        self, 
        role: AgentRole, 
        agent_name: str, 
        content: str, 
        focus_points: list[str]
    ) -> AgentReview:
        """Helper to create a AgentReview object."""
        return AgentReview(
            role=role,
            agent_name=agent_name,
            content=AnalysisContent(
                summary=content[:200] + "..." if len(content) > 200 else content,
                details={"full_content": content},
                focus_areas=focus_points,
                raw_output=content
            )
        )

    @abstractmethod
    def analyze(self, stock_info: StockInfo, data_bundle: StockDataBundle) -> Optional[AgentReview]:
        pass

class TechnicalAgent(BaseDeepSeekAgent):
    role = AgentRole.TECHNICAL
    
    def analyze(self, stock_info: StockInfo, bundle: StockDataBundle) -> Optional[AgentReview]:
        indicators = bundle.indicators or {}
        prompt = TECHNICAL_ANALYSIS_PROMPT.format(
            symbol=stock_info.symbol,
            name=stock_info.name,
            current_price=stock_info.current_price,
            change_percent=stock_info.current_price, # Note: check if change_percent is available
            price=indicators.get('price', 'N/A'),
            ma5=indicators.get('ma5', 'N/A'),
            ma10=indicators.get('ma10', 'N/A'),
            ma20=indicators.get('ma20', 'N/A'),
            ma60=indicators.get('ma60', 'N/A'),
            rsi=indicators.get('rsi', 'N/A'),
            macd=indicators.get('macd', 'N/A'),
            macd_signal=indicators.get('macd_signal', 'N/A'),
            bb_upper=indicators.get('bb_upper', 'N/A'),
            bb_lower=indicators.get('bb_lower', 'N/A'),
            k_value=indicators.get('k_value', 'N/A'),
            d_value=indicators.get('d_value', 'N/A'),
            volume_ratio=indicators.get('volume_ratio', 'N/A')
        )
        
        analysis_text = self._call_llm(
            "你是一名经验丰富的股票技术分析师，具有深厚的技术分析功底。", 
            prompt
        )
        
        return self._create_review_result(
            self.role, 
            "技术分析师", 
            analysis_text,
            ["技术指标", "趋势分析", "支撑阻力", "交易信号"]
        )

class FundamentalAgent(BaseDeepSeekAgent):
    role = AgentRole.FUNDAMENTAL
    
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client)
        self._quarterly_fetcher = QuarterlyReportDataFetcher()

    def _format_financial_ratios(self, ratios: Dict[str, Any], stock_info: StockInfo) -> str:
        """格式化财务比率数据"""
        lines = []
        lines.append(f"**股票代码**: {stock_info.symbol} | **名称**: {stock_info.name}")
        lines.append(f"**行业**: {stock_info.industry} | **板块**: {stock_info.sector}")
        
        # 主要指标
        key_metrics = ["市盈率", "市净率", "总市值", "流通市值", "每股收益", "每股净资产"]
        lines.append("\n【主要估值指标】")
        for k in key_metrics:
            if k in ratios:
                lines.append(f"- {k}: {ratios[k]}")
                
        # 盈利能力
        profit_metrics = ["净资产收益率", "总资产净利率", "毛利率", "净利率"]
        lines.append("\n【盈利能力】")
        for k in profit_metrics:
            if k in ratios:
                lines.append(f"- {k}: {ratios[k]}")
                
        # 成长能力
        growth_metrics = ["营业收入同比增长", "净利润同比增长"]
        lines.append("\n【成长能力】")
        for k in growth_metrics:
            if k in ratios:
                lines.append(f"- {k}: {ratios[k]}")
                
        return "\n".join(lines)

    def analyze(self, stock_info: StockInfo, bundle: StockDataBundle) -> Optional[AgentReview]:
        financial_data = bundle.financial_data or {}
        quarterly_data = bundle.quarterly_data
        
        # 格式化财务数据
        financial_section = ""
        ratios = financial_data.get("financial_ratios", {}) if isinstance(financial_data, dict) else {}
        if ratios:
            financial_section = self._format_financial_ratios(ratios, stock_info)

        # 格式化季报数据
        quarterly_section = ""
        if quarterly_data and hasattr(quarterly_data, 'data'):
             q_data_dict = quarterly_data.data
             if isinstance(q_data_dict, dict) and q_data_dict.get("data_success"):
                 quarterly_section = f"\n【最近8期季报详细数据】\n{self._quarterly_fetcher.format_quarterly_reports_for_ai(q_data_dict)}\n"
                 quarterly_section += "\n以上是通过akshare获取的最近8期季度财务报告，请重点基于这些数据进行趋势分析。\n"

        prompt = FUNDAMENTAL_ANALYSIS_PROMPT.format(
            symbol=stock_info.symbol,
            name=stock_info.name,
            industry=stock_info.industry,
            sector=stock_info.sector,
            pe=ratios.get('市盈率', 'N/A'),
            pb=ratios.get('市净率', 'N/A'),
            total_market_cap=ratios.get('总市值', 'N/A'),
            circulating_market_cap=ratios.get('流通市值', 'N/A'),
            financial_section=financial_section,
            quarterly_section=quarterly_section
        )
        
        analysis_text = self._call_llm(
            "你是一名资深的基本面分析师，擅长通过财务数据挖掘公司价值。", 
            prompt
        )
        
        return self._create_review_result(
            self.role, 
            "基本面分析师", 
            analysis_text,
            ["财务指标", "行业分析", "公司价值", "成长性", "季报趋势"]
        )

class FundFlowAgent(BaseDeepSeekAgent):
    role = AgentRole.FUND_FLOW
    
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client)
        self._fund_flow_fetcher = FundFlowAkshareDataFetcher()

    def analyze(self, stock_info: StockInfo, bundle: StockDataBundle) -> Optional[AgentReview]:
        indicators = bundle.indicators or {}
        fund_flow_data = bundle.fund_flow_data
        
        fund_flow_section = ""
        if fund_flow_data and hasattr(fund_flow_data, 'data'):
             f_data = fund_flow_data.data
             if isinstance(f_data, dict) and f_data.get("data_success"):
                 fund_flow_section = f"\n【近20个交易日资金流向详细数据】\n{self._fund_flow_fetcher.format_fund_flow_for_ai(f_data)}\n"
                 fund_flow_section += "\n以上是通过akshare从东方财富获取的实际资金流向数据，请重点基于这些数据进行趋势分析。\n"
             else:
                 fund_flow_section = "\n【资金流向数据】\n注意：未能获取到资金流向数据，将基于成交量进行分析。\n"
        else:
             fund_flow_section = "\n【资金流向数据】\n注意：未能获取到资金流向数据，将基于成交量进行分析。\n"

        prompt = FUND_FLOW_ANALYSIS_PROMPT.format(
            symbol=stock_info.symbol,
            name=stock_info.name,
            turnover_rate=indicators.get('turnover_rate', 'N/A'),
            volume_ratio=indicators.get('volume_ratio', 'N/A'),
            fund_flow_section=fund_flow_section
        )

        analysis_text = self._call_llm(
            "你是一名资深的资金面分析师，擅长从资金流向数据中洞察主力行为和市场趋势。", 
            prompt
        )

        return self._create_review_result(
            self.role, 
            "资金面分析师", 
            analysis_text,
            ["资金流向", "主力动向", "市场情绪", "流动性"]
        )

class RiskManagementAgent(BaseDeepSeekAgent):
    role = AgentRole.RISK_MANAGEMENT
    
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client)
        self._risk_fetcher = RiskDataFetcher()

    def analyze(self, stock_info: StockInfo, bundle: StockDataBundle) -> Optional[AgentReview]:
        indicators = bundle.indicators or {}
        risk_data = bundle.risk_data
        
        risk_data_text = ""
        if risk_data and hasattr(risk_data, 'data'):
            r_data = risk_data.data
            if isinstance(r_data, dict) and r_data.get("data_success"):
                risk_data_text = f"""
【实际风险数据】（来自问财）
{self._risk_fetcher.format_risk_data_for_ai(r_data)}
以上是通过问财（pywencai）获取的实际风险数据，请重点关注这些数据进行深度风险分析。
"""

        prompt = RISK_MANAGEMENT_PROMPT.format(
            symbol=stock_info.symbol,
            name=stock_info.name,
            current_price=stock_info.current_price,
            beta=indicators.get('beta', 'N/A'),
            high_52w=indicators.get('high_52w', 'N/A'),
            low_52w=indicators.get('low_52w', 'N/A'),
            rsi=indicators.get('rsi', 'N/A'),
            risk_data_text=risk_data_text
        )

        analysis_text = self._call_llm(
            "你是一名资深的风险管理专家，具有20年以上的风险识别和控制经验，擅长全面评估各类投资风险。", 
            prompt
        )

        return self._create_review_result(
            self.role, 
            "风险管理师", 
            analysis_text,
            ["风险识别", "风险量化", "风险控制", "资产配置"]
        )

class MarketSentimentAgent(BaseDeepSeekAgent):
    role = AgentRole.MARKET_SENTIMENT
    
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client)
        self._sentiment_fetcher = MarketSentimentDataFetcher()

    def analyze(self, stock_info: StockInfo, bundle: StockDataBundle) -> Optional[AgentReview]:
        sentiment_data = bundle.sentiment_data
        
        sentiment_data_text = ""
        if sentiment_data and hasattr(sentiment_data, 'data'):
             s_data = sentiment_data.data
             if isinstance(s_data, dict) and s_data.get("data_success"):
                 sentiment_data_text = f"""
【市场情绪实际数据】
{self._sentiment_fetcher.format_sentiment_data_for_ai(s_data)}

以上是通过akshare获取的实际市场情绪数据，请重点基于这些数据进行分析。
"""

        prompt = MARKET_SENTIMENT_PROMPT.format(
            symbol=stock_info.symbol,
            name=stock_info.name,
            sector=stock_info.sector,
            industry=stock_info.industry,
            sentiment_data_text=sentiment_data_text
        )

        analysis_text = self._call_llm(
            "你是一名专业的市场情绪分析师，擅长解读市场心理和投资者行为，善于利用ARBR等情绪指标进行分析。", 
            prompt
        )

        return self._create_review_result(
            self.role, 
            "市场情绪分析师", 
            analysis_text,
            ["ARBR指标", "市场情绪", "投资者心理"]
        )

class NewsAgent(BaseDeepSeekAgent):
    role = AgentRole.NEWS_ANALYST
    
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client)
        self._news_fetcher = QStockNewsDataFetcher()

    def analyze(self, stock_info: StockInfo, bundle: StockDataBundle) -> Optional[AgentReview]:
        news_data = bundle.news_data
        
        news_text = ""
        if news_data and hasattr(news_data, 'data'):
             n_data = news_data.data
             if isinstance(n_data, dict) and n_data.get("data_success"):
                 news_text = f"""
【最新新闻数据】
{self._news_fetcher.format_news_for_ai(n_data)}

以上是通过qstock获取的实际新闻数据，请重点基于这些数据进行分析。
"""

        prompt = NEWS_ANALYSIS_PROMPT.format(
            symbol=stock_info.symbol,
            name=stock_info.name,
            sector=stock_info.sector,
            industry=stock_info.industry,
            news_text=news_text
        )

        analysis_text = self._call_llm(
            "你是一名专业的新闻分析师，擅长解读新闻事件、舆情分析，评估新闻对股价的影响。", 
            prompt
        )

        return self._create_review_result(
            self.role, 
            "新闻分析师", 
            analysis_text,
            ["舆情分析", "新闻事件", "股价影响"]
        )
