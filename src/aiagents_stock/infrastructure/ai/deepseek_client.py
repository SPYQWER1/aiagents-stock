import json
from typing import Any, Dict, List, Optional

import openai

from aiagents_stock.core.config_manager import config_manager
from aiagents_stock.infrastructure.ai.prompts import (
    COMPREHENSIVE_DISCUSSION_PROMPT,
    FINAL_DECISION_PROMPT,
    FUND_FLOW_ANALYSIS_PROMPT,
    FUNDAMENTAL_ANALYSIS_PROMPT,
    TECHNICAL_ANALYSIS_PROMPT,
)


class DeepSeekClient:
    """DeepSeek API客户端"""

    def __init__(self, model="deepseek-chat"):
        self.model = model
        config = config_manager.read_env()
        self.client = openai.OpenAI(
            api_key=config.get("DEEPSEEK_API_KEY", ""),
            base_url=config.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )

    def call_chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """实现 LLMClient 接口"""
        return self.call_api(messages, model, temperature, max_tokens)

    def call_api(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """调用DeepSeek API"""
        # 使用实例的模型，如果没有传入则使用默认模型
        model_to_use = model or self.model

        # 对于 reasoner 模型，自动增加 max_tokens
        if "reasoner" in model_to_use.lower() and max_tokens <= 2000:
            max_tokens = 8000  # reasoner 模型需要更多 tokens 来输出推理过程

        try:
            response = self.client.chat.completions.create(
                model=model_to_use, messages=messages, temperature=temperature, max_tokens=max_tokens
            )

            # 处理 reasoner 模型的响应
            message = response.choices[0].message

            # reasoner 模型可能包含 reasoning_content（推理过程）和 content（最终答案）
            # 我们返回完整内容，包括推理过程（如果有的话）
            result = ""

            # 检查是否有推理内容
            if hasattr(message, "reasoning_content") and message.reasoning_content:
                result += f"【推理过程】\n{message.reasoning_content}\n\n"

            # 添加最终内容
            if message.content:
                result += message.content

            return result if result else "API返回空响应"

        except Exception as e:
            return f"API调用失败: {str(e)}"

    def technical_analysis(self, stock_info: Dict, stock_data: Any, indicators: Dict) -> str:
        """技术面分析"""
        prompt = TECHNICAL_ANALYSIS_PROMPT.format(
            symbol=stock_info.get("symbol", "N/A"),
            name=stock_info.get("name", "N/A"),
            current_price=stock_info.get("current_price", "N/A"),
            change_percent=stock_info.get("change_percent", "N/A"),
            price=indicators.get("price", "N/A"),
            ma5=indicators.get("ma5", "N/A"),
            ma10=indicators.get("ma10", "N/A"),
            ma20=indicators.get("ma20", "N/A"),
            ma60=indicators.get("ma60", "N/A"),
            rsi=indicators.get("rsi", "N/A"),
            macd=indicators.get("macd", "N/A"),
            macd_signal=indicators.get("macd_signal", "N/A"),
            bb_upper=indicators.get("bb_upper", "N/A"),
            bb_lower=indicators.get("bb_lower", "N/A"),
            k_value=indicators.get("k_value", "N/A"),
            d_value=indicators.get("d_value", "N/A"),
            volume_ratio=indicators.get("volume_ratio", "N/A"),
        )

        messages = [
            {"role": "system", "content": "你是一名经验丰富的股票技术分析师，具有深厚的技术分析功底。"},
            {"role": "user", "content": prompt},
        ]

        return self.call_api(messages)

    def fundamental_analysis(self, stock_info: Dict, financial_data: Dict = None, quarterly_data: Dict = None) -> str:
        """基本面分析"""

        # 构建财务数据部分
        financial_section = ""
        if financial_data and not financial_data.get("error"):
            ratios = financial_data.get("financial_ratios", {})
            if ratios:
                financial_section = f"""
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
- 股息率：{ratios.get('股息率', stock_info.get('dividend_yield', 'N/A'))}
- 派息率：{ratios.get('派息率', 'N/A')}
"""

            # 添加报告期信息
            if ratios.get("报告期"):
                financial_section = f"\n财务数据报告期：{ratios.get('报告期')}\n" + financial_section

        # 构建季报数据部分
        quarterly_section = ""
        if quarterly_data and quarterly_data.get("data_success"):
            # 使用格式化的季报数据
            from aiagents_stock.infrastructure.data_sources.quarterly_report_data import QuarterlyReportDataFetcher

            fetcher = QuarterlyReportDataFetcher()
            quarterly_section = f"""

【最近8期季报详细数据】
{fetcher.format_quarterly_reports_for_ai(quarterly_data)}

以上是通过akshare获取的最近8期季度财务报告，请重点基于这些数据进行趋势分析。
"""

        prompt = FUNDAMENTAL_ANALYSIS_PROMPT.format(
            symbol=stock_info.get("symbol", "N/A"),
            name=stock_info.get("name", "N/A"),
            industry=stock_info.get("industry", "N/A"),
            sector=stock_info.get("sector", "N/A"),
            pe=stock_info.get("pe_ratio", "N/A"),
            pb=stock_info.get("pb_ratio", "N/A"),
            total_market_cap=stock_info.get("market_cap", "N/A"),
            circulating_market_cap=stock_info.get("circulating_market_cap", "N/A"),
            financial_section=financial_section,
            quarterly_section=quarterly_section,
        )

        messages = [
            {"role": "system", "content": "你是一名经验丰富的股票基本面分析师，擅长公司财务分析和行业研究。"},
            {"role": "user", "content": prompt},
        ]

        return self.call_api(messages)

    def fund_flow_analysis(self, stock_info: Dict, indicators: Dict, fund_flow_data: Dict = None) -> str:
        """资金面分析"""

        # 构建资金流向数据部分 - 使用akshare格式化数据
        fund_flow_section = ""
        if fund_flow_data and fund_flow_data.get("data_success"):
            # 使用格式化的资金流向数据
            from aiagents_stock.infrastructure.data_sources.fund_flow_akshare import FundFlowAkshareDataFetcher

            fetcher = FundFlowAkshareDataFetcher()
            fund_flow_section = f"""

【近20个交易日资金流向详细数据】
{fetcher.format_fund_flow_for_ai(fund_flow_data)}

以上是通过akshare从东方财富获取的实际资金流向数据，请重点基于这些数据进行趋势分析。
"""
        else:
            fund_flow_section = "\n【资金流向数据】\n注意：未能获取到资金流向数据，将基于成交量进行分析。\n"

        prompt = FUND_FLOW_ANALYSIS_PROMPT.format(
            symbol=stock_info.get("symbol", "N/A"),
            name=stock_info.get("name", "N/A"),
            turnover_rate=stock_info.get("turnover_rate", "N/A"),
            volume_ratio=indicators.get("volume_ratio", "N/A"),
            fund_flow_section=fund_flow_section,
        )

        messages = [
            {
                "role": "system",
                "content": "你是一名经验丰富的资金面分析师，擅长市场资金流向和主力行为分析，能够深入解读资金数据背后的投资逻辑。",
            },
            {"role": "user", "content": prompt},
        ]

        return self.call_api(messages, max_tokens=3000)

    def comprehensive_discussion(
        self, technical_report: str, fundamental_report: str, fund_flow_report: str, stock_info: Dict
    ) -> str:
        """综合讨论"""
        prompt = COMPREHENSIVE_DISCUSSION_PROMPT.format(
            symbol=stock_info.get("symbol", "N/A"),
            name=stock_info.get("name", "N/A"),
            current_price=stock_info.get("current_price", "N/A"),
            technical_report=technical_report,
            fundamental_report=fundamental_report,
            fund_flow_report=fund_flow_report,
        )

        messages = [
            {"role": "system", "content": "你是一名资深的首席投资分析师，擅长综合不同维度的分析形成投资判断。"},
            {"role": "user", "content": prompt},
        ]

        return self.call_api(messages, max_tokens=6000)

    def final_decision(self, comprehensive_discussion: str, stock_info: Dict, indicators: Dict) -> Dict[str, Any]:
        """最终投资决策"""
        prompt = FINAL_DECISION_PROMPT.format(
            symbol=stock_info.get("symbol", "N/A"),
            name=stock_info.get("name", "N/A"),
            current_price=stock_info.get("current_price", "N/A"),
            comprehensive_discussion=comprehensive_discussion,
            ma20=indicators.get("ma20", "N/A"),
            bb_upper=indicators.get("bb_upper", "N/A"),
            bb_lower=indicators.get("bb_lower", "N/A"),
        )

        messages = [
            {"role": "system", "content": "你是一名专业的投资决策专家，需要给出明确、可执行的投资建议。"},
            {"role": "user", "content": prompt},
        ]

        response = self.call_api(messages, temperature=0.3, max_tokens=4000)

        try:
            # 尝试解析JSON响应
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                decision_json = json.loads(json_match.group())
                return decision_json
            else:
                # 如果无法解析JSON，返回文本响应
                return {"decision_text": response}
        except Exception:
            return {"decision_text": response}
