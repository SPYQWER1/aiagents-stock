"""
分析记录 SQLite 仓储适配器。

该模块基于现有的 StockAnalysisDatabase 存储实现，
对外提供领域端口 StockAnalysisRepository 所需的最小能力。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict

from aiagents_stock.db.database import StockAnalysisDatabase
from aiagents_stock.domain.analysis.ports import StockAnalysisRepository
from aiagents_stock.domain.analysis.model import StockAnalysis, StockInfo, AgentRole, AgentReview, AnalysisContent

@dataclass(frozen=True)
class SqliteStockAnalysisRepository(StockAnalysisRepository):
    """
    基于 sqlite 的聚合根仓储。
    """
    database: StockAnalysisDatabase

    def save(self, analysis: StockAnalysis) -> int:
        """保存分析聚合根。"""
        # Map Aggregate to DB format
        agents_results = {}
        for role, review in analysis.reviews.items():
            # Convert AgentReview to dict expected by DB
            # DB expects structure similar to what DeepSeekAnalyzer outputted
            agents_results[role.value] = {
                "agent_name": review.agent_name,
                "analysis": review.content.raw_output, # DB often stores the raw string or dict
                "focus_areas": review.content.focus_areas,
                "timestamp": review.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }

        # Convert StockInfo to dict
        stock_info_dict = asdict(analysis.stock_info)

        record_id = self.database.save_analysis(
            symbol=analysis.stock_info.symbol,
            stock_name=analysis.stock_info.name,
            period=analysis.period,
            stock_info=stock_info_dict,
            agents_results=agents_results,
            discussion_result=analysis.team_discussion,
            final_decision=analysis.final_decision
        )
        
        # Update ID if it was new (though Aggregate usually has ID beforehand, DB ID might be different)
        # Here we assume analysis.id is UUID, but DB returns int ID. 
        # We might need to store the DB ID or mapping if we want to retrieve by it later.
        # For now, we just save and return the DB ID.
        return int(record_id)

    def find_by_id(self, analysis_id: str) -> StockAnalysis | None:
        """根据 ID 查找分析聚合根。"""
        # Note: The DB uses int ID, but Aggregate uses UUID (str). 
        # If analysis_id is passed as str representation of int, we can try to parse it.
        try:
            db_id = int(analysis_id)
        except ValueError:
            return None # Or handle UUID lookup if DB supported it

        raw = self.database.get_record_by_id(db_id)
        if not raw:
            return None

        # Map DB raw data to Aggregate
        stock_info_data = raw.get("stock_info") or {}
        # Ensure minimal fields
        stock_info_data.setdefault("symbol", raw.get("symbol"))
        stock_info_data.setdefault("name", raw.get("stock_name"))
        
        stock_info = StockInfo.from_dict(stock_info_data)
        
        analysis = StockAnalysis(
            stock_info=stock_info,
            analysis_id=str(db_id),
            period=str(raw.get("period") or "1y")
        )

        # Restore Reviews
        agents_results = raw.get("agents_results") or {}
        for role_key, agent_data in agents_results.items():
            try:
                role = AgentRole(role_key)
                content = AnalysisContent(
                    summary=agent_data.get("analysis", "")[:200],
                    details={"full_text": agent_data.get("analysis", "")},
                    focus_areas=agent_data.get("focus_areas", []),
                    raw_output=agent_data.get("analysis", "")
                )
                analysis.add_review(role, content, agent_data.get("agent_name", ""))
            except ValueError:
                continue # Unknown role

        # Restore Discussion
        discussion = raw.get("discussion_result")
        if discussion:
            # discussion in DB might be dict or str
            if isinstance(discussion, dict):
                 # Assuming structure from DeepSeekAnalyzer: {"content": ..., ...}
                 discussion_content = discussion.get("content", str(discussion))
                 analysis.conduct_team_discussion(discussion_content)
            else:
                 analysis.conduct_team_discussion(str(discussion))

        # Restore Final Decision
        final_decision = raw.get("final_decision")
        if final_decision:
            analysis.finalize_decision(final_decision)

        return analysis
