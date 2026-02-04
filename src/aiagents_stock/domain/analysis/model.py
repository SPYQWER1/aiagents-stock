"""
分析领域模型。

本模块定义了单股分析的核心业务对象，包括聚合根、实体和值对象。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# ==========================================
# Value Objects (值对象)
# ==========================================

class AgentRole(str, Enum):
    """分析师角色定义"""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    FUND_FLOW = "fund_flow"
    RISK_MANAGEMENT = "risk_management"
    MARKET_SENTIMENT = "market_sentiment"
    NEWS_ANALYST = "news_analyst"

@dataclass(frozen=True)
class AnalysisContent:
    """分析内容值对象，保证不可变性"""
    summary: str
    details: Dict[str, Any]
    focus_areas: List[str]
    raw_output: str

@dataclass(frozen=True)
class StockInfo:
    """股票基本信息值对象"""
    symbol: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    current_price: float = 0.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StockInfo:
        return cls(
            symbol=str(data.get("symbol", "")),
            name=str(data.get("name", "")),
            sector=str(data.get("sector", "")),
            industry=str(data.get("industry", "")),
            current_price=float(data.get("current_price", 0.0) or 0.0)
        )

# ==========================================
# Entities (实体)
# ==========================================

@dataclass
class AgentReview:
    """
    实体：代表一个智能体的评审记录
    """
    role: AgentRole
    content: AnalysisContent
    timestamp: datetime = field(default_factory=datetime.now)
    agent_name: str = ""  # e.g., "技术分析师"

    def is_positive(self) -> bool:
        """业务行为：判断该评审是否偏向正面"""
        # 示例逻辑：基于 content 中的评分或关键词
        score = self.content.details.get("score")
        if score is not None:
            return float(score) > 60
        return False

# ==========================================
# Aggregate Root (聚合根)
# ==========================================

class StockAnalysisStatus(str, Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class StockAnalysis:
    """
    聚合根：单股分析
    
    职责：
    1. 维护分析过程的完整性
    2. 确保所有 Agent 的评审都已完成才能生成最终决策
    3. 封装状态变更逻辑
    """
    
    def __init__(
        self, 
        stock_info: StockInfo, 
        analysis_id: Optional[str] = None,
        period: str = "1y"
    ):
        self.id = analysis_id or str(uuid.uuid4())
        self.stock_info = stock_info
        self.period = period
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self._reviews: Dict[AgentRole, AgentReview] = {}
        self.team_discussion: Optional[str] = None
        self.final_decision: Optional[Dict[str, Any]] = None
        self._status = StockAnalysisStatus.CREATED

    @property
    def status(self) -> StockAnalysisStatus:
        return self._status

    @property
    def reviews(self) -> Dict[AgentRole, AgentReview]:
        return self._reviews.copy()

    def start(self) -> None:
        """开始分析"""
        if self._status != StockAnalysisStatus.CREATED:
             # 允许重入，或者抛出异常，视业务规则而定。这里简单处理。
             pass
        self._status = StockAnalysisStatus.IN_PROGRESS
        self.updated_at = datetime.now()

    def add_review(self, role: AgentRole, content: AnalysisContent, agent_name: str = "") -> None:
        """
        业务行为：添加分析评审
        """
        if self._status == StockAnalysisStatus.COMPLETED:
            raise ValueError("Cannot add review to a completed analysis.")
        
        review = AgentReview(role=role, content=content, agent_name=agent_name)
        self._reviews[role] = review
        self._status = StockAnalysisStatus.IN_PROGRESS
        self.updated_at = datetime.now()

    def conduct_team_discussion(self, discussion_content: str) -> None:
        """记录团队讨论结果"""
        if not self._reviews:
            raise ValueError("Cannot conduct discussion without any reviews.")
        self.team_discussion = discussion_content
        self.updated_at = datetime.now()

    def finalize_decision(self, decision: Dict[str, Any]) -> None:
        """
        业务行为：生成最终决策
        """
        if not self.team_discussion:
            raise ValueError("Cannot finalize decision before team discussion.")
        
        self.final_decision = decision
        self._status = StockAnalysisStatus.COMPLETED
        self.updated_at = datetime.now()
    
    def fail(self, reason: str = "") -> None:
        self._status = StockAnalysisStatus.FAILED
        self.updated_at = datetime.now()
