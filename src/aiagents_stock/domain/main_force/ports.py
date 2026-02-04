from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from aiagents_stock.domain.main_force.model import MainForceAnalysis, MainForceRecommendation, MainForceStock


class MainForceProvider(ABC):
    """主力资金数据提供者接口"""
    
    @abstractmethod
    def get_main_force_stocks(
        self, 
        start_date: str = None, 
        days_ago: int = None, 
        min_market_cap: float = None, 
        max_market_cap: float = None,
        max_range_change: float = None,
        top_n: int = None
    ) -> Tuple[bool, List[MainForceStock], str]:
        """获取主力资金净流入股票"""
        pass

class MainForceAnalysisRepository(ABC):
    """主力选股分析仓储接口"""
    
    @abstractmethod
    def save(self, analysis: MainForceAnalysis) -> int:
        """保存分析记录"""
        pass
        
    @abstractmethod
    def get_by_id(self, record_id: int) -> Optional[MainForceAnalysis]:
        """根据ID获取记录"""
        pass
        
    @abstractmethod
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取历史记录列表(摘要)"""
        pass

    @abstractmethod
    def delete(self, record_id: int) -> bool:
        pass

class MainForceAIAnalyzer(ABC):
    """主力选股AI分析师接口"""
    
    @abstractmethod
    def analyze_fund_flow(self, stocks: List[MainForceStock], summary: str) -> str:
        """资金流向整体分析"""
        pass
        
    @abstractmethod
    def analyze_industry(self, stocks: List[MainForceStock], summary: str) -> str:
        """行业板块整体分析"""
        pass
        
    @abstractmethod
    def analyze_fundamental(self, stocks: List[MainForceStock], summary: str) -> str:
        """基本面整体分析"""
        pass
        
    @abstractmethod
    def select_best_stocks(
        self, 
        stocks: List[MainForceStock], 
        fund_analysis: str, 
        industry_analysis: str, 
        fundamental_analysis: str, 
        final_n: int
    ) -> List[MainForceRecommendation]:
        """综合精选"""
        pass
