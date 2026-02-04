"""
DeepSeek 分析编排器实现。

该模块实现了 AnalysisOrchestrator 接口，负责协调 DeepSeek 智能体进行分析。
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from aiagents_stock.domain.ai.ports import LLMClient
from aiagents_stock.domain.analysis.dto import StockDataBundle
from aiagents_stock.domain.analysis.model import (
    AgentRole,
    StockAnalysis,
)
from aiagents_stock.domain.analysis.prompts import (
    FINAL_DECISION_PROMPT,
    TEAM_DISCUSSION_PROMPT,
)
from aiagents_stock.domain.analysis.services import AnalysisAgent, AnalysisOrchestrator
from aiagents_stock.infrastructure.ai.agents import (
    FundamentalAgent,
    FundFlowAgent,
    MarketSentimentAgent,
    NewsAgent,
    RiskManagementAgent,
    TechnicalAgent,
)

logger = logging.getLogger(__name__)

class DeepSeekAnalysisOrchestrator(AnalysisOrchestrator):
    """
    基于 DeepSeek 的分析编排器。
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.agents: Dict[AgentRole, AnalysisAgent] = self._initialize_agents()

    def _initialize_agents(self) -> Dict[AgentRole, AnalysisAgent]:
        """初始化所有可用的 Agent"""
        return {
            AgentRole.TECHNICAL: TechnicalAgent(self.llm_client),
            AgentRole.FUNDAMENTAL: FundamentalAgent(self.llm_client),
            AgentRole.FUND_FLOW: FundFlowAgent(self.llm_client),
            AgentRole.RISK_MANAGEMENT: RiskManagementAgent(self.llm_client),
            AgentRole.MARKET_SENTIMENT: MarketSentimentAgent(self.llm_client),
            AgentRole.NEWS_ANALYST: NewsAgent(self.llm_client),
        }

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
            future_to_role = {}
            for role in enabled_agents:
                agent = self.agents.get(role)
                if agent:
                    future_to_role[executor.submit(agent.analyze, analysis.stock_info, data_bundle)] = role
                else:
                    logger.warning(f"Agent {role} not implemented or initialized.")

            for future in as_completed(future_to_role):
                role = future_to_role[future]
                try:
                    review = future.result()
                    if review:
                        analysis.add_review(role, review.content, review.agent_name)
                except Exception as e:
                    logger.error(f"Agent {role} failed: {e}", exc_info=True)
        
        # 2. 团队讨论与决策
        self._conduct_team_discussion(analysis, data_bundle)
        
        return analysis

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.llm_client.call_chat(messages, temperature=temperature, max_tokens=max_tokens)

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

        decision_json = None
        error_msg = None

        # 第一次解析尝试
        try:
            decision_json = self._extract_json(response)
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"First attempt to parse decision JSON failed: {e}. Output: {response[:200]}...")

        # 如果失败，尝试修复
        if decision_json is None:
            logger.info("Attempting to fix JSON format...")
            try:
                fixed_response = self._fix_json_format(response, error_msg or "No JSON found")
                decision_json = self._extract_json(fixed_response)
            except Exception as e:
                logger.error(f"Failed to fix JSON format: {e}")
                # 依然失败，降级处理
        
        if decision_json:
            analysis.finalize_decision(decision_json)
        else:
            # 最终兜底
            analysis.finalize_decision({"decision_text": response, "error": "JSON parse failed after retry"})

    def _extract_json(self, text: str) -> Optional[Dict]:
        """从文本中提取并解析 JSON"""
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None

    def _fix_json_format(self, raw_output: str, error_message: str) -> str:
        """调用 LLM 修复 JSON 格式"""
        from aiagents_stock.domain.analysis.prompts import JSON_FIX_PROMPT
        
        prompt = JSON_FIX_PROMPT.format(
            error_message=error_message,
            raw_output=raw_output
        )
        
        return self._call_llm(
            "你是一个 JSON 格式修复专家。",
            prompt,
            temperature=0.1 # 低温度以保证格式准确
        )
