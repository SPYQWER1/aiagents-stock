from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MainForceStock:
    """主力资金选出的候选股票"""
    symbol: str
    name: str
    industry: str
    market_cap: float
    range_change: float  # 区间涨跌幅
    main_fund_inflow: float # 主力资金净流入
    
    # 财务数据
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    revenue: Optional[str] = None
    net_profit: Optional[str] = None
    
    # 评分数据
    scores: Dict[str, Any] = field(default_factory=dict)
    
    # 原始数据
    raw_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MainForceRecommendation:
    """最终推荐"""
    rank: int
    symbol: str
    name: str
    reasons: List[str]
    highlights: str
    risks: str
    position: str # 建议仓位
    investment_period: str # 投资周期
    stock_data: Dict[str, Any] = field(default_factory=dict) # 关联的股票数据

@dataclass
class MainForceAnalysis:
    """主力选股分析聚合根"""
    id: Optional[int] = None # 数据库ID
    analysis_date: datetime = field(default_factory=datetime.now)
    
    # 输入参数
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 过程数据
    raw_stocks: List[MainForceStock] = field(default_factory=list)
    filtered_stocks: List[MainForceStock] = field(default_factory=list)
    
    # AI 分析结果
    fund_flow_analysis: Optional[str] = None
    industry_analysis: Optional[str] = None
    fundamental_analysis: Optional[str] = None
    
    # 最终决策
    recommendations: List[MainForceRecommendation] = field(default_factory=list)
    
    # 统计信息
    total_time: float = 0.0
    success: bool = False
    error: Optional[str] = None
