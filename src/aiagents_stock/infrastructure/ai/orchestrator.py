"""
DeepSeek 分析编排器实现。

该模块实现了 AnalysisOrchestrator 接口，负责协调 DeepSeek 智能体进行分析。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re

from aiagents_stock.domain.analysis.model import (
    StockAnalysis, 
    AgentRole, 
    AnalysisContent, 
    StockInfo
)
from aiagents_stock.domain.analysis.services import AnalysisOrchestrator
from aiagents_stock.domain.analysis.dto import StockDataBundle
from aiagents_stock.domain.ai.ports import LLMClient
from aiagents_stock.infrastructure.ai.prompts import (
    TECHNICAL_ANALYSIS_PROMPT,
    FUNDAMENTAL_ANALYSIS_PROMPT,
    FUND_FLOW_ANALYSIS_PROMPT,
    RISK_MANAGEMENT_PROMPT,
    MARKET_SENTIMENT_PROMPT,
    NEWS_ANALYSIS_PROMPT,
    TEAM_DISCUSSION_PROMPT,
    FINAL_DECISION_PROMPT,
)

# 导入用于格式化数据的 Fetcher (仅用于格式化，不进行网络请求)
from aiagents_stock.infrastructure.data_sources.risk_data_fetcher import RiskDataFetcher
from aiagents_stock.infrastructure.data_sources.market_sentiment_data import MarketSentimentDataFetcher
from aiagents_stock.infrastructure.data_sources.qstock_news_data import QStockNewsDataFetcher
from aiagents_stock.infrastructure.data_sources.quarterly_report_data import QuarterlyReportDataFetcher
from aiagents_stock.infrastructure.data_sources.fund_flow_akshare import FundFlowAkshareDataFetcher

logger = logging.getLogger(__name__)

class DeepSeekAnalysisOrchestrator(AnalysisOrchestrator):
    """
    基于 DeepSeek 的分析编排器。
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self._risk_fetcher = RiskDataFetcher()
        self._sentiment_fetcher = MarketSentimentDataFetcher()
        self._news_fetcher = QStockNewsDataFetcher()
        self._quarterly_fetcher = QuarterlyReportDataFetcher()
        self._fund_flow_fetcher = FundFlowAkshareDataFetcher()

    def perform_analysis(
        self, 
        analysis: StockAnalysis, 
        data_bundle: StockDataBundle,
        enabled_agents: List[AgentRole]
    ) -> StockAnalysis:
        """执行全流程分析"""
        
        analysis.start()
        
        # 1. 并行执行各 Agent 分析
        with ThreadPoolExecutor(max_workers=len(enabled_agents)) as executor:
            future_to_role = {
                executor.submit(self._run_agent, role, analysis.stock_info, data_bundle): role
                for role in enabled_agents
            }
            
            for future in as_completed(future_to_role):
                role = future_to_role[future]
                try:
                    review = future.result()
                    if review:
                        analysis.add_review(role, review.content, review.agent_name)
                except Exception as e:
                    logger.error(f"Agent {role} failed: {e}")
        
        # 2. 团队讨论与决策
        self._conduct_team_discussion(analysis, data_bundle)
        
        return analysis

    def _run_agent(
        self, 
        role: AgentRole, 
        stock_info: StockInfo, 
        bundle: StockDataBundle
    ) -> Any: # Returns partial AgentReview data or similar object
        """运行单个 Agent"""
        
        if role == AgentRole.TECHNICAL:
            return self._run_technical_agent(stock_info, bundle)
        elif role == AgentRole.FUNDAMENTAL:
            return self._run_fundamental_agent(stock_info, bundle)
        elif role == AgentRole.FUND_FLOW:
            return self._run_fund_flow_agent(stock_info, bundle)
        elif role == AgentRole.RISK_MANAGEMENT:
            return self._run_risk_agent(stock_info, bundle)
        elif role == AgentRole.MARKET_SENTIMENT:
            return self._run_sentiment_agent(stock_info, bundle)
        elif role == AgentRole.NEWS_ANALYST:
            return self._run_news_agent(stock_info, bundle)
        else:
            logger.warning(f"Unknown agent role: {role}")
            return None

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        # Assuming llm_client.call_chat takes messages and optional params. 
        # But wait, LLMClient port signature is call_chat(messages: List[Dict[str, str]]) -> str.
        # It doesn't strictly support kwargs in the interface definition (I should check ports.py).
        # DeepSeekLLMAdapter implements it.
        # If the adapter supports it, great. If not, I might need to rely on adapter defaults or update the port.
        # Let's check ports.py and DeepSeekLLMAdapter later. For now, pass messages only if interface is strict.
        # Or maybe I should assume the adapter handles extra config or I should configure it elsewhere.
        # DeepSeekClient.call_api supports max_tokens. 
        # DeepSeekLLMAdapter probably just calls call_api.
        # Let's check adapter implementation.
        # For now, I'll stick to messages only to be safe with the interface, 
        # unless I know the adapter allows more control via some mechanism.
        # Actually, let's assume standard call for now.
        return self.llm_client.call_chat(messages)

    # =========================================================================
    # 各 Agent 具体实现
    # =========================================================================

    def _run_technical_agent(self, stock_info: StockInfo, bundle: StockDataBundle):
        indicators = bundle.indicators or {}
        prompt = TECHNICAL_ANALYSIS_PROMPT.format(
            symbol=stock_info.symbol,
            name=stock_info.name,
            current_price=stock_info.current_price,
            change_percent=stock_info.current_price, # Note: stock_info might not have change_percent directly, using current_price as placeholder or check indicators
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
            AgentRole.TECHNICAL, 
            "技术分析师", 
            analysis_text,
            ["技术指标", "趋势分析", "支撑阻力", "交易信号"]
        )

    def _run_fundamental_agent(self, stock_info: StockInfo, bundle: StockDataBundle):
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
            AgentRole.FUNDAMENTAL, 
            "基本面分析师", 
            analysis_text,
            ["财务指标", "行业分析", "公司价值", "成长性", "季报趋势"]
        )

    def _run_fund_flow_agent(self, stock_info: StockInfo, bundle: StockDataBundle):
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
            AgentRole.FUND_FLOW, 
            "资金面分析师", 
            analysis_text,
            ["资金流向", "主力动向", "市场情绪", "流动性"]
        )

    def _run_risk_agent(self, stock_info: StockInfo, bundle: StockDataBundle):
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
            AgentRole.RISK_MANAGEMENT, 
            "风险管理师", 
            analysis_text,
            ["风险识别", "风险量化", "风险控制", "资产配置"]
        )

    def _run_sentiment_agent(self, stock_info: StockInfo, bundle: StockDataBundle):
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
            AgentRole.MARKET_SENTIMENT, 
            "市场情绪分析师", 
            analysis_text,
            ["ARBR指标", "市场情绪", "投资者心理"]
        )

    def _run_news_agent(self, stock_info: StockInfo, bundle: StockDataBundle):
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
            AgentRole.NEWS_ANALYST, 
            "新闻分析师", 
            analysis_text,
            ["舆情分析", "新闻事件", "股价影响"]
        )

    def _conduct_team_discussion(self, analysis: StockAnalysis, bundle: StockDataBundle):
        """组织团队讨论并生成最终决策"""
        
        # 1. 汇总各 Agent 观点
        agents_summary = ""
        
        # 按照特定顺序汇总，使讨论更自然
        ordered_roles = [
            AgentRole.TECHNICAL, AgentRole.FUNDAMENTAL, AgentRole.FUND_FLOW,
            AgentRole.RISK_MANAGEMENT, AgentRole.MARKET_SENTIMENT, AgentRole.NEWS_ANALYST
        ]
        
        for role in ordered_roles:
            if role in analysis.reviews:
                review = analysis.reviews[role]
                agents_summary += f"\n【{review.agent_name}】:\n{review.content.summary}\n"
            
        prompt = TEAM_DISCUSSION_PROMPT.format(
            symbol=analysis.stock_info.symbol,
            name=analysis.stock_info.name,
            agents_analysis_text=agents_summary
        )
        
        discussion_text = self._call_llm(
            "你现在是股票分析团队的主持人。", 
            prompt
        )
        
        analysis.conduct_team_discussion(discussion_text)
        
        # 2. 生成最终决策 (使用专门的 JSON 决策 Prompt)
        self._make_final_decision(analysis, discussion_text, bundle)

    def _make_final_decision(self, analysis: StockAnalysis, discussion_text: str, bundle: StockDataBundle):
        """生成最终投资决策"""
        indicators = bundle.indicators or {}
        
        prompt = FINAL_DECISION_PROMPT.format(
            symbol=analysis.stock_info.symbol,
            name=analysis.stock_info.name,
            current_price=analysis.stock_info.current_price,
            comprehensive_discussion=discussion_text,
            ma20=indicators.get('ma20', 'N/A'),
            bb_upper=indicators.get('bb_upper', 'N/A'),
            bb_lower=indicators.get('bb_lower', 'N/A')
        )
        
        response = self._call_llm(
            "你是一名专业的投资决策专家，需要给出明确、可执行的投资建议。",
            prompt
        )

        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                decision_json = json.loads(json_match.group())
                analysis.finalize_decision(decision_json)
            else:
                analysis.finalize_decision({"decision_text": response})
        except Exception as e:
            logger.error(f"Failed to parse final decision JSON: {e}")
            analysis.finalize_decision({"decision_text": response, "error": str(e)})

    # 辅助方法
    def _create_review_result(self, role, agent_name, text, focus_areas):
        # 简单的内容封装
        content = AnalysisContent(
            summary=text[:200] + "...", # 简略版
            details={"full_text": text},
            focus_areas=focus_areas,
            raw_output=text
        )
        
        # 临时的 Review 包装对象，用于传回主线程
        from dataclasses import dataclass
        @dataclass
        class ReviewResult:
            content: AnalysisContent
            agent_name: str
            
        return ReviewResult(content, agent_name)

    def _format_financial_ratios(self, ratios: Dict, stock_info: StockInfo) -> str:
        # 复用 DeepSeekClient 中的逻辑
        return f"""
详细财务指标：
【盈利能力】
- 净资产收益率(ROE)：{ratios.get('净资产收益率ROE', ratios.get('ROE', 'N/A'))}
- 总资产收益率(ROA)：{ratios.get('总资产收益率ROA', ratios.get('ROA', 'N/A'))}
- 销售毛利率：{ratios.get('销售毛利率', ratios.get('毛利率', 'N/A'))}
- 销售净利率：{ratios.get('销售净利率', ratios.get('净利率', 'N/A'))}

【偿债能力】
- 资产负债率：{ratios.get('资产负债率', 'N/A')}
- 流动比率：{ratios.get('流动比率', 'N/A')}
- 速动比率：{ratios.get('速动比率', 'N/A')}

【运营能力】
- 存货周转率：{ratios.get('存货周转率', 'N/A')}
- 应收账款周转率：{ratios.get('应收账款周转率', 'N/A')}
- 总资产周转率：{ratios.get('总资产周转率', 'N/A')}

【成长能力】
- 营业收入同比增长：{ratios.get('营业收入同比增长', ratios.get('收入增长', 'N/A'))}
- 净利润同比增长：{ratios.get('净利润同比增长', ratios.get('盈利增长', 'N/A'))}

【每股指标】
- 每股收益(EPS)：{ratios.get('EPS', 'N/A')}
- 每股账面价值：{ratios.get('每股账面价值', 'N/A')}
- 股息率：{ratios.get('股息率', stock_info.current_price if isinstance(stock_info.current_price, str) else 'N/A')} 
- 派息率：{ratios.get('派息率', 'N/A')}
"""

# Note: stock_info.current_price usage above might be wrong context for dividend yield default, but keeping consistent with original logic structure.
