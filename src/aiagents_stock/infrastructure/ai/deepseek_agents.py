"""
DeepSeek AI 分析器实现。

该模块实现了 AIAnalyzer 端口，协调多个专门的 AI 智能体进行股票分析。
"""

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict

from aiagents_stock.infrastructure.ai.deepseek_client import DeepSeekClient
from aiagents_stock.domain.analysis.dto import StockDataBundle
from aiagents_stock.infrastructure.ai.prompts import (
    RISK_MANAGEMENT_PROMPT,
    MARKET_SENTIMENT_PROMPT,
    NEWS_ANALYSIS_PROMPT,
    TEAM_DISCUSSION_PROMPT,
)

logger = logging.getLogger(__name__)


class DeepSeekAnalyzer:
    """DeepSeek 多智能体分析器"""

    def __init__(self, model="deepseek-chat"):
        self.model = model
        self.deepseek_client = DeepSeekClient(model=model)

    def technical_analyst_agent(self, stock_info: Dict, stock_data: Any, indicators: Dict) -> Dict[str, Any]:
        """技术面分析智能体"""
        logger.info("技术分析师正在分析中...")
        analysis = self.deepseek_client.technical_analysis(stock_info, stock_data, indicators)

        return {
            "agent_name": "技术分析师",
            "agent_role": "负责技术指标分析、图表形态识别、趋势判断",
            "analysis": analysis,
            "focus_areas": ["技术指标", "趋势分析", "支撑阻力", "交易信号"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def fundamental_analyst_agent(
        self, stock_info: Dict, financial_data: Dict = None, quarterly_data: Dict = None
    ) -> Dict[str, Any]:
        """基本面分析智能体"""
        logger.info("基本面分析师正在分析中...")
        analysis = self.deepseek_client.fundamental_analysis(stock_info, financial_data, quarterly_data)

        return {
            "agent_name": "基本面分析师",
            "agent_role": "负责公司财务分析、行业研究、估值分析",
            "analysis": analysis,
            "focus_areas": ["财务指标", "行业分析", "公司价值", "成长性", "季报趋势"],
            "quarterly_data": quarterly_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def fund_flow_analyst_agent(
        self, stock_info: Dict, indicators: Dict, fund_flow_data: Dict = None
    ) -> Dict[str, Any]:
        """资金面分析智能体"""
        logger.info("资金面分析师正在分析中...")
        analysis = self.deepseek_client.fund_flow_analysis(stock_info, indicators, fund_flow_data)

        return {
            "agent_name": "资金面分析师",
            "agent_role": "负责资金流向分析、主力行为研究、市场情绪判断",
            "analysis": analysis,
            "focus_areas": ["资金流向", "主力动向", "市场情绪", "流动性"],
            "fund_flow_data": fund_flow_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def risk_management_agent(self, stock_info: Dict, indicators: Dict, risk_data: Dict = None) -> Dict[str, Any]:
        """风险管理智能体"""
        logger.info("风险管理师正在评估中...")

        # 构建风险数据文本
        risk_data_text = ""
        if risk_data and risk_data.get("data_success"):
            from aiagents_stock.infrastructure.data_sources.risk_data_fetcher import RiskDataFetcher
            fetcher = RiskDataFetcher()
            risk_data_text = f"""
【实际风险数据】（来自问财）
{fetcher.format_risk_data_for_ai(risk_data)}
以上是通过问财（pywencai）获取的实际风险数据，请重点关注这些数据进行深度风险分析。
"""

        # 填充Prompt
        risk_prompt = RISK_MANAGEMENT_PROMPT.format(
            symbol=stock_info.get('symbol', 'N/A'),
            name=stock_info.get('name', 'N/A'),
            current_price=stock_info.get('current_price', 'N/A'),
            beta=stock_info.get('beta', 'N/A'),
            high_52w=stock_info.get('52_week_high', 'N/A'),
            low_52w=stock_info.get('52_week_low', 'N/A'),
            rsi=indicators.get('rsi', 'N/A'),
            risk_data_text=risk_data_text
        )

        messages = [
            {
                "role": "system",
                "content": "你是一名资深的风险管理专家，具有20年以上的风险识别和控制经验，擅长全面评估各类投资风险，特别关注限售解禁、股东减持、重要事件等可能影响股价的风险因素。你擅长从海量原始数据中提取关键信息，进行深度解析和量化评估。",
            },
            {"role": "user", "content": risk_prompt},
        ]

        analysis = self.deepseek_client.call_api(messages, max_tokens=6000)

        return {
            "agent_name": "风险管理师",
            "agent_role": "负责风险识别、风险评估、风险控制策略制定",
            "analysis": analysis,
            "focus_areas": [
                "限售解禁风险",
                "股东减持风险",
                "重要事件风险",
                "风险识别",
                "风险量化",
                "风险控制",
                "资产配置",
            ],
            "risk_data": risk_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def market_sentiment_agent(self, stock_info: Dict, sentiment_data: Dict = None) -> Dict[str, Any]:
        """市场情绪分析智能体"""
        logger.info("市场情绪分析师正在分析中...")

        # 构建带有市场情绪数据的prompt
        sentiment_data_text = ""
        if sentiment_data and sentiment_data.get("data_success"):
            from aiagents_stock.infrastructure.data_sources.market_sentiment_data import MarketSentimentDataFetcher
            fetcher = MarketSentimentDataFetcher()
            sentiment_data_text = f"""
【市场情绪实际数据】
{fetcher.format_sentiment_data_for_ai(sentiment_data)}

以上是通过akshare获取的实际市场情绪数据，请重点基于这些数据进行分析。
"""

        sentiment_prompt = MARKET_SENTIMENT_PROMPT.format(
            symbol=stock_info.get('symbol', 'N/A'),
            name=stock_info.get('name', 'N/A'),
            sector=stock_info.get('sector', 'N/A'),
            industry=stock_info.get('industry', 'N/A'),
            sentiment_data_text=sentiment_data_text
        )

        messages = [
            {
                "role": "system",
                "content": "你是一名专业的市场情绪分析师，擅长解读市场心理和投资者行为，善于利用ARBR等情绪指标进行分析。",
            },
            {"role": "user", "content": sentiment_prompt},
        ]

        analysis = self.deepseek_client.call_api(messages, max_tokens=4000)

        return {
            "agent_name": "市场情绪分析师",
            "agent_role": "负责市场情绪研究、投资者心理分析、热点追踪",
            "analysis": analysis,
            "focus_areas": ["ARBR指标", "市场情绪", "投资者心理", "资金活跃度", "恐慌贪婪指数"],
            "sentiment_data": sentiment_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def news_analyst_agent(self, stock_info: Dict, news_data: Dict = None) -> Dict[str, Any]:
        """新闻分析智能体"""
        logger.info("新闻分析师正在分析中...")

        # 构建带有新闻数据的prompt
        news_text = ""
        if news_data and news_data.get("data_success"):
            from aiagents_stock.infrastructure.data_sources.qstock_news_data import QStockNewsDataFetcher
            fetcher = QStockNewsDataFetcher()
            news_text = f"""
【最新新闻数据】
{fetcher.format_news_for_ai(news_data)}

以上是通过qstock获取的实际新闻数据，请重点基于这些数据进行分析。
"""

        news_prompt = NEWS_ANALYSIS_PROMPT.format(
            symbol=stock_info.get('symbol', 'N/A'),
            name=stock_info.get('name', 'N/A'),
            sector=stock_info.get('sector', 'N/A'),
            industry=stock_info.get('industry', 'N/A'),
            news_text=news_text
        )

        messages = [
            {
                "role": "system",
                "content": "你是一名专业的新闻分析师，擅长解读新闻事件、舆情分析，评估新闻对股价的影响。你具有敏锐的洞察力和丰富的市场经验。",
            },
            {"role": "user", "content": news_prompt},
        ]

        analysis = self.deepseek_client.call_api(messages, max_tokens=4000)

        return {
            "agent_name": "新闻分析师",
            "agent_role": "负责新闻事件分析、舆情研究、重大事件影响评估",
            "analysis": analysis,
            "focus_areas": ["新闻解读", "舆情分析", "事件影响", "市场反应", "投资机会"],
            "news_data": news_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def run_multi_agent_analysis(
        self,
        stock_info: Dict,
        bundle: StockDataBundle,
        enabled_analysts: Dict = None,
    ) -> Dict[str, Any]:
        """运行多智能体分析"""
        if enabled_analysts is None:
            enabled_analysts = {
                "technical": True,
                "fundamental": True,
                "fund_flow": True,
                "risk": True,
                "sentiment": True,
                "news": True,
            }

        logger.info("启动多智能体股票分析系统...")

        # 并行运行各个分析师
        agents_results = {}
        future_to_name = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            # 技术面分析
            if enabled_analysts.get("technical", True):
                future_to_name[
                    executor.submit(
                        self.technical_analyst_agent, stock_info, bundle.stock_data, bundle.indicators
                    )
                ] = "technical"

            # 基本面分析
            if enabled_analysts.get("fundamental", True):
                future_to_name[
                    executor.submit(
                        self.fundamental_analyst_agent,
                        stock_info,
                        bundle.financial_data,
                        bundle.quarterly_data.data if bundle.quarterly_data else None,
                    )
                ] = "fundamental"

            # 资金面分析
            if enabled_analysts.get("fund_flow", True):
                future_to_name[
                    executor.submit(
                        self.fund_flow_analyst_agent,
                        stock_info,
                        bundle.indicators,
                        bundle.fund_flow_data.data if bundle.fund_flow_data else None,
                    )
                ] = "fund_flow"

            # 风险管理分析
            if enabled_analysts.get("risk", True):
                future_to_name[
                    executor.submit(
                        self.risk_management_agent,
                        stock_info,
                        bundle.indicators,
                        bundle.risk_data.data if bundle.risk_data else None,
                    )
                ] = "risk_management"

            # 市场情绪分析
            if enabled_analysts.get("sentiment", False):
                future_to_name[
                    executor.submit(
                        self.market_sentiment_agent,
                        stock_info,
                        bundle.sentiment_data.data if bundle.sentiment_data else None,
                    )
                ] = "market_sentiment"

            # 新闻分析
            if enabled_analysts.get("news", False):
                future_to_name[
                    executor.submit(
                        self.news_analyst_agent,
                        stock_info,
                        bundle.news_data.data if bundle.news_data else None,
                    )
                ] = "news"

            # 等待所有任务完成并获取结果
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    agents_results[name] = future.result()
                except Exception as e:
                    logger.error(f"运行 {name} 分析师时发生错误: {e}")

        logger.info("所有已选择的分析师完成分析")
        return agents_results

    def conduct_team_discussion(self, agents_results: Dict[str, Any], stock_info: Dict) -> str:
        """进行团队讨论"""
        logger.info("分析团队正在进行综合讨论...")

        # 收集参与分析的分析师名单和报告
        participants = []
        reports = []

        if "technical" in agents_results:
            participants.append("技术分析师")
            reports.append(f"【技术分析师报告】\n{agents_results['technical'].get('analysis', '')}")

        if "fundamental" in agents_results:
            participants.append("基本面分析师")
            reports.append(f"【基本面分析师报告】\n{agents_results['fundamental'].get('analysis', '')}")

        if "fund_flow" in agents_results:
            participants.append("资金面分析师")
            reports.append(f"【资金面分析师报告】\n{agents_results['fund_flow'].get('analysis', '')}")

        if "risk_management" in agents_results:
            participants.append("风险管理师")
            reports.append(f"【风险管理师报告】\n{agents_results['risk_management'].get('analysis', '')}")

        if "market_sentiment" in agents_results:
            participants.append("市场情绪分析师")
            reports.append(f"【市场情绪分析师报告】\n{agents_results['market_sentiment'].get('analysis', '')}")

        if "news" in agents_results:
            participants.append("新闻分析师")
            reports.append(f"【新闻分析师报告】\n{agents_results['news'].get('analysis', '')}")

        # 组合所有报告
        all_reports = "\n\n".join(reports)

        discussion_prompt = TEAM_DISCUSSION_PROMPT.format(
            participants=', '.join(participants),
            name=stock_info.get('name', 'N/A'),
            symbol=stock_info.get('symbol', 'N/A'),
            reports=all_reports
        )

        messages = [
            {
                "role": "system",
                "content": "你需要模拟一场专业的投资团队讨论会议，体现不同角色的观点碰撞和最终共识形成。",
            },
            {"role": "user", "content": discussion_prompt},
        ]

        discussion_result = self.deepseek_client.call_api(messages, max_tokens=6000)

        logger.info("团队讨论完成")
        return discussion_result

    def make_final_decision(self, discussion_result: str, stock_info: Dict, bundle: StockDataBundle) -> Dict[str, Any]:
        """制定最终投资决策"""
        logger.info("正在制定最终投资决策...")

        decision = self.deepseek_client.final_decision(discussion_result, stock_info, bundle.indicators)

        logger.info("最终投资决策完成")
        return decision
